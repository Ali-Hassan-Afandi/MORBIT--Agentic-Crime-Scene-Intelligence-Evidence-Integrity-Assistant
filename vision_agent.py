from __future__ import annotations

import base64
import hashlib
import io
import json
from typing import Any

from PIL import Image
from groq import Groq

# Keep this in one place so it can be changed if Groq retires/renames a model.
VISION_MODEL = "qwen/qwen3.6-27b"


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


def analyze_image(
    client: Groq,
    data: bytes,
    filename: str,
    scene_context: str = "",
) -> dict[str, Any]:
    prompt = f"""
You are SceneGuard AI's Multimodal Scene Agent.
This is a human-in-the-loop forensic documentation prototype.

Rules:
- Analyze visible features only.
- Never identify a person or suspect.
- Never infer guilt.
- Never claim that an apparent stain is blood, DNA, narcotics, explosive material, or another scientifically confirmed substance.
- Never claim a visible mark is a confirmed fingerprint.
- Use cautious language: visible, apparent, possible, potential, may warrant examination.
- Separate observation from interpretation.
- The investigator must verify every proposed observation.

Investigator scene context:
{scene_context or "No scene context supplied."}

Return ONLY one valid JSON object:
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
""".strip()

    completion = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": _data_url(data, filename)}},
            ],
        }],
        temperature=0.1,
        max_completion_tokens=1800,
        response_format={"type": "json_object"},
    )

    raw = completion.choices[0].message.content or ""
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Vision model returned invalid JSON. Beginning of response: {raw[:400]!r}"
        ) from exc
