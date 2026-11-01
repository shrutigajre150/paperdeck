"""
Step 7 - Retrieval evaluation: dense-only vs hybrid (dense + BM25), no LLM calls.

For each question we know which paper should contain the answer. Metrics:
  Hit@1     - the top retrieved passage comes from the expected paper
  Hit@5     - the expected paper appears in the top 5 passages
  MRR       - mean of 1/rank of the first passage from the expected paper
  Passed    - best dense score is above the relevance cutoff (would reach the LLM)
  Rejected  - out-of-scope questions that fall below the cutoff
  Latency   - retrieval time only (excludes LLM calls)

Run:  python eval.py
"""
import sys
import time

from search import PaperSearch

try:
    from answer import MIN_SCORE
except ImportError:
    MIN_SCORE = 0.30

sys.stdout.reconfigure(encoding="utf-8")

# (question, expected paper ID). Check these against your papers and add your own!
# Tip: add questions that contain specific terms (names, acronyms, numbers) - that is
# where keyword search is expected to help.
CASES = [
    ("What is retrieval-augmented generation and how does it combine parametric and non-parametric memory?", "2005.11401"),
    ("How does a dense dual-encoder retriever compare to BM25 for open-domain question answering?", "2004.04906"),
    ("How does prompting with intermediate reasoning steps improve arithmetic and commonsense reasoning?", "2201.11903"),
    ("What are intrinsic and extrinsic hallucinations in natural language generation?", "2202.03629"),
    ("How do language models interleave reasoning traces and actions to use external sources?", "2210.03629"),
    ("How can a language model teach itself to call external APIs such as a calculator or search engine?", "2302.04761"),
    ("How does performance change when relevant information is in the middle of a long input context?", "2307.03172"),
    ("How does a model decide when to retrieve and critique its own output using special reflection tokens?", "2310.11511"),
    ("What metrics are used to evaluate hallucination in generated text?", "2202.03629"),
    ("How does chain-of-thought prompting behave as model size increases?", "2201.11903"),
    ("Which approach trains the retriever jointly with the generator?", "2005.11401"),
    ("How are passages encoded and indexed for fast similarity search?", "2004.04906"),
    ("Why do models struggle to use documents placed in the middle of the prompt?", "2307.03172"),
    ("How can a model reduce factual errors by deciding on demand whether to retrieve?", "2310.11511"),
    ("What training or decoding choices lead to unfaithful generated text?", "2202.03629"),
    ("How can a model learn to use tools without human annotation for every example?", "2302.04761"),
]

# Questions the papers cannot answer; these should be rejected.
OUT_OF_SCOPE = [
    "What is the capital of France?",
    "What is a good recipe for chocolate cake?",
    "Who won the 2018 football World Cup?",
]

MODES = ["dense", "hybrid"]


def evaluate(engine, mode):
    hit1 = hit5 = passed = 0
    rr_total = 0.0
    latencies = []
    not_first = []

    for question, expected in CASES:
        t0 = time.perf_counter()
        results = engine.search(question, k=5, mode=mode)
        latencies.append(time.perf_counter() - t0)
        ids = [r["paper_id"] for r in results]
        rank = ids.index(expected) + 1 if expected in ids else None
        hit1 += rank == 1
        hit5 += rank is not None
        rr_total += 1 / rank if rank else 0.0
        best = max((r["score"] for r in results), default=0.0)
        passed += best >= MIN_SCORE
        if rank != 1:
            not_first.append((question, expected, ids[0] if ids else "-", rank))

    rejected = 0
    for question in OUT_OF_SCOPE:
        results = engine.search(question, k=5, mode=mode)
        best = max((r["score"] for r in results), default=0.0)
        rejected += best < MIN_SCORE

    n = len(CASES)
    return {
        "Hit@1": f"{hit1}/{n}",
        "Hit@5": f"{hit5}/{n}",
        "MRR": f"{rr_total / n:.3f}",
        "In-scope passed cutoff": f"{passed}/{n}",
        "Out-of-scope rejected": f"{rejected}/{len(OUT_OF_SCOPE)}",
        "Latency avg (ms)": f"{1000 * sum(latencies) / n:.0f}",
        "Latency max (ms)": f"{1000 * max(latencies):.0f}",
        "_not_first": not_first,
    }


def main():
    engine = PaperSearch()
    engine.search("warm up", k=1)   # so the first timed search isn't slower than the rest

    stats = {mode: evaluate(engine, mode) for mode in MODES}

    print(f"Relevance cutoff (MIN_SCORE) = {MIN_SCORE}")
    print(f"{len(CASES)} in-scope questions, {len(OUT_OF_SCOPE)} out-of-scope questions\n")

    metrics = [k for k in stats[MODES[0]] if not k.startswith("_")]
    print(f"{'Metric':<26}" + "".join(f"{m:>12}" for m in MODES))
    print("-" * (26 + 12 * len(MODES)))
    for metric in metrics:
        print(f"{metric:<26}" + "".join(f"{stats[m][metric]:>12}" for m in MODES))

    for mode in MODES:
        missed = stats[mode]["_not_first"]
        print(f"\nQuestions where the right paper was not ranked first ({mode}): {len(missed)}")
        for question, expected, got, rank in missed:
            print(f"  expected={expected}  top1={got}  rank_of_expected={rank}")
            print(f"  {question}")


if __name__ == "__main__":
    main()
