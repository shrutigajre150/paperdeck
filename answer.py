"""
Step 4 - Grounded answers with citations
Retrieves passages with search.py, then asks an OpenAI model to answer using
ONLY those passages. If the answer isn't in the passages, it must say so.

Setup (PowerShell, once per terminal session):
    $env:OPENAI_API_KEY="your-key-here"

Run:
    python answer.py "How do RAG systems reduce hallucination?"
    python answer.py "What is the training objective?" --paper 2005.11401
"""
import argparse
import os
import sys

from openai import OpenAI

from search import PaperSearch

sys.stdout.reconfigure(encoding="utf-8")

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")   # change if your account uses another model

MIN_SCORE = 0.30   # below this, treat the question as not covered by the papers

SYSTEM_PROMPT = """You answer questions about research papers using ONLY the excerpts provided.
Rules:
- Use only information found in the excerpts. Do not use outside knowledge.
- Cite every claim with the source label in square brackets, exactly as given, e.g. [2005.11401, p.3].
- If the excerpts only partly answer the question, answer what they support and state what is missing.
- If the excerpts contain nothing relevant, reply exactly: Not found in the provided papers.
- Be concise: 3 to 6 sentences."""


def build_context(results):
    return "\n\n".join(
        f"[{r['paper_id']}, p.{r['page']}]\n{r['text']}" for r in results
    )


def answer_question(engine, question, k=8, paper_id=None, client=None):
    """Returns (answer_text, retrieved_chunks)."""
    results = engine.search(question, k=k, paper_id=paper_id)
    if not results or max(r["score"] for r in results) < MIN_SCORE:
        return "Not found in the provided papers.", results

    client = client or OpenAI()   # reads OPENAI_API_KEY from the environment
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Excerpts:\n\n{build_context(results)}\n\nQuestion: {question}",
            },
        ],
    )
    return response.choices[0].message.content.strip(), results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--paper", default=None, help="restrict to one paper ID")
    parser.add_argument("-k", type=int, default=8)
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit('Set your key first:  $env:OPENAI_API_KEY="your-key-here"')

    engine = PaperSearch()
    answer, results = answer_question(engine, args.question, k=args.k, paper_id=args.paper)

    print("\nANSWER\n" + "-" * 60)
    print(answer)
    print("\nSOURCES USED\n" + "-" * 60)
    for r in results:
        print(f"[{r['paper_id']}, p.{r['page']}]  score={r['score']:.2f}")


if __name__ == "__main__":
    main()
