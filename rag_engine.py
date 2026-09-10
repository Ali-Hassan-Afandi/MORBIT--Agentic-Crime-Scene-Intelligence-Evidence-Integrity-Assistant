from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SUPPORTED = {".pdf", ".txt", ".md"}


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def chunk_text(text: str, chunk_size: int = 950, overlap: int = 180) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def infer_document_type(filename: str) -> str:
    name = filename.lower()
    if "fee" in name or "gazette" in name or "challan" in name:
        return "fee_or_payment"
    if "sop" in name or "procedure" in name:
        return "sop_or_procedure"
    if "guideline" in name or "handbook" in name or "pre-requisite" in name or "prerequisite" in name:
        return "guideline"
    if "request form" in name or "submission form" in name or "form" in name:
        return "form"
    if "act" in name or "policy" in name:
        return "act_or_policy"
    if "checklist" in name:
        return "checklist"
    if "guide" in name or "manual" in name:
        return "guide_or_manual"
    return "reference"


def load_manifest_optional(knowledge_dir: Path) -> dict[str, Any]:
    path = knowledge_dir / "manifest.json"
    if not path.exists():
        return {"sources": []}
    raw = path.read_text(encoding="utf-8-sig", errors="strict")
    if not raw.strip():
        return {"sources": []}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Do not take the whole application down because one optional metadata file is malformed.
        return {"sources": []}
    if not isinstance(data, dict):
        return {"sources": []}
    if not isinstance(data.get("sources"), list):
        data["sources"] = []
    return data


def _manifest_lookup(root: Path) -> dict[str, dict[str, Any]]:
    manifest = load_manifest_optional(root)
    lookup: dict[str, dict[str, Any]] = {}
    for source in manifest.get("sources", []):
        rel = str(source.get("file", "")).replace("\\", "/").strip()
        if rel:
            lookup[rel.lower()] = source
    return lookup


def discover_sources(knowledge_dir: str | Path, agency: str = "BOTH") -> list[dict[str, Any]]:
    """
    Automatically discovers supported files under knowledge/NFA and knowledge/PFSA.

    manifest.json is OPTIONAL. If a matching manifest entry exists, its title/url/
    verification metadata is used. Otherwise safe metadata is inferred from the file.
    """
    root = Path(knowledge_dir)
    if not root.exists():
        raise RuntimeError(f"Knowledge directory not found: {root.resolve()}")

    wanted = agency.upper()
    if wanted not in {"NFA", "PFSA", "BOTH", "ALL"}:
        raise ValueError("agency must be NFA, PFSA, BOTH or ALL")

    manifest_lookup = _manifest_lookup(root)
    agencies = ["NFA", "PFSA"] if wanted in {"BOTH", "ALL"} else [wanted]
    found: list[dict[str, Any]] = []

    for agency_name in agencies:
        folder = root / agency_name
        if not folder.exists():
            continue

        for path in sorted(folder.rglob("*"), key=lambda p: p.name.lower()):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED:
                continue
            if path.name.startswith("~$"):
                continue

            rel = path.relative_to(root).as_posix()
            meta = manifest_lookup.get(rel.lower(), {})

            found.append({
                "source_id": meta.get("source_id") or f"{agency_name.lower()}_{hashlib.sha1(rel.encode()).hexdigest()[:10]}",
                "title": meta.get("title") or path.stem,
                "agency": agency_name,
                "authority": meta.get("authority") or (
                    "National Forensics Agency, Pakistan"
                    if agency_name == "NFA"
                    else "Punjab Forensic Science Agency"
                ),
                "url": meta.get("url", ""),
                "verification": meta.get("verification", "local-public-source"),
                "document_type": meta.get("document_type") or infer_document_type(path.name),
                "file": rel,
                "filename": path.name,
                "sha256": meta.get("sha256") or sha256_file(path),
                "size_bytes": path.stat().st_size,
            })

    if not found:
        raise RuntimeError(
            f"No supported files were discovered for {agency}. "
            f"Expected PDFs/TXT/MD under {root / 'NFA'} and/or {root / 'PFSA'}."
        )
    return found


def knowledge_fingerprint(knowledge_dir: str | Path, agency: str = "BOTH") -> str:
    sources = discover_sources(knowledge_dir, agency)
    joined = "|".join(
        f"{s['file']}:{s['size_bytes']}:{s['sha256']}" for s in sources
    )
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def knowledge_inventory(knowledge_dir: str | Path = "knowledge") -> dict[str, list[dict[str, Any]]]:
    inventory: dict[str, list[dict[str, Any]]] = {"NFA": [], "PFSA": []}
    root = Path(knowledge_dir)
    for agency in inventory:
        try:
            inventory[agency] = discover_sources(root, agency)
        except RuntimeError:
            inventory[agency] = []
    return inventory


def _extract_pdf(path: Path, base: dict[str, Any]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        # Invalid/unreadable PDFs are skipped instead of poisoning the vector index.
        base["load_warning"] = f"Could not open PDF: {exc}"
        return docs

    for page_no, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        for idx, chunk in enumerate(chunk_text(page_text), start=1):
            docs.append({
                **base,
                "text": chunk,
                "page": page_no,
                "chunk": idx,
            })
    return docs


def load_corpus(knowledge_dir: str | Path, agency: str = "BOTH") -> list[dict[str, Any]]:
    root = Path(knowledge_dir)
    sources = discover_sources(root, agency)
    docs: list[dict[str, Any]] = []

    for source in sources:
        path = root / source["file"]
        base = {
            "source_id": source["source_id"],
            "title": source["title"],
            "filename": source["filename"],
            "agency": source["agency"],
            "authority": source["authority"],
            "url": source["url"],
            "verification": source["verification"],
            "document_type": source["document_type"],
            "sha256": source["sha256"],
            "file": source["file"],
        }

        if path.suffix.lower() == ".pdf":
            docs.extend(_extract_pdf(path, base))
        else:
            try:
                text = path.read_text(encoding="utf-8-sig", errors="ignore")
            except Exception:
                continue
            for idx, chunk in enumerate(chunk_text(text), start=1):
                docs.append({
                    **base,
                    "text": chunk,
                    "page": None,
                    "chunk": idx,
                })

    if not docs:
        raise RuntimeError(
            f"Files were discovered for {agency}, but no extractable text was found. "
            "Scanned-image PDFs may require OCR before they can be used by this RAG pipeline."
        )
    return docs


class ForensicRAG:
    def __init__(
        self,
        knowledge_dir: str | Path = "knowledge",
        agency: str = "BOTH",
        embed_model: str = EMBED_MODEL,
    ):
        self.knowledge_dir = str(knowledge_dir)
        self.agency = agency.upper()
        self.embed_model = embed_model
        self.documents = load_corpus(knowledge_dir, self.agency)

        self.model = SentenceTransformer(embed_model)
        texts = [d["text"] for d in self.documents]
        vectors = self.model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
        ).astype("float32")

        if vectors.ndim != 2 or vectors.shape[0] == 0:
            raise RuntimeError("Embedding model returned no indexable vectors.")

        faiss.normalize_L2(vectors)
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)

    def search(self, query: str, k: int = 8) -> list[dict[str, Any]]:
        query = clean_text(query)
        if not query:
            return []

        q = self.model.encode(
            [query],
            show_progress_bar=False,
            convert_to_numpy=True,
        ).astype("float32")
        faiss.normalize_L2(q)

        k = max(1, min(int(k), len(self.documents)))
        scores, indices = self.index.search(q, k)

        results: list[dict[str, Any]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            item = dict(self.documents[int(idx)])
            item["score"] = float(score)
            results.append(item)
        return results


def make_context(results: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for i, r in enumerate(results, start=1):
        page = f" | page {r['page']}" if r.get("page") else ""
        blocks.append(
            f"[S{i}] {r.get('title')} | {r.get('agency')} | "
            f"{r.get('authority')}{page}\n"
            f"Document type: {r.get('document_type')}\n"
            f"Verification: {r.get('verification')}\n"
            f"Local file: {r.get('file')}\n"
            f"SHA-256: {r.get('sha256')}\n"
            f"URL: {r.get('url') or 'Not recorded in manifest'}\n"
            f"Excerpt: {r.get('text')}"
        )
    return "\n\n".join(blocks)
