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

# Keep the currently deployed vision model to minimize moving parts.
VISION_MODEL = "qwen/qwen3.6-27b"

# Hackathon-safe output limits for an OTPM ceiling of 1000.
PRIMARY_OUTPUT_TOKENS = 420
RETRY_OUTPUT_TOKENS = 320


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
    raw = (raw or "").strip()
    if not raw:
        raise RuntimeError("Vision model returned an empty response.")

    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end > start:
            return json.loads(raw[start:end + 1])

    raise RuntimeError(f"Vision model returned invalid JSON: {raw[:300]!r}")


def _normalize_result(obj: dict[str, Any]) -> dict[str, Any]:
    result = {
        "image_summary": str(obj.get("image_summary", "") or ""),
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
                    "observation": str(item.get("observation", "") or "")[:240],
                    "possible_category": category,
                    "confidence": confidence,
                    "reason": str(item.get("reason", "") or "")[:240],
                }
            )

    suggestions = obj.get("documentation_suggestions", [])
    if isinstance(suggestions, list):
        result["documentation_suggestions"] = [
            str(x)[:220] for x in suggestions[:3] if str(x).strip()
        ]

    limitations = obj.get("limitations", [])
    if isinstance(limitations, list):
        result["limitations"] = [
            str(x)[:220] for x in limitations[:2] if str(x).strip()
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


def _make_completion(
    client: Groq,
    messages: list[dict[str, Any]],
    max_tokens: int,
):
    return client.chat.completions.create(
        model=VISION_MODEL,
        messages=messages,
        temperature=0,
        max_completion_tokens=max_tokens,
        response_format={"type": "json_object"},
    )


def analyze_image(
    client: Groq,
    data: bytes,
    filename: str,
    scene_context: str = "",
) -> dict[str, Any]:
    prompt = f"""
You are MORBIT CSI CaseAssistant's Multimodal Scene Agent.
This is a human-supervised forensic documentation prototype.

Analyze ONLY what is visibly supportable in the supplied scene photograph.

Mandatory safety rules:
- Never identify a person or suspect.
- Never infer guilt, motive, ethnicity, age, offender profile, or identity.
- Never confirm that a visible stain is blood, DNA, narcotics, explosive material,
  or another scientifically established substance from the image alone.
- Never claim a visible mark is a confirmed fingerprint.
- Never make laboratory findings, firearm-linkage conclusions, toolmark conclusions,
  cause-of-death findings, or fire-cause determinations.
- Use cautious terms such as visible, apparent, possible, potential, and may warrant examination.
- Separate direct visual observation from interpretation.
- The investigator must verify every proposed observation.

Investigator scene context:
{scene_context or "No scene context supplied."}

Return ONLY one compact valid JSON object with exactly these keys:
{{
  "image_summary": "...",
  "potential_observations": [
    {{
      "observation": "...",
      "possible_category": "biological|digital|latent_print|trace|physical|other",
      "confidence": "low|medium|high",
      "reason": "..."
    }}
  ],
  "documentation_suggestions": ["..."],
  "limitations": ["..."]
}}

Hackathon output limits:
- image_summary: maximum 2 short sentences.
- potential_observations: maximum 4 items.
- documentation_suggestions: maximum 3 short items.
- limitations: maximum 2 short items.
- Keep every field brief.
- Do not repeat information.
""".strip()

    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": _data_url(data, filename)}},
        ],
    }]

    try:
        completion = _make_completion(
            client=client,
            messages=messages,
            max_tokens=PRIMARY_OUTPUT_TOKENS,
        )
    except Exception as exc:
        if not _is_rate_limit_error(exc):
            raise

        # One short backoff protects the live demo from a transient OTPM window.
        time.sleep(6)

        completion = _make_completion(
            client=client,
            messages=messages,
            max_tokens=RETRY_OUTPUT_TOKENS,
        )

    raw = completion.choices[0].message.content or ""
    parsed = _extract_json(raw)
    return _normalize_result(parsed)
