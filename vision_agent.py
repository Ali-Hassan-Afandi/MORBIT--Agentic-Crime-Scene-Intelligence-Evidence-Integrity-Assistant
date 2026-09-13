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

PRIMARY_OUTPUT_TOKENS = 620
FALLBACK_OUTPUT_TOKENS = 520

ALLOWED_CATEGORIES = [
    "possible_human_body_or_remains",
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
        "scene_priority_mode": {
            "type": "string",
            "enum": ["death_scene_body_first", "general_scene"],
        },
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
        "scene_priority_mode",
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
        value = json.loads(raw)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        value = json.loads(raw[start:end + 1])
        if isinstance(value, dict):
            return value

    raise RuntimeError("Vision model did not return a usable JSON object.")


def _looks_like_death_scene(scene_type: str, scene_context: str) -> bool:
    text = f"{scene_type}\n{scene_context}".lower()
    death_terms = [
        "homicide",
        "murder",
        "suspicious death",
        "death scene",
        "human remains",
        "body/remains",
        "body remains",
        "corpse",
        "deceased",
    ]
    return any(term in text for term in death_terms)


def _normalize_result(obj: dict[str, Any], death_scene: bool) -> dict[str, Any]:
    result = {
        "image_summary": str(obj.get("image_summary", "") or "")[:600],
        "scene_priority_mode": (
            "death_scene_body_first" if death_scene else "general_scene"
        ),
        "potential_observations": [],
        "documentation_suggestions": [],
        "limitations": [],
    }

    observations = obj.get("potential_observations", [])
    seen = set()
    normalized = []

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

            normalized.append({
                "priority_rank": rank,
                "observation": observation[:220],
                "location_in_image": str(item.get("location_in_image", "") or "")[:120],
                "possible_category": category,
                "confidence": confidence,
                "importance_reason": str(item.get("importance_reason", "") or "")[:220],
            })

    if death_scene:
        body_items = [
            x for x in normalized
            if x["possible_category"] == "possible_human_body_or_remains"
        ]
        other_items = [
            x for x in normalized
            if x["possible_category"] != "possible_human_body_or_remains"
        ]
        normalized = body_items + other_items

    normalized = normalized[:5]
    for i, item in enumerate(normalized, start=1):
        item["priority_rank"] = i

    result["potential_observations"] = normalized

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


def _prompt(scene_context: str, scene_type: str) -> str:
    death_scene = _looks_like_death_scene(scene_type, scene_context)

    death_priority = """
DEATH / MURDER SCENE PRIORITY MODE
The investigator's scene type indicates a homicide, murder, suspicious-death or human-remains scene.

FIRST PRIORITY:
- Before ranking any other evidence, systematically inspect the entire photograph for EVERY
  visually supportable possible human body, body-like form, or possible human remains.
- Put those candidates FIRST in the output.
- Use the category: possible_human_body_or_remains.
- Do NOT state that a person is dead merely from the photograph.
- Use cautious wording such as "possible human body", "person-like form", or
  "possible human remains" unless investigator context independently establishes status.
- Do not infer cause, manner or time of death.
- After all visible possible body/remains candidates have been included, use any remaining
  slots (up to five total candidates) for the most important other visible evidence.
- If five possible body/remains candidates occupy all five slots, return no other evidence.
""" if death_scene else """
GENERAL SCENE PRIORITY MODE
Rank the five most important distinct visible potential evidence candidates using scene relevance,
fragility/risk of loss, distinctiveness, relationship to damage or entry/exit, and visual clarity.
"""

    return f"""
You are MORBIT CSI CaseAssistant's Multimodal Scene Agent.
This is a human-supervised forensic documentation tool.

Review the ONE uploaded scene photograph systematically and return a MAXIMUM of FIVE
distinct visible potential evidence candidates. If fewer than five are genuinely supportable,
return fewer. Never invent evidence.

{death_priority}

SYSTEMATIC VISUAL SWEEP
Before ranking, inspect foreground/middle/background and left/centre/right, including:
- floor/ground
- doors, windows and entry/exit points
- furniture and fixtures
- devices and documents
- glass/fragments
- visible stains or residue-like areas
- impressions/marks
- fibres/hair-like material
- damage
- containers and loose objects
- disturbed surfaces
- weapon-like objects by visible form only

FORENSIC SAFETY
- Do not identify a person or suspect.
- Do not infer guilt, motive, ethnicity, age or offender profile.
- Do not scientifically confirm blood, DNA, drugs, explosives, fingerprints,
  toolmarks, firearm relationships, cause of death, fire cause or laboratory findings.
- Use cautious terms: visible, apparent, possible, potential, may warrant examination.
- Every item is an AI proposal until an investigator verifies it.

SCENE TYPE
{scene_type or "Not specified"}

COMPLETE SAVED CASE INPUT
{scene_context or "No investigator case description supplied."}

OUTPUT RULES
- image_summary: maximum 2 concise sentences.
- potential_observations: maximum 5.
- location_in_image: concise position such as lower-left foreground.
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
    match = re.search(r"try again in\s+([0-9]+(?:\.[0-9]+)?)s", text, flags=re.I)
    if match:
        return min(max(float(match.group(1)) + 1.2, 2.0), 25.0)
    return 8.0


def analyze_image(
    client: Groq,
    data: bytes,
    filename: str,
    scene_context: str = "",
    scene_type: str = "",
) -> dict[str, Any]:
    death_scene = _looks_like_death_scene(scene_type, scene_context)
    prompt = _prompt(scene_context, scene_type)
    messages = _messages(prompt, data, filename)

    try:
        completion = _primary_request(client, messages)
        raw = completion.choices[0].message.content or ""
        return _normalize_result(json.loads(raw), death_scene)
    except Exception as exc:
        if _is_rate_limit(exc):
            time.sleep(_retry_seconds(exc))
            completion = _primary_request(client, messages)
            raw = completion.choices[0].message.content or ""
            return _normalize_result(json.loads(raw), death_scene)

        if not _is_capacity(exc) and "json" not in str(exc).lower():
            raise

    fallback_prompt = prompt + """
Return exactly one compact JSON object with the requested keys.
Do not use markdown or code fences.
""".strip()

    completion = _fallback_request(
        client,
        _messages(fallback_prompt, data, filename),
    )
    raw = completion.choices[0].message.content or ""
    return _normalize_result(_extract_json(raw), death_scene)
