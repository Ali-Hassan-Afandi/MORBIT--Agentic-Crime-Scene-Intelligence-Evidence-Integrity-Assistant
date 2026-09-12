from __future__ import annotations

import base64
import hashlib
import io
import json
import random
import re
import time
from typing import Any

from PIL import Image
from groq import Groq

# Vision + strict JSON Schema support.
VISION_MODEL = "qwen/qwen3.8-27b"

# Keep output comfortably below the user's OTPM ceiling.
PRIMARY_OUTPUT_TOKENS = 360
RETRY_OUTPUT_TOKENS = 280

# Hackathon reliability:
# Groq currently counts each Qwen vision image as 2048 input tokens.
# When Photo 2 arrives inside the same rolling minute as Photo 1 or another
# organization request, ITPM can be temporarily exhausted. We therefore
# honor Groq's requested retry delay instead of using a fixed sleep.
MAX_RATE_LIMIT_RETRIES = 3
DEFAULT_RETRY_SECONDS = 10.0
RETRY_BUFFER_SECONDS = 1.5

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
                    "observation": str(item.get("observation", "") or "")[:200],
                    "possible_category": category,
                    "confidence": confidence,
                    "reason": str(item.get("reason", "") or "")[:200],
                }
            )

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


def _is_rate_limit_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return (
        "429" in text
        or "rate_limit_exceeded" in text
        or "rate limit reached" in text
        or "input tokens per minute" in text
        or "output tokens per minute" in text
        or "itpm" in text
        or "otpm" in text
    )


def _retry_delay_from_error(exc: Exception) -> float:
    """
    Groq rate-limit messages commonly contain:
      'Please try again in 8.382857142s.'
    Parse that delay and add a small buffer. If the SDK/provider changes the
    text, fall back to a safe delay.
    """
    text = str(exc)

    patterns = [
        r"try again in\s+([0-9]+(?:\.[0-9]+)?)s",
        r"retry[- ]after[:=\s]+([0-9]+(?:\.[0-9]+)?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return max(float(match.group(1)) + RETRY_BUFFER_SECONDS, 2.0)

    return DEFAULT_RETRY_SECONDS


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


def _request_with_adaptive_retry(
    client: Groq,
    messages: list[dict[str, Any]],
):
    """
    Retry only provider rate-limit errors.
    The important change is that we wait for Groq's actual rolling-window reset
    instead of retrying after a hard-coded 6 seconds.
    """
    last_error: Exception | None = None

    for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
        max_tokens = PRIMARY_OUTPUT_TOKENS if attempt == 0 else RETRY_OUTPUT_TOKENS

        try:
            return _run_strict_request(
                client=client,
                messages=messages,
                max_tokens=max_tokens,
            )

        except Exception as exc:
            last_error = exc

            if not _is_rate_limit_error(exc):
                raise

            if attempt >= MAX_RATE_LIMIT_RETRIES:
                break

            wait_seconds = _retry_delay_from_error(exc)

            # Small jitter prevents multiple app sessions from retrying
            # at exactly the same instant.
            wait_seconds += random.uniform(0.2, 0.8)
            time.sleep(wait_seconds)

    raise RuntimeError(
        "Groq vision rate limit remained active after automatic retries. "
        "Please wait about one minute and try the photograph again. "
        f"Last provider error: {last_error}"
    ) from last_error


def analyze_image(
    client: Groq,
    data: bytes,
    filename: str,
    scene_context: str = "",
) -> dict[str, Any]:
    """
    Hackathon-safe image analysis:
    - qwen/qwen3.8-27b
    - strict schema (prevents json_validate_failed)
    - compact output (protects OTPM)
    - adaptive retry using Groq's own requested delay (protects ITPM/OTPM)
    """

    prompt = f"""
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
- summary: max 2 short sentences
- observations: max 4
- documentation suggestions: max 3
- limitations: max 2
- no repetition
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

    completion = _request_with_adaptive_retry(
        client=client,
        messages=messages,
    )

    raw = completion.choices[0].message.content or ""
    parsed = json.loads(raw)
    return _normalize_result(parsed)
