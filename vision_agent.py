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

# Primary model: vision + strict structured output.
PRIMARY_VISION_MODEL = "qwen/qwen3.8-27b"

# Availability fallback: no provider-side JSON validation.
FALLBACK_VISION_MODEL = "qwen/qwen3.6-27b"

# One-photo workflow allows a richer evidence inventory while staying below
# the previously observed 1000 OTPM ceiling.
PRIMARY_OUTPUT_TOKENS = 780
FALLBACK_OUTPUT_TOKENS = 650

VISION_MODEL = PRIMARY_VISION_MODEL

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
        "scene_zones_reviewed": {
            "type": "array",
            "items": {"type": "string"},
        },
        "potential_observations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
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
                    "reason": {"type": "string"},
                },
                "required": [
                    "observation",
                    "location_in_image",
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
        "coverage_note": {"type": "string"},
        "limitations": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "image_summary",
        "scene_zones_reviewed",
        "potential_observations",
        "documentation_suggestions",
        "coverage_note",
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

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        value = json.loads(raw[start:end + 1])
        if isinstance(value, dict):
            return value

    raise RuntimeError("Vision model did not return a usable JSON object.")


def _normalize_result(obj: dict[str, Any]) -> dict[str, Any]:
    result = {
        "image_summary": str(obj.get("image_summary", "") or "")[:700],
        "scene_zones_reviewed": [],
        "potential_observations": [],
        "documentation_suggestions": [],
        "coverage_note": str(obj.get("coverage_note", "") or "")[:400],
        "limitations": [],
    }

    zones = obj.get("scene_zones_reviewed", [])
    if isinstance(zones, list):
        result["scene_zones_reviewed"] = [
            str(x)[:80] for x in zones[:9] if str(x).strip()
        ]

    observations = obj.get("potential_observations", [])
    if isinstance(observations, list):
        seen = set()
        for item in observations[:10]:
            if not isinstance(item, dict):
                continue

            observation = str(item.get("observation", "") or "").strip()
            if not observation:
                continue

            # Avoid duplicate evidence candidates with trivially different wording.
            dedupe_key = re.sub(r"\W+", " ", observation.lower()).strip()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            category = str(item.get("possible_category", "other") or "other").lower()
            if category not in ALLOWED_CATEGORIES:
                category = "other"

            confidence = str(item.get("confidence", "low") or "low").lower()
            if confidence not in {"low", "medium", "high"}:
                confidence = "low"

            result["potential_observations"].append({
                "observation": observation[:240],
                "location_in_image": str(item.get("location_in_image", "") or "")[:140],
                "possible_category": category,
                "confidence": confidence,
                "reason": str(item.get("reason", "") or "")[:240],
            })

    suggestions = obj.get("documentation_suggestions", [])
    if isinstance(suggestions, list):
        result["documentation_suggestions"] = [
            str(x)[:220] for x in suggestions[:5] if str(x).strip()
        ]

    limitations = obj.get("limitations", [])
    if isinstance(limitations, list):
        result["limitations"] = [
            str(x)[:220] for x in limitations[:3] if str(x).strip()
        ]

    return result


def _base_prompt(scene_context: str) -> str:
    return f"""
You are MORBIT CSI CaseAssistant's Multimodal Scene Agent.
This is a human-supervised forensic documentation prototype.

Your goal is to perform a SYSTEMATIC VISUAL EVIDENCE SWEEP of the single uploaded
crime-scene photograph. Do not stop after finding the first obvious object.

VISUAL SWEEP METHOD
Review the photograph in an orderly sequence:
1. foreground, middle distance, background
2. left, centre, right
3. floor/ground, walls/vertical surfaces, furniture/fixtures, doors/windows/entry-exit areas
4. loose objects, containers, documents, devices, glass, weapons-like objects, damage,
   stains/residue-like areas, impressions/patterns, fibres/hair-like material, fragments,
   discarded items, disturbed surfaces and other objects that may warrant documentation
5. relationships between visible items and their apparent positions

For every distinct visually supportable potential evidence candidate, create a separate
observation. Include less obvious candidates when they are genuinely visible. Aim for a
complete inventory of the photograph, not merely the four most obvious items.

FORENSIC SAFETY RULES
- Never identify a person or suspect.
- Never infer guilt, motive, ethnicity, age, offender profile or identity.
- Never confirm blood, DNA, narcotics, explosives, fingerprints, toolmarks,
  firearm relationships, cause of death, fire cause or laboratory conclusions.
- A stain may be described only as an apparent/possible stain.
- A mark may be described only as a visible/apparent mark or impression.
- A weapon-like item may be described by visible form only; do not confirm operability.
- Use cautious terms: visible, apparent, possible, potential, may warrant examination.
- Separate direct observation from interpretation.
- Every proposed observation requires investigator verification.
- Do not invent an item merely to make the list longer.

INVESTIGATOR SCENE CONTEXT
{scene_context or "No scene context supplied."}

OUTPUT EXPECTATIONS
- image_summary: 2-3 concise sentences
- scene_zones_reviewed: list the zones/areas actually reviewed
- potential_observations: up to 10 DISTINCT visible evidence candidates
- each observation must state where it appears in the image
- documentation_suggestions: up to 5 practical photography/documentation suggestions
- coverage_note: briefly state whether the visible scene was systematically reviewed and
  mention any area obscured, blurred, dark, cropped or impossible to assess
- limitations: up to 3 concise limitations
- avoid repetition
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
                "name": "morbit_systematic_scene_sweep",
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


def _is_capacity_or_rate_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(term in text for term in [
        "429", "503", "rate_limit_exceeded", "over capacity",
        "currently over capacity", "service unavailable",
        "input tokens per minute", "output tokens per minute", "itpm", "otpm",
    ])


def analyze_image(
    client: Groq,
    data: bytes,
    filename: str,
    scene_context: str = "",
) -> dict[str, Any]:
    """
    One-photo systematic evidence sweep.

    - One vision call in the normal path.
    - Rich enough output for up to 10 evidence candidates.
    - Qwen 3.8 strict schema first.
    - Qwen 3.6 plain-text JSON fallback only during provider pressure.
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
image_summary, scene_zones_reviewed, potential_observations,
documentation_suggestions, coverage_note, limitations.

Each potential_observations item must contain:
observation, location_in_image, possible_category, confidence, reason.
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

        time.sleep(4)
        completion = _fallback_request(client, fallback_messages)
        raw = completion.choices[0].message.content or ""
        return _normalize_result(_extract_json(raw))
