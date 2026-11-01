"""
Step 3 - Search with citations (now with hybrid search)

Modes:
  dense   - embedding similarity only (finds meaning, can miss exact terms)
  hybrid  - dense + BM25 keyword search, combined with Reciprocal Rank Fusion

Each result keeps "score" = dense cosine similarity (used by the relevance cutoff)
and "fused" = the ranking score actually used to order hybrid results.

Run:  python search.py "chain-of-thought prompting and model size" --mode hybrid
      python search.py "how is the retriever trained" --paper 2005.11401
"""
import argparse
import json
import re
import sys
from pathlib import Path

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

sys.stdout.reconfigure(encoding="utf-8")

INDEX_DIR = Path("index")
MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_MODE = "hybrid"   # set to "dense" to go back to embeddings only
RRF_K = 60                # standard constant for Reciprocal Rank Fusion

STOPWORDS = {
    "a", "an", "the", "of", "to", "in", "on", "for", "and", "or", "is", "are", "was",
    "were", "be", "by", "with", "as", "at", "it", "its", "that", "this", "from", "how",
    "do", "does", "what", "which", "why", "can", "when", "who", "into", "than", "their",
}


def tokenize(text):
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS]


class PaperSearch:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_NAME)
        self.index = faiss.read_index(str(INDEX_DIR / "papers.faiss"))
        self.chunks = json.loads((INDEX_DIR / "chunks.json").read_text(encoding="utf-8"))
        self.bm25 = BM25Okapi([tokenize(c["text"]) for c in self.chunks])

    def _dense_scores(self, query):
        """Cosine similarity of the query to every chunk (small corpus, so this is cheap)."""
        q = self.model.encode([query], normalize_embeddings=True).astype("float32")
        scores, ids = self.index.search(q, self.index.ntotal)
        dense = np.zeros(self.index.ntotal, dtype="float32")
        dense[ids[0]] = scores[0]
        return dense

    def search(self, query, k=5, paper_id=None, mode=None):
        mode = mode or DEFAULT_MODE
        dense = self._dense_scores(query)
        dense_order = np.argsort(-dense)

        if mode == "dense":
            order, fused = dense_order, dense
        elif mode == "hybrid":
            bm25 = np.array(self.bm25.get_scores(tokenize(query)))
            bm25_order = np.argsort(-bm25)
            fused = np.zeros(len(self.chunks), dtype="float64")
            for rank, idx in enumerate(dense_order):
                fused[idx] += 1.0 / (RRF_K + rank + 1)
            for rank, idx in enumerate(bm25_order):
                fused[idx] += 1.0 / (RRF_K + rank + 1)
            order = np.argsort(-fused)
        else:
            raise ValueError("mode must be 'dense' or 'hybrid'")

        results = []
        for idx in order:
            chunk = self.chunks[int(idx)]
            if paper_id and chunk["paper_id"] != paper_id:
                continue
            results.append({**chunk, "score": float(dense[idx]), "fused": float(fused[idx])})
            if len(results) == k:
                break
        return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--paper", default=None, help="restrict to one paper ID")
    parser.add_argument("--mode", default=None, choices=["dense", "hybrid"])
    parser.add_argument("-k", type=int, default=5)
    args = parser.parse_args()

    engine = PaperSearch()
    for r in engine.search(args.query, k=args.k, paper_id=args.paper, mode=args.mode):
        print(f"[{r['paper_id']}, p.{r['page']}]  score={r['score']:.2f}")
        print(r["text"][:300].replace("\n", " ") + "...\n")


if __name__ == "__main__":
    main()
