from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import time
from typing import Any

from PIL import Image
from groq import Groq

# Primary: strict structured output.
PRIMARY_VISION_MODEL = "qwen/qwen3.8-27b"

# Availability fallback:
# qwen3.6 is used WITHOUT provider-side JSON mode so a transient structured
# output/over-capacity issue cannot block the hackathon workflow.
FALLBACK_VISION_MODEL = "qwen/qwen3.6-27b"

# Keep the single-photo response compact and fast.
PRIMARY_OUTPUT_TOKENS = 360
FALLBACK_OUTPUT_TOKENS = 320

VISION_MODEL = PRIMARY_VISION_MODEL

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


def _extract_json(raw: str) -> dict[str, Any]:
    """Recover a JSON object from plain model text without provider JSON mode."""
    raw = (raw or "").strip()
    if not raw:
        raise RuntimeError("Vision model returned an empty response.")

    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        value = json.loads(raw)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        value = json.loads(raw[start:end + 1])
        if isinstance(value, dict):
            return value

    raise RuntimeError("Vision model did not return a usable JSON object.")


def _normalize_result(obj: dict[str, Any]) -> dict[str, Any]:
    result = {
        "image_summary": str(obj.get("image_summary", "") or "")[:500],
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
                "biological", "digital", "latent_print",
                "trace", "physical", "other",
            }:
                category = "other"

            confidence = str(item.get("confidence", "low") or "low").lower()
            if confidence not in {"low", "medium", "high"}:
                confidence = "low"

            result["potential_observations"].append({
                "observation": str(item.get("observation", "") or "")[:200],
                "possible_category": category,
                "confidence": confidence,
                "reason": str(item.get("reason", "") or "")[:200],
            })

    suggestions = obj.get("documentation_suggestions", [])
    if isinstance(suggestions, list):
        result["documentation_suggestions"] = [
            str(x)[:180] for x in suggestions[:3] if str(x).strip()
        ]

    limitations = obj.get("limitations", [])
    if isinstance(limitations, list):
        result["limitations"] = [
            str(x)[:180] for x in limitations[:2] if str(x).strip()
        ]

    return result


def _base_prompt(scene_context: str) -> str:
    return f"""
You are MORBIT CSI CaseAssistant's Multimodal Scene Agent.
This is a human-supervised forensic documentation prototype.

Analyze only what is visibly supportable in the supplied photograph.

Rules:
- Do not identify a person or suspect.
- Do not infer guilt, motive, ethnicity, age, offender profile, or identity.
- Do not confirm blood, DNA, narcotics, explosives, fingerprints, toolmarks,
  firearm relationships, cause of death, fire cause, or laboratory conclusions.
- Use cautious terms: visible, apparent, possible, potential, may warrant examination.
- Separate observation from interpretation.
- Every proposed observation requires investigator verification.

Scene context:
{scene_context or "No scene context supplied."}

Be concise:
- image_summary: maximum 2 short sentences
- potential_observations: maximum 4 items
- documentation_suggestions: maximum 3 short items
- limitations: maximum 2 short items
- no repetition
""".strip()


def _messages(prompt: str, data: bytes, filename: str) -> list[dict[str, Any]]:
    return [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": _data_url(data, filename)}},
        ],
    }]


def _primary_request(client: Groq, messages: list[dict[str, Any]]):
    return client.chat.completions.create(
        model=PRIMARY_VISION_MODEL,
        messages=messages,
        temperature=0,
        reasoning_effort="none",
        max_completion_tokens=PRIMARY_OUTPUT_TOKENS,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "morbit_single_scene_photo",
                "strict": True,
                "schema": VISION_SCHEMA,
            },
        },
    )


def _fallback_request(client: Groq, messages: list[dict[str, Any]]):
    # IMPORTANT: no response_format here. This avoids the previous
    # json_validate_failed provider error on qwen3.6.
    return client.chat.completions.create(
        model=FALLBACK_VISION_MODEL,
        messages=messages,
        temperature=0,
        reasoning_effort="none",
        max_completion_tokens=FALLBACK_OUTPUT_TOKENS,
    )


def _is_capacity_or_rate_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(term in text for term in [
        "429",
        "503",
        "rate_limit_exceeded",
        "over capacity",
        "currently over capacity",
        "service unavailable",
        "input tokens per minute",
        "output tokens per minute",
        "itpm",
        "otpm",
    ])


def analyze_image(
    client: Groq,
    data: bytes,
    filename: str,
    scene_context: str = "",
) -> dict[str, Any]:
    """
    One-photo hackathon path.

    1) Try Qwen 3.8 with strict JSON Schema.
    2) If Groq reports capacity/rate pressure, immediately fall back to Qwen 3.6
       without provider JSON validation and parse JSON locally.
    3) If the fallback is also temporarily unavailable, wait briefly and retry
       the fallback once.

    Normal successful requests do not wait or sleep.
    """
    prompt = _base_prompt(scene_context)
    messages = _messages(prompt, data, filename)

    try:
        completion = _primary_request(client, messages)
        raw = completion.choices[0].message.content or ""
        return _normalize_result(json.loads(raw))
    except Exception as primary_exc:
        if not _is_capacity_or_rate_error(primary_exc):
            raise

    fallback_prompt = prompt + """

Return ONE compact JSON object only with these exact keys:
image_summary
potential_observations
documentation_suggestions
limitations

Each potential_observations item must contain:
observation, possible_category, confidence, reason.
Do not use markdown or code fences.
""".strip()
    fallback_messages = _messages(fallback_prompt, data, filename)

    try:
        completion = _fallback_request(client, fallback_messages)
        raw = completion.choices[0].message.content or ""
        return _normalize_result(_extract_json(raw))
    except Exception as fallback_exc:
        if not _is_capacity_or_rate_error(fallback_exc):
            raise

        # One short retry only on genuine temporary provider pressure.
        time.sleep(4)
        completion = _fallback_request(client, fallback_messages)
        raw = completion.choices[0].message.content or ""
        return _normalize_result(_extract_json(raw))
