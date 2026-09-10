from __future__ import annotations

import base64
import hashlib
import io
import json
from typing import Any

from PIL import Image
from groq import Groq


# ============================================================
# MODEL CONFIGURATION
# ============================================================

VISION_MODEL = "qwen/qwen3.6-27b"


# ============================================================
# HASHING
# ============================================================

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ============================================================
# IMAGE METADATA
# ============================================================

def image_metadata(
    data: bytes,
    filename: str
) -> dict[str, Any]:

    with Image.open(
        io.BytesIO(data)
    ) as image:

        exif = image.getexif()

        return {

            "filename": filename,

            "format": image.format,

            "width": image.width,

            "height": image.height,

            "mode": image.mode,

            "sha256": sha256_bytes(
                data
            ),

            "bytes": len(data),

            "exif_datetime": (
                str(
                    exif.get(
                        306,
                        ""
                    )
                )
                if exif
                else ""
            ),
        }


# ============================================================
# IMAGE -> DATA URL
# ============================================================

def _data_url(
    data: bytes,
    filename: str
) -> str:

    extension = (
        filename
        .lower()
        .rsplit(".", 1)[-1]
    )

    if extension == "png":

        mime = "image/png"

    elif extension == "webp":

        mime = "image/webp"

    else:

        mime = "image/jpeg"

    encoded = base64.b64encode(
        data
    ).decode(
        "utf-8"
    )

    return (
        f"data:{mime};base64,"
        f"{encoded}"
    )


# ============================================================
# JSON PARSER
# ============================================================

def _parse_json_response(
    raw: str
) -> dict[str, Any]:

    raw = (
        raw or ""
    ).strip()

    if not raw:

        raise RuntimeError(
            "Vision model returned an empty response."
        )

    try:

        result = json.loads(
            raw
        )

    except json.JSONDecodeError as exc:

        raise RuntimeError(
            "Vision model returned invalid JSON. "
            f"Beginning of response: {raw[:500]!r}"
        ) from exc

    if not isinstance(
        result,
        dict
    ):

        raise RuntimeError(
            "Vision model response must be a JSON object."
        )

    result.setdefault(
        "image_summary",
        ""
    )

    result.setdefault(
        "potential_observations",
        []
    )

    result.setdefault(
        "documentation_suggestions",
        []
    )

    result.setdefault(
        "limitations",
        []
    )

    return result


# ============================================================
# MAIN VISION REQUEST
# ============================================================

def _request_analysis(
    client: Groq,
    data: bytes,
    filename: str,
    scene_context: str,
    compact: bool = False
) -> dict[str, Any]:

    if compact:

        prompt = f"""
You are SceneGuard AI's forensic image observation assistant.

Scene context:
{scene_context or "No scene description supplied."}

Inspect ONLY visible features.

Rules:
- Never identify a person.
- Never infer guilt.
- Never confirm blood, DNA, fingerprints, drugs,
  explosives, weapons linkage, or any laboratory finding.
- Use words such as visible, apparent, possible,
  potential, or may warrant examination.
- Keep the response very short.
- Maximum 5 observations.
- Maximum 3 documentation suggestions.
- Maximum 3 limitations.

Return ONLY JSON in exactly this structure:

{{
  "image_summary": "one short sentence",
  "potential_observations": [
    {{
      "observation": "short visible observation",
      "possible_category": "biological|digital|latent_print|trace|physical|other",
      "confidence": "low|medium|high",
      "reason": "one short reason"
    }}
  ],
  "documentation_suggestions": [
    "short suggestion"
  ],
  "limitations": [
    "short limitation"
  ]
}}
""".strip()

    else:

        prompt = f"""
You are SceneGuard AI's Multimodal Scene Agent.

This application is a human-in-the-loop forensic
documentation prototype.

INVESTIGATOR SCENE CONTEXT:
{scene_context or "No scene description supplied."}

Your task is to describe visible features that may
require investigator attention.

STRICT FORENSIC RULES:

1. Analyze only what is visibly present.
2. Never identify a person or suspect.
3. Never infer guilt, motive, intent, ownership,
   or offender characteristics.
4. Never state that a visible stain is blood,
   DNA, narcotics, explosive material, chemicals,
   or another scientifically confirmed substance.
5. Never claim that a visible mark is a confirmed
   fingerprint.
6. Never perform laboratory conclusions.
7. Separate visible observation from possible
   forensic relevance.
8. Use cautious terminology:
   visible, apparent, possible, potential,
   may warrant examination.
9. The investigator must verify every proposed
   observation.
10. Keep output concise.
11. Return no more than FIVE potential observations.
12. Each reason must be one short sentence.

Return ONLY one JSON object:

{{
  "image_summary": "brief neutral visual summary",

  "potential_observations": [
    {{
      "observation": "visible observation only",

      "possible_category":
      "biological|digital|latent_print|trace|physical|other",

      "confidence":
      "low|medium|high",

      "reason":
      "brief reason why investigator attention may be warranted"
    }}
  ],

  "documentation_suggestions": [
    "short procedural documentation suggestion"
  ],

  "limitations": [
    "important limitation of image-only analysis"
  ]
}}
""".strip()

    completion = (
        client
        .chat
        .completions
        .create(

            model=VISION_MODEL,

            messages=[
                {
                    "role": "user",
                    "content": [

                        {
                            "type": "text",
                            "text": prompt
                        },

                        {
                            "type": "image_url",
                            "image_url": {
                                "url": _data_url(
                                    data,
                                    filename
                                )
                            }
                        }

                    ]
                }
            ],

            # Visual observation does not need
            # extended reasoning.
            reasoning_effort="none",

            temperature=0,

            # Give JSON enough room to complete.
            max_completion_tokens=3500,

            response_format={
                "type": "json_object"
            }
        )
    )

    raw = (
        completion
        .choices[0]
        .message
        .content
        or ""
    )

    return _parse_json_response(
        raw
    )


# ============================================================
# PUBLIC FUNCTION WITH AUTOMATIC RETRY
# ============================================================

def analyze_image(
    client: Groq,
    data: bytes,
    filename: str,
    scene_context: str = ""
) -> dict[str, Any]:

    first_error = None

    # --------------------------------------------------------
    # ATTEMPT 1
    # Normal forensic prompt
    # --------------------------------------------------------

    try:

        return _request_analysis(

            client=client,

            data=data,

            filename=filename,

            scene_context=scene_context,

            compact=False
        )

    except Exception as exc:

        first_error = exc


    # --------------------------------------------------------
    # ATTEMPT 2
    # Compact fallback prompt
    # --------------------------------------------------------

    try:

        return _request_analysis(

            client=client,

            data=data,

            filename=filename,

            scene_context=scene_context,

            compact=True
        )

    except Exception as second_error:

        raise RuntimeError(
            "SceneGuard Vision Agent failed after "
            "two attempts.\n\n"
            f"First attempt: {first_error}\n\n"
            f"Retry attempt: {second_error}"
        ) from second_error
