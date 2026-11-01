"""Readable titles for the papers in data/papers/.
Most arXiv PDFs have no title in their metadata, so ingest.py stores the arXiv ID
as the title. This lookup is used for the references slide and the app instead.
Add a line here whenever you add a new paper."""

PAPER_TITLES = {
    "2004.04906": "Dense Passage Retrieval for Open-Domain Question Answering (Karpukhin et al., 2020)",
    "2005.11401": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks (Lewis et al., 2020)",
    "2201.11903": "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models (Wei et al., 2022)",
    "2202.03629": "Survey of Hallucination in Natural Language Generation (Ji et al., 2022)",
    "2210.03629": "ReAct: Synergizing Reasoning and Acting in Language Models (Yao et al., 2022)",
    "2302.04761": "Toolformer: Language Models Can Teach Themselves to Use Tools (Schick et al., 2023)",
    "2307.03172": "Lost in the Middle: How Language Models Use Long Contexts (Liu et al., 2023)",
    "2310.11511": "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection (Asai et al., 2023)",
}


def paper_title(paper_id, fallback=None):
    return PAPER_TITLES.get(paper_id) or fallback or paper_id
