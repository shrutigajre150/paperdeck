"""
Step 8 - Manual faithfulness check

Is every claim in an answer actually supported by the passages it cites?
This script makes the manual review quick:

  python faithfulness.py run     -> answers every test question, writes:
                                      faithfulness_review.md   (read this: answer + passages)
                                      faithfulness_scores.csv  (fill in the 'supported' column)
  python faithfulness.py score   -> reads your marks and prints the summary
  python faithfulness.py check   -> lists citations that were not among the retrieved
                                    passages (writes no files)

Scoring rubric (decide it BEFORE you read the answers, then stick to it):
  1   = every claim in the answer is supported by the retrieved passages
  0.5 = mostly supported, but one minor claim is unsupported or on the wrong page
  0   = contains a claim that is unsupported or contradicted by the passages

It also checks automatically how many citations in the answers match a passage
that was really retrieved (citation validity).
"""
import argparse
import csv
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

OUT_MD = Path("faithfulness_review.md")
OUT_CSV = Path("faithfulness_scores.csv")


def extract_citations(text):
    """Return (paper_id, page) pairs from citations such as [2005.11401, p.3],
    [2004.04906, p.1; p.2], [2005.11401, p.3, p.4] or
    [2310.11511, p.1; 2310.11511, p.17]."""
    cites = []
    for group in re.findall(r"\[([^\]]*\bp\.\s*\d[^\]]*)\]", text):
        current_id = None
        for pid, page in re.findall(r"(\d{4}\.\d{4,5})|p\.\s*(\d+)", group):
            if pid:
                current_id = pid
            elif current_id:
                cites.append((current_id, page))
    return cites


def run(force):
    from answer import answer_question
    from eval import CASES
    from search import PaperSearch

    if OUT_CSV.exists() and not force:
        raise SystemExit(
            f"{OUT_CSV} already exists and may contain your marks. "
            "Run with --force to overwrite it."
        )

    engine = PaperSearch()
    md = ["# Faithfulness review\n",
          "Mark each answer in faithfulness_scores.csv: 1, 0.5 or 0 (see rubric in faithfulness.py).\n"]
    rows = []
    cites_total = cites_valid = abstained = 0

    for i, (question, _expected) in enumerate(CASES, start=1):
        answer, results = answer_question(engine, question)
        valid = {(r["paper_id"], str(r["page"])) for r in results}
        found = extract_citations(answer)
        cites_total += len(found)
        cites_valid += sum(1 for c in found if c in valid)
        abstained += answer.startswith("Not found")

        md.append(f"\n---\n\n## Q{i}: {question}\n")
        md.append(f"**Answer:**\n\n{answer}\n")
        md.append("**Retrieved passages:**\n")
        for r in results:
            text = " ".join(r["text"].split())
            md.append(f"**[{r['paper_id']}, p.{r['page']}]** (score {r['score']:.2f})\n\n> {text}\n")
        rows.append([i, question, "", ""])

    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "question", "supported", "notes"])
        writer.writerows(rows)

    print(f"Wrote {OUT_MD} and {OUT_CSV}")
    print(f"Questions answered: {len(CASES)}  (abstained with 'Not found': {abstained})")
    if cites_total:
        print(f"Citation validity: {cites_valid}/{cites_total} citations in answers "
              f"match a retrieved passage ({cites_valid / cites_total:.0%})")
    else:
        print("No citations were found in the answers.")
    print("\nNext: open faithfulness_review.md, read each answer against its passages, "
          "and fill in the 'supported' column of faithfulness_scores.csv.")


def score():
    if not OUT_CSV.exists():
        raise SystemExit("Run `python faithfulness.py run` first.")
    with OUT_CSV.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    marks = []
    for r in rows:
        value = (r.get("supported") or "").strip()
        if value:
            marks.append(float(value))
    if not marks:
        raise SystemExit("No marks found. Fill in the 'supported' column first.")

    n = len(marks)
    full = sum(m == 1 for m in marks)
    partial = sum(m == 0.5 for m in marks)
    zero = sum(m == 0 for m in marks)
    print(f"Reviewed answers:        {n} of {len(rows)}")
    print(f"Fully supported (1):     {full}/{n}  ({full / n:.0%})")
    print(f"Partly supported (0.5):  {partial}/{n}")
    print(f"Not supported (0):       {zero}/{n}")
    print(f"Average score:           {sum(marks) / n:.2f}")


def check():
    """Re-answer the test questions and list any citation that was not among the
    retrieved passages. Writes no files, so your review marks are safe."""
    from answer import answer_question
    from eval import CASES
    from search import PaperSearch

    engine = PaperSearch()
    total = ok = 0
    bad = []
    for i, (question, _expected) in enumerate(CASES, start=1):
        answer, results = answer_question(engine, question)
        valid = {(r["paper_id"], str(r["page"])) for r in results}
        for pid, page in extract_citations(answer):
            total += 1
            if (pid, page) in valid:
                ok += 1
            else:
                retrieved = sorted({int(r["page"]) for r in results if r["paper_id"] == pid})
                bad.append((i, pid, page, retrieved, question))

    print(f"Citations checked: {total}   valid: {ok}   invalid: {len(bad)}")
    for i, pid, page, retrieved, question in bad:
        print(f"\nQ{i}: cited [{pid}, p.{page}] but that page was not retrieved.")
        print(f"     retrieved pages for {pid}: {retrieved if retrieved else 'none'}")
        print(f"     question: {question}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["run", "score", "check"])
    parser.add_argument("--force", action="store_true", help="overwrite existing review files")
    args = parser.parse_args()
    if args.command == "run":
        run(args.force)
    elif args.command == "score":
        score()
    else:
        check()


if __name__ == "__main__":
    main()
