"""
Step 2 - Ingestion
Reads every PDF in data/papers/, splits it into overlapping chunks (keeping the
paper ID and page number), embeds the chunks, and saves a FAISS index.

Run:  python ingest.py
"""
import json
from pathlib import Path

import re

import faiss
import numpy as np
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer

PAPERS_DIR = Path("data/papers")
INDEX_DIR = Path("index")
MODEL_NAME = "all-MiniLM-L6-v2"   # small, free, runs locally
CHUNK_WORDS = 250                 # chunk size in words
OVERLAP_WORDS = 50                # overlap so ideas aren't cut in half


def chunk_words(words, size, overlap):
    step = size - overlap
    for start in range(0, len(words), step):
        piece = words[start:start + size]
        if len(piece) < 40:       # skip tiny trailing fragments
            break
        yield " ".join(piece)

def looks_like_references(text):
    years = len(re.findall(r"\b(?:19|20)\d{2}\b", text))
    markers = sum(text.count(m) for m in ("arXiv", "Proceedings", "pp.", "preprint"))
    return years >= 10 or markers >= 4

def load_chunks():
    chunks = []
    for pdf_path in sorted(PAPERS_DIR.glob("*.pdf")):
        paper_id = pdf_path.stem
        doc = fitz.open(str(pdf_path))
        title = (doc.metadata or {}).get("title") or paper_id
        for page_num, page in enumerate(doc, start=1):
            words = page.get_text().split()
            for piece in chunk_words(words, CHUNK_WORDS, OVERLAP_WORDS):
                if looks_like_references(piece):
                    continue
                chunks.append({
                    "paper_id": paper_id,
                    "title": title,
                    "page": page_num,
                    "text": piece,
                })
    return chunks


def main():
    chunks = load_chunks()
    if not chunks:
        raise SystemExit(f"No text found. Put PDFs in {PAPERS_DIR}/ first.")
    print(f"Loaded {len(chunks)} chunks from {len(set(c['paper_id'] for c in chunks))} papers")

    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(
        [c["text"] for c in chunks],
        normalize_embeddings=True,
        show_progress_bar=True,
    ).astype("float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])   # inner product == cosine (normalized)
    index.add(embeddings)

    INDEX_DIR.mkdir(exist_ok=True)
    faiss.write_index(index, str(INDEX_DIR / "papers.faiss"))
    (INDEX_DIR / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")
    print("Index saved to index/")


if __name__ == "__main__":
    main()
