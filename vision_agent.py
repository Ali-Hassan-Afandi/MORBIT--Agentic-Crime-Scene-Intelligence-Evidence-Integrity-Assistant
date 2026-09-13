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

PRIMARY_VISION_MODEL = "qwen/qwen3.8-27b"
FALLBACK_VISION_MODEL = "qwen/qwen3.6-27b"
VISION_MODEL = PRIMARY_VISION_MODEL

# One image, one normal vision request. This budget is deliberately kept
# comfortably below the previously observed 1000 OTPM ceiling.
PRIMARY_OUTPUT_TOKENS = 620
FALLBACK_OUTPUT_TOKENS = 520

ALLOWED_CATEGORIES = [
    "biological",
    "digital",
    "latent_print",
    "trace",
    "physical",
    "document",
    "firearm_related",
    "impression",
    "glass",
    "other",
]

VISION_SCHEMA = {
    "type": "object",
    "properties": {
        "image_summary": {"type": "string"},
        "potential_observations": {
            "type": "array",
            "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {
                    "priority_rank": {"type": "integer", "minimum": 1, "maximum": 5},
                    "observation": {"type": "string"},
                    "location_in_image": {"type": "string"},
                    "possible_category": {
                        "type": "string",
                        "enum": ALLOWED_CATEGORIES,
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                    },
                    "importance_reason": {"type": "string"},
                },
                "required": [
                    "priority_rank",
                    "observation",
                    "location_in_image",
                    "possible_category",
                    "confidence",
                    "importance_reason",
                ],
                "additionalProperties": False,
            },
        },
        "documentation_suggestions": {
            "type": "array",
            "maxItems": 3,
            "items": {"type": "string"},
        },
        "limitations": {
            "type": "array",
            "maxItems": 2,
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
    raw = (raw or "").strip()
    if not raw:
        raise RuntimeError("Vision model returned an empty response.")

    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        obj = json.loads(raw[start:end + 1])
        if isinstance(obj, dict):
            return obj

    raise RuntimeError("Vision model did not return a usable JSON object.")


def _normalize_result(obj: dict[str, Any]) -> dict[str, Any]:
    result = {
        "image_summary": str(obj.get("image_summary", "") or "")[:600],
        "potential_observations": [],
        "documentation_suggestions": [],
        "limitations": [],
    }

    seen = set()
    observations = obj.get("potential_observations", [])
    if isinstance(observations, list):
        for index, item in enumerate(observations[:5], start=1):
            if not isinstance(item, dict):
                continue

            observation = str(item.get("observation", "") or "").strip()
            if not observation:
                continue

            dedupe = re.sub(r"\W+", " ", observation.lower()).strip()
            if dedupe in seen:
                continue
            seen.add(dedupe)

            category = str(item.get("possible_category", "other") or "other").lower()
            if category not in ALLOWED_CATEGORIES:
                category = "other"

            confidence = str(item.get("confidence", "low") or "low").lower()
            if confidence not in {"low", "medium", "high"}:
                confidence = "low"

            try:
                rank = int(item.get("priority_rank", index))
            except Exception:
                rank = index
            rank = max(1, min(5, rank))

            result["potential_observations"].append({
                "priority_rank": rank,
                "observation": observation[:220],
                "location_in_image": str(item.get("location_in_image", "") or "")[:120],
                "possible_category": category,
                "confidence": confidence,
                "importance_reason": str(item.get("importance_reason", "") or "")[:220],
            })

    result["potential_observations"] = sorted(
        result["potential_observations"],
        key=lambda x: x.get("priority_rank", 99),
    )[:5]

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


def _prompt(scene_context: str) -> str:
    return f"""
You are MORBIT CSI CaseAssistant's Multimodal Scene Agent.
This is a human-supervised forensic documentation tool.

Review the ONE uploaded scene photograph systematically, but return only the FIVE
MOST IMPORTANT distinct visible potential evidence candidates. If fewer than five
genuinely supportable candidates are visible, return fewer. Never invent evidence.

PRIORITIZATION
Rank candidates by practical forensic-documentation importance using:
1. likely relevance to the described scene/event,
2. fragility or risk of loss/contamination,
3. distinctiveness and value for later examination,
4. relationship to entry/exit, damage, position or other visible items,
5. clarity/visibility in the photograph.

Before ranking, mentally sweep foreground/middle/background and left/centre/right,
including floor/ground, doors/windows, furniture, devices, documents, glass/fragments,
visible stains/residue-like areas, impressions/marks, fibres/hair-like material,
damage, containers, loose objects and disturbed surfaces.

SAFETY
- Do not identify a person or suspect.
- Do not infer guilt, motive, ethnicity, age, offender profile or identity.
- Do not scientifically confirm blood, DNA, drugs, explosives, fingerprints,
  toolmarks, firearm relationships, cause of death, fire cause or laboratory findings.
- Use cautious terms such as visible, apparent, possible, potential, may warrant examination.
- Every item is an AI proposal until an investigator verifies it.

CASE INPUT USED AS CONTEXT
{scene_context or "No investigator case description supplied."}

OUTPUT
- image_summary: maximum 2 concise sentences.
- potential_observations: maximum 5, ranked 1-5 by importance.
- location_in_image: concise visible position, e.g. lower-left foreground.
- importance_reason: one concise sentence.
- documentation_suggestions: maximum 3.
- limitations: maximum 2.
- no repetition.
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
                "name": "morbit_top_five_visual_evidence",
                "strict": True,
                "schema": VISION_SCHEMA,
            },
        },
    )


def _fallback_request(client: Groq, messages: list[dict[str, Any]]):
    # Deliberately no response_format. This avoids provider-side JSON validation
    # failures previously seen on qwen3.6; JSON is parsed locally instead.
    return client.chat.completions.create(
        model=FALLBACK_VISION_MODEL,
        messages=messages,
        temperature=0,
        reasoning_effort="none",
        max_completion_tokens=FALLBACK_OUTPUT_TOKENS,
    )


def _is_rate_limit(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(x in text for x in [
        "429", "rate_limit_exceeded", "itpm", "otpm",
        "input tokens per minute", "output tokens per minute",
    ])


def _is_capacity(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(x in text for x in [
        "503", "over capacity", "currently over capacity", "service unavailable",
    ])


def _retry_seconds(exc: Exception) -> float:
    text = str(exc)
    m = re.search(r"try again in\s+([0-9]+(?:\.[0-9]+)?)s", text, flags=re.I)
    if m:
        return min(max(float(m.group(1)) + 1.2, 2.0), 25.0)
    return 8.0


def analyze_image(
    client: Groq,
    data: bytes,
    filename: str,
    scene_context: str = "",
) -> dict[str, Any]:
    """
    Reliable single-photo path:
    - normal path = one Qwen 3.8 request;
    - 429 = respect provider retry window and retry once;
    - 503/structured-output provider pressure = Qwen 3.6 plain JSON fallback.
    """
    prompt = _prompt(scene_context)
    messages = _messages(prompt, data, filename)

    try:
        completion = _primary_request(client, messages)
        raw = completion.choices[0].message.content or ""
        return _normalize_result(json.loads(raw))
    except Exception as exc:
        if _is_rate_limit(exc):
            time.sleep(_retry_seconds(exc))
            completion = _primary_request(client, messages)
            raw = completion.choices[0].message.content or ""
            return _normalize_result(json.loads(raw))
        if not _is_capacity(exc) and "json" not in str(exc).lower():
            raise

    fallback_prompt = prompt + """
Return exactly one compact JSON object with the requested keys.
Do not use markdown or code fences.
""".strip()
    completion = _fallback_request(client, _messages(fallback_prompt, data, filename))
    raw = completion.choices[0].message.content or ""
    return _normalize_result(_extract_json(raw))
