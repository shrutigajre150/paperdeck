"""
Step 5 - Slide agent
Question -> retrieve passages -> LLM writes a structured deck (JSON) -> python-pptx
renders it with one consistent template. Every slide carries source citations,
and any citation the model invents (not in the retrieved passages) is dropped.

Run:
    python slides.py "How does the RAG model combine a retriever and a generator?"
    python slides.py "How are the retriever and generator trained?" --paper 2005.11401
Output: output/<question>.pptx
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from paper_titles import paper_title

# ---- Template (change these to rebrand every deck at once) -------------------
NAVY = RGBColor(0x1F, 0x2A, 0x44)
ACCENT = RGBColor(0x2E, 0x86, 0xDE)
TEXT = RGBColor(0x22, 0x22, 0x22)
GRAY = RGBColor(0x6B, 0x72, 0x80)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Calibri"

SYSTEM_PROMPT = """You turn research-paper excerpts into a slide deck.
Return JSON only, in exactly this shape:
{"title": str, "subtitle": str,
 "slides": [{"title": str, "bullets": [str], "sources": [str], "notes": str}]}
Rules:
- Use ONLY the excerpts provided. Do not add outside knowledge.
- 4 to 5 content slides, 3 to 4 bullets each, each bullet at most 15 words.
- "sources" must be copied exactly from the excerpt labels, written like: 2005.11401, p.3
  (no square brackets). Only list sources that support that slide.
- "notes" are 2 to 3 sentences of speaker notes.
- If a point is not supported by the excerpts, leave it out."""


# ---- Step A: ask the LLM for structured slide content -----------------------
def generate_deck_content(question, results, client=None):
    from openai import OpenAI
    from answer import MODEL, build_context

    client = client or OpenAI()
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Question: {question}\n\nExcerpts:\n\n{build_context(results)}",
            },
        ],
    )
    content = json.loads(response.choices[0].message.content)
    return clean_citations(content, results)


def clean_citations(content, results):
    """Keep only citations that match a passage we actually retrieved.
    Accepts small format variations from the model, e.g. "[2005.11401, p. 3]",
    "2005.11401 p.3" or "2005.11401, p.3; 2005.11401, p.4"."""
    valid = {f"{r['paper_id']}, p.{r['page']}" for r in results}
    for slide in content.get("slides", []):
        cleaned = []
        for s in slide.get("sources", []):
            for pid, page in re.findall(r"(\d{4}\.\d{4,5})\s*,?\s*p\.?\s*(\d+)", str(s)):
                label = f"{pid}, p.{page}"
                if label in valid and label not in cleaned:
                    cleaned.append(label)
        slide["sources"] = cleaned
    return content


# ---- Step B: render the deck -------------------------------------------------
def add_rect(slide, left, top, width, height, color):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape


def add_text(slide, left, top, width, height, text, size, color,
             bold=False, italic=False, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    run = tf.paragraphs[0].add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = FONT
    run.font.color.rgb = color
    return box


def add_bullets(slide, bullets, left, top, width, height):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    for i, bullet in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(14)
        run = p.add_run()
        run.text = "\u2022  " + bullet
        run.font.size = Pt(24)
        run.font.name = FONT
        run.font.color.rgb = TEXT


def build_pptx(content, results, out_path):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]
    W, H = prs.slide_width, prs.slide_height

    # Title slide
    s = prs.slides.add_slide(blank)
    add_rect(s, 0, 0, W, H, NAVY)
    add_rect(s, Inches(0.9), Inches(3.55), Inches(1.6), Inches(0.08), ACCENT)
    add_text(s, Inches(0.9), Inches(1.6), Inches(11.5), Inches(1.9),
             content.get("title", "Untitled"), 40, WHITE, bold=True,
             anchor=MSO_ANCHOR.BOTTOM)
    add_text(s, Inches(0.9), Inches(3.8), Inches(11.5), Inches(1.2),
             content.get("subtitle", ""), 20, RGBColor(0xC9, 0xD6, 0xEA))

    # Content slides
    for slide_data in content.get("slides", []):
        s = prs.slides.add_slide(blank)
        add_rect(s, 0, 0, W, Inches(1.2), NAVY)
        add_text(s, Inches(0.7), Inches(0.1), Inches(11.9), Inches(1.0),
                 slide_data.get("title", ""), 30, WHITE, bold=True,
                 anchor=MSO_ANCHOR.MIDDLE)
        add_bullets(s, slide_data.get("bullets", []),
                    Inches(0.7), Inches(1.6), Inches(11.9), Inches(4.7))
        if slide_data.get("sources"):
            add_text(s, Inches(0.7), Inches(6.7), Inches(11.9), Inches(0.5),
                     "Sources: " + "; ".join(slide_data["sources"]),
                     12, GRAY, italic=True)
        if slide_data.get("notes"):
            s.notes_slide.notes_text_frame.text = slide_data["notes"]

    # References slide
    used = []
    for sd in content.get("slides", []):
        for src in sd.get("sources", []):
            if src not in used:
                used.append(src)
    titles = {r["paper_id"]: paper_title(r["paper_id"], r.get("title")) for r in results}
    papers = []
    for src in used:
        pid = src.split(",")[0]
        if pid not in papers:
            papers.append(pid)

    s = prs.slides.add_slide(blank)
    add_rect(s, 0, 0, W, Inches(1.2), NAVY)
    add_text(s, Inches(0.7), Inches(0.1), Inches(11.9), Inches(1.0),
             "References", 30, WHITE, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    lines = []
    for pid in papers:
        pages = sorted({int(x.split("p.")[1]) for x in used if x.startswith(pid + ",")})
        lines.append(f"arXiv:{pid}  \u2013  {titles.get(pid, pid)}  (pp. {', '.join(map(str, pages))})")
    if not lines:
        lines = ["No verified citations were returned."]
    box = s.shapes.add_textbox(Inches(0.7), Inches(1.6), Inches(11.9), Inches(5.0))
    tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(12)
        run = p.add_run()
        run.text = line
        run.font.size = Pt(18)
        run.font.name = FONT
        run.font.color.rgb = TEXT

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))
    return out_path


# ---- CLI ---------------------------------------------------------------------
def slugify(text, limit=50):
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")[:limit] or "deck"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--paper", default=None, help="restrict to one paper ID")
    parser.add_argument("-k", type=int, default=8)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit('Set your key first:  $env:OPENAI_API_KEY="your-key-here"')

    from answer import MIN_SCORE
    from search import PaperSearch

    engine = PaperSearch()
    # Same relevance check as answer.py, without paying for an extra LLM call.
    results = engine.search(args.question, k=args.k, paper_id=args.paper)
    if not results or max(r["score"] for r in results) < MIN_SCORE:
        raise SystemExit("The papers don't cover this question, so no deck was generated.")

    content = generate_deck_content(args.question, results)
    out = args.out or f"output/{slugify(args.question)}.pptx"
    build_pptx(content, results, out)
    print(f"Deck saved to {out}")
    print(f"Slides: {len(content.get('slides', []))} content slides + title + references")


if __name__ == "__main__":
    main()
