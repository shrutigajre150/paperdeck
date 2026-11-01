# PaperDeck

Ask a question about a set of research papers and get a **page-cited answer**, a **summary document**, and an **auto-generated slide deck** where every citation is checked against the passages that were actually retrieved.

The demo corpus is 8 open-access arXiv papers on retrieval-augmented generation and LLM reasoning (RAG, DPR, Chain-of-Thought, ReAct, Toolformer, Lost in the Middle, Self-RAG, and a hallucination survey), indexed as 618 passages.

## How it works

```
question
   │
   ▼
Hybrid retrieval ── BM25 keywords + MiniLM embeddings (FAISS), merged with Reciprocal Rank Fusion
   │                 relevance cutoff → out-of-scope questions are rejected, no LLM call
   ▼
Grounded answer ─── LLM answers ONLY from retrieved passages, cites [paper, page]
   │
   ├──► Summary (.md): answer + source list + passages
   │
   └──► Slide agent ─ LLM returns structured JSON (title, bullets, sources, notes)
                      → invented citations dropped → python-pptx renders a fixed template
                      → references slide built from verified citations only
```

| File | Purpose |
|---|---|
| `ingest.py` | Reads PDFs, chunks them (250 words, 50 overlap) with paper + page metadata, skips reference sections, builds the FAISS index |
| `search.py` | Dense and hybrid (BM25 + dense, RRF) search |
| `answer.py` | Grounded, cited answers with a relevance cutoff |
| `slides.py` | Slide agent: structured JSON → citation cleaning → .pptx |
| `app.py` | Streamlit app |
| `ui.py` | Theme, original SVG illustrations, citation highlighting, live slide thumbnails |
| `eval.py` | Retrieval evaluation (Hit@1, Hit@5, MRR, abstention, latency) |
| `faithfulness.py` | Manual faithfulness review + automatic citation-validity check |

## Evaluation

**Retrieval** (16 hand-labeled questions, 3 out-of-scope):

| Metric | Dense | Hybrid |
|---|---|---|
| Hit@1 | 15/16 | 16/16 |
| Hit@5 | 16/16 | 16/16 |
| MRR | 0.969 | 1.000 |
| Out-of-scope rejected | 3/3 | 3/3 |
| Avg latency | 14 ms | 16 ms |

Hybrid search fixed the one question dense search missed ("Why do models struggle to use documents placed in the middle of the prompt?"). At the paper level both modes are near the ceiling on a corpus this small; passage-level relevance on a larger, overlapping corpus is the next step.

**Faithfulness** (16 answers hand-scored against a fixed rubric: 1 / 0.5 / 0):
75% fully supported, 3 partly supported, 1 unsupported; average 0.84. The one failure was a correct number attributed to the wrong baseline, which motivates a per-claim verifier step.

**Citation validity:** 35/35 citations in the latest run pointed to a retrieved page.

## Run it locally

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Search works without an API key. To get answers, summaries and slides, paste an OpenAI API key in the app's sidebar, or set it in the terminal first: `$env:OPENAI_API_KEY="sk-..."`.

To use your own papers: put PDFs in `data/papers/`, run `python ingest.py`, and add their titles to `paper_titles.py`.

## Privacy

Visitors bring their own OpenAI key. It is held only in their browser session and is never stored, logged, or shared.

## Roadmap

- Formatting agent: enforce bullet/word limits and split overflowing slides
- Verifier agent: check each bullet against its source passage before export
- Passage-level retrieval evaluation on a larger corpus
