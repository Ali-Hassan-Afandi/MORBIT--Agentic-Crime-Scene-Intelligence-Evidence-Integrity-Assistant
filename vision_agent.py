from __future__ import annotations

import base64
import hashlib
import io
import json
import re
from typing import Any

from PIL import Image
from groq import Groq

VISION_MODEL = "qwen/qwen3.8-27b"

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
                        "enum": ["biological", "digital", "latent_print", "trace", "physical", "other"],
                    },
                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                    "reason": {"type": "string"},
                },
                "required": ["observation", "possible_category", "confidence", "reason"],
                "additionalProperties": False,
            },
        },
        "documentation_suggestions": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["image_summary", "potential_observations", "documentation_suggestions", "limitations"],
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
        "image_summary": str(obj.get("image_summary", "") or ""),
        "potential_observations": [],
        "documentation_suggestions": [],
        "limitations": [],
    }

    observations = obj.get("potential_observations", [])
    if isinstance(observations, list):
        for item in observations:
            if not isinstance(item, dict):
                continue

            category = str(item.get("possible_category", "other") or "other").lower()
            if category not in {"biological", "digital", "latent_print", "trace", "physical", "other"}:
                category = "other"

            confidence = str(item.get("confidence", "low") or "low").lower()
            if confidence not in {"low", "medium", "high"}:
                confidence = "low"

            result["potential_observations"].append({
                "observation": str(item.get("observation", "") or ""),
                "possible_category": category,
                "confidence": confidence,
                "reason": str(item.get("reason", "") or ""),
            })

    for key in ("documentation_suggestions", "limitations"):
        value = obj.get(key, [])
        if isinstance(value, list):
            result[key] = [str(x) for x in value if str(x).strip()]

    return result


def _extract_json_fallback(raw: str) -> dict[str, Any]:
    raw = (raw or "").strip()
    if not raw:
        raise RuntimeError("Vision model returned an empty response.")

    raw = re.sub(r"^```(?:json)?\\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\\s*```$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end > start:
            return json.loads(raw[start:end + 1])

    raise RuntimeError(f"Vision model returned unparseable JSON text: {raw[:300]!r}")


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
- Never confirm that a visible stain is blood, DNA, narcotics, explosive material, or another scientifically established substance from the image alone.
- Never claim a visible mark is a confirmed fingerprint.
- Never make laboratory findings, firearm-linkage conclusions, toolmark conclusions, cause-of-death findings, or fire-cause determinations.
- Use cautious terms such as visible, apparent, possible, potential, and may warrant examination.
- Separate direct visual observation from interpretation.
- The investigator must verify every proposed observation.

Investigator scene context:
{scene_context or "No scene context supplied."}

Keep the response concise:
- image_summary: 1 to 3 sentences.
- potential_observations: maximum 8 items.
- documentation_suggestions: maximum 5 short items.
- limitations: maximum 4 short items.
""".strip()

    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": _data_url(data, filename)}},
        ],
    }]

    try:
        completion = client.chat.completions.create(
            model=VISION_MODEL,
            messages=messages,
            temperature=0,
            max_completion_tokens=1400,
            reasoning_effort="none",
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "morbit_scene_image_analysis",
                    "strict": True,
                    "schema": VISION_SCHEMA,
                },
            },
        )
        raw = completion.choices[0].message.content or ""
        return _normalize_result(json.loads(raw))

    except Exception as primary_exc:
        fallback_prompt = prompt + """

Return one compact JSON object only, with these exact keys:
image_summary
potential_observations
documentation_suggestions
limitations

Each potential_observations item must contain:
observation, possible_category, confidence, reason.
""".strip()

        fallback_messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": fallback_prompt},
                {"type": "image_url", "image_url": {"url": _data_url(data, filename)}},
            ],
        }]

        try:
            completion = client.chat.completions.create(
                model=VISION_MODEL,
                messages=fallback_messages,
                temperature=0,
                max_completion_tokens=1400,
                reasoning_effort="none",
            )
            raw = completion.choices[0].message.content or ""
            return _normalize_result(_extract_json_fallback(raw))
        except Exception as fallback_exc:
            raise RuntimeError(
                "Photograph analysis could not produce a valid structured response. "
                f"Primary error: {primary_exc}. Fallback error: {fallback_exc}"
            ) from fallback_exc
