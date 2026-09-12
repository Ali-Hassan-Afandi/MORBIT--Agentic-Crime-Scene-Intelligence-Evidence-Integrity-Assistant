from __future__ import annotations

import base64
import hashlib
import io
import json
import time
from typing import Any

from PIL import Image
from groq import Groq

# Qwen 3.8 supports BOTH vision and strict JSON Schema Structured Outputs on Groq.
VISION_MODEL = "qwen/qwen3.8-27b"

# Keep well below the user's 1000 OTPM ceiling.
PRIMARY_OUTPUT_TOKENS = 420
RETRY_OUTPUT_TOKENS = 320

VISION_SCHEMA = {
    "type": "object",
    "properties": {
        "image_summary": {"type": "string"},
        "potential_observations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "observation": {"type": "string"},
                    "possible_category": {
                        "type": "string",
                        "enum": [
                            "biological",
                            "digital",
                            "latent_print",
                            "trace",
                            "physical",
                            "other",
                        ],
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                    },
                    "reason": {"type": "string"},
                },
                "required": [
                    "observation",
                    "possible_category",
                    "confidence",
                    "reason",
                ],
                "additionalProperties": False,
            },
        },
        "documentation_suggestions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "limitations": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "image_summary",
        "potential_observations",
        "documentation_suggestions",
        "limitations",
    ],
    "additionalProperties": False,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def image_metadata(data: bytes, filename: str) -> dict[str, Any]:
    with Image.open(io.BytesIO(data)) as im:
        exif = im.getexif()
        return {
            "filename": filename,
            "format": im.format,
            "width": im.width,
            "height": im.height,
            "mode": im.mode,
            "sha256": sha256_bytes(data),
            "bytes": len(data),
            "exif_datetime": str(exif.get(306, "")) if exif else "",
        }


def _data_url(data: bytes, filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1]
    mime = "image/png" if ext == "png" else "image/jpeg"
    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def _normalize_result(obj: dict[str, Any]) -> dict[str, Any]:
    """
    Keep downstream app expectations stable even if model wording varies.
    """
    result = {
        "image_summary": str(obj.get("image_summary", "") or "")[:600],
        "potential_observations": [],
        "documentation_suggestions": [],
        "limitations": [],
    }

    observations = obj.get("potential_observations", [])
    if isinstance(observations, list):
        for item in observations[:4]:
            if not isinstance(item, dict):
                continue

            category = str(item.get("possible_category", "other") or "other").lower()
            if category not in {
                "biological",
                "digital",
                "latent_print",
                "trace",
                "physical",
                "other",
            }:
                category = "other"

            confidence = str(item.get("confidence", "low") or "low").lower()
            if confidence not in {"low", "medium", "high"}:
                confidence = "low"

            result["potential_observations"].append(
                {
                    "observation": str(item.get("observation", "") or "")[:220],
                    "possible_category": category,
                    "confidence": confidence,
                    "reason": str(item.get("reason", "") or "")[:220],
                }
            )

    suggestions = obj.get("documentation_suggestions", [])
    if isinstance(suggestions, list):
        result["documentation_suggestions"] = [
            str(x)[:200] for x in suggestions[:3] if str(x).strip()
        ]

    limitations = obj.get("limitations", [])
    if isinstance(limitations, list):
        result["limitations"] = [
            str(x)[:200] for x in limitations[:2] if str(x).strip()
        ]

    return result


def _is_rate_limit_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return (
        "429" in text
        or "rate_limit_exceeded" in text
        or "output tokens per minute" in text
        or "otpm" in text
    )


def _run_strict_request(
    client: Groq,
    messages: list[dict[str, Any]],
    max_tokens: int,
):
    return client.chat.completions.create(
        model=VISION_MODEL,
        messages=messages,
        temperature=0,
        reasoning_effort="none",
        max_completion_tokens=max_tokens,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "morbit_scene_image_analysis",
                "strict": True,
                "schema": VISION_SCHEMA,
            },
        },
    )


def analyze_image(
    client: Groq,
    data: bytes,
    filename: str,
    scene_context: str = "",
) -> dict[str, Any]:
    """
    Production-style hackathon image analysis:
    - strict schema so provider cannot return malformed JSON
    - low output-token budget to stay below OTPM limit
    - one retry for transient rate-limit errors
    """

    prompt = f"""
You are MORBIT CSI CaseAssistant's Multimodal Scene Agent.
This is a human-supervised forensic documentation prototype.

Analyze ONLY what is visibly supportable in the supplied photograph.

Mandatory safety rules:
- Never identify a person or suspect.
- Never infer guilt, motive, ethnicity, age, offender profile, or identity.
- Never confirm that an apparent stain is blood, DNA, narcotics, explosive material,
  or any other scientifically established substance from the image alone.
- Never claim a visible mark is a confirmed fingerprint.
- Never make laboratory findings, firearm-linkage conclusions, toolmark conclusions,
  cause-of-death findings, or fire-cause determinations.
- Use cautious language such as visible, apparent, possible, potential, and may warrant examination.
- Separate observation from interpretation.
- The investigator must verify every proposed observation.

Investigator scene context:
{scene_context or "No scene context supplied."}

Keep the output concise:
- image_summary: maximum 2 short sentences.
- potential_observations: maximum 4 items.
- documentation_suggestions: maximum 3 short items.
- limitations: maximum 2 short items.
- Avoid repetition.
""".strip()

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": _data_url(data, filename)},
                },
            ],
        }
    ]

    try:
        completion = _run_strict_request(
            client=client,
            messages=messages,
            max_tokens=PRIMARY_OUTPUT_TOKENS,
        )
    except Exception as exc:
        if not _is_rate_limit_error(exc):
            raise

        time.sleep(6)

        completion = _run_strict_request(
            client=client,
            messages=messages,
            max_tokens=RETRY_OUTPUT_TOKENS,
        )

    raw = completion.choices[0].message.content or ""
    parsed = json.loads(raw)
    return _normalize_result(parsed)
