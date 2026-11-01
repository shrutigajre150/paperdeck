"""
Step 6 - Streamlit UI (public version)

Anyone can search the papers for free (retrieval runs locally, no API calls).
To get a written answer, a summary document or a slide deck, visitors paste
their own OpenAI API key in the sidebar. The key lives only in that visitor's
browser session: it is never written to disk, logged, or shared.

Run locally:   streamlit run app.py
(If OPENAI_API_KEY is set in your terminal, it is used and the sidebar box is optional.)
"""
import html
import os
import tempfile
from datetime import date
from pathlib import Path

import streamlit as st
from openai import APIConnectionError, AuthenticationError, OpenAI, OpenAIError, RateLimitError

import ui
from answer import MIN_SCORE, answer_question
from paper_titles import paper_title
from search import PaperSearch
from slides import build_pptx, generate_deck_content, slugify

PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
EXAMPLES = [
    "How does a dense retriever compare to BM25?",
    "Why do models miss information in the middle of long prompts?",
    "How does Self-RAG decide when to retrieve?",
    "What causes hallucination in generated text?",
]

st.set_page_config(page_title="PaperDeck", page_icon="\U0001F4C4", layout="wide")
st.markdown(ui.CSS, unsafe_allow_html=True)


@st.cache_resource(show_spinner="Loading the paper index (first visit only)...")
def load_engine():
    return PaperSearch()


def get_client(key):
    return OpenAI(api_key=key) if key else None


def friendly_error(err):
    if isinstance(err, AuthenticationError):
        return "OpenAI rejected that API key. Check the key in the sidebar and search again."
    if isinstance(err, RateLimitError):
        return "This key is out of credit or rate-limited. Wait a minute or use another key."
    if isinstance(err, APIConnectionError):
        return "PaperDeck couldn't reach OpenAI. Check your connection and search again."
    return f"OpenAI returned an error: {err}"


def summary_markdown(question, answer, results):
    lines = [
        "# PaperDeck summary",
        f"*Generated {date.today():%B %d, %Y}*",
        "",
        "## Question",
        question,
        "",
        "## Answer",
        answer,
        "",
        "## Sources",
    ]
    seen = set()
    for r in results:
        label = f"{r['paper_id']}, p.{r['page']}"
        if label in seen:
            continue
        seen.add(label)
        lines.append(f"- [{label}] {paper_title(r['paper_id'])} - https://arxiv.org/abs/{r['paper_id']}")
    lines += ["", "## Retrieved passages", ""]
    for r in results:
        text = " ".join(r["text"].split())
        lines.append(f"**[{r['paper_id']}, p.{r['page']}]**\n\n> {text}\n")
    return "\n".join(lines)


def source_list_html(results):
    rows = []
    for r in sorted(results, key=lambda r: r["score"], reverse=True):
        pid = r["paper_id"]
        quote = html.escape(" ".join(r["text"].split())[:320])
        rows.append(
            f'<div class="pd-src"><span class="pd-cite">{pid}, p.{r["page"]}</span>'
            f'<a href="https://arxiv.org/abs/{pid}" target="_blank">{html.escape(paper_title(pid))}</a>'
            f'<span class="rel">similarity {r["score"]:.2f}</span>'
            f'<span class="q">&ldquo;{quote}&hellip;&rdquo;</span></div>'
        )
    return "".join(rows)


engine = load_engine()
paper_ids = sorted({c["paper_id"] for c in engine.chunks})

# ---- Sidebar -----------------------------------------------------------------
with st.sidebar:
    st.markdown("### Your OpenAI key")
    env_key = os.getenv("OPENAI_API_KEY", "")
    typed_key = st.text_input(
        "Paste a key to get written answers and slides",
        type="password",
        placeholder="sk-...",
        help="Used only for this browser session. It is never stored or logged.",
    )
    api_key = typed_key.strip() or env_key
    if api_key:
        st.success("Answers, summaries and slides are on.")
    else:
        st.info("Without a key you can still search and read the cited passages.")
    st.caption("Create a key at platform.openai.com/api-keys. One answer plus a deck "
               "costs well under one cent with gpt-4o-mini.")

    st.markdown("### Search settings")
    paper = st.selectbox(
        "Search in",
        ["All papers"] + paper_ids,
        format_func=lambda p: p if p == "All papers" else paper_title(p).split(" (")[0],
    )
    k = st.slider("Passages to read", 3, 12, 8)

# ---- Hero --------------------------------------------------------------------
st.markdown(
    '<div class="pd-hero"><div>'
    "<h1>Ask the papers.<br>Get the page it came from.</h1>"
    "<p>PaperDeck answers questions from research papers and turns the answer into a slide deck. "
    "Every claim is marked with the paper and page that support it.</p>"
    f'<div class="pd-facts"><span><b>{len(paper_ids)}</b>papers</span>'
    f"<span><b>{len(engine.chunks)}</b>passages</span>"
    "<span><b>1.000</b>retrieval MRR</span><span><b>100%</b>valid citations</span></div>"
    f"</div>{ui.img_tag(ui.HERO_SVG, 'A highlighted line in a paper becomes a slide that cites its page')}</div>",
    unsafe_allow_html=True,
)

tab_ask, tab_how, tab_eval, tab_papers = st.tabs(["Ask", "How it works", "Evaluation", "Papers"])

# ---- Ask ---------------------------------------------------------------------
with tab_ask:
    cols = st.columns(len(EXAMPLES))
    for col, example in zip(cols, EXAMPLES):
        if col.button(example, use_container_width=True):
            st.session_state["question_box"] = example

    with st.form("ask"):
        question = st.text_input("Your question", key="question_box",
                                 placeholder="e.g. How is the retriever trained in RAG?")
        submitted = st.form_submit_button("Search the papers", type="primary")

    if submitted and question.strip():
        q = question.strip()
        pid = None if paper == "All papers" else paper
        st.session_state.update(question=q, deck=None, deck_content=None, error=None)
        try:
            if api_key:
                with st.spinner("Reading the papers and writing a cited answer..."):
                    answer, results = answer_question(engine, q, k=k, paper_id=pid,
                                                      client=get_client(api_key))
            else:
                with st.spinner("Searching the papers..."):
                    results = engine.search(q, k=k, paper_id=pid)
                covered = results and max(r["score"] for r in results) >= MIN_SCORE
                answer = None if covered else "Not found in the provided papers."
            st.session_state.update(answer=answer, results=results)
        except OpenAIError as err:
            st.session_state.update(answer=None, results=[], error=friendly_error(err))

    if st.session_state.get("error"):
        st.error(st.session_state["error"])

    if st.session_state.get("question") and "results" in st.session_state:
        question = st.session_state["question"]
        answer = st.session_state.get("answer")
        results = st.session_state["results"]
        not_found = bool(answer) and answer.startswith("Not found")

        if not_found:
            st.warning("These papers don't cover that question. Rephrase it, "
                       "or set 'Search in' to All papers.")
        elif answer:
            st.markdown("### Answer")
            st.markdown(f'<div class="pd-answer">{ui.highlight_citations(answer)}</div>',
                        unsafe_allow_html=True)
        elif results:
            st.info("Here are the most relevant passages. Add an OpenAI key in the sidebar "
                    "to get a written answer, a summary and a slide deck.")

        if answer and not not_found:
            name = slugify(question)
            c1, c2, _ = st.columns([1, 1, 2])
            make_deck = c1.button("Create slide deck", type="primary", use_container_width=True)
            c2.download_button("Download summary (.md)",
                               data=summary_markdown(question, answer, results),
                               file_name=f"{name}_summary.md", mime="text/markdown",
                               use_container_width=True)
            if make_deck:
                try:
                    with st.spinner("Writing slides and checking every citation..."):
                        content = generate_deck_content(question, results, client=get_client(api_key))
                        with tempfile.TemporaryDirectory() as tmp:
                            path = build_pptx(content, results, Path(tmp) / f"{name}.pptx")
                            st.session_state["deck"] = (Path(path).name, Path(path).read_bytes())
                        st.session_state["deck_content"] = content
                except OpenAIError as err:
                    st.error(friendly_error(err))

            if st.session_state.get("deck"):
                content = st.session_state["deck_content"]
                slides = content.get("slides", [])
                st.markdown("### Your deck")
                st.caption(f"{len(slides) + 2} slides: title, {len(slides)} content slides and references. "
                           "Citations that didn't match a retrieved page were removed.")
                thumbs = [(ui.title_slide_svg(content), "Title")] + [
                    (ui.content_slide_svg(s), s.get("title", "")) for s in slides
                ]
                for row in range(0, len(thumbs), 3):
                    cols = st.columns(3)
                    for col, (svg, label) in zip(cols, thumbs[row:row + 3]):
                        col.markdown(f'<div class="pd-thumb">{ui.img_tag(svg, label)}'
                                     f"<p>{html.escape(label)}</p></div>", unsafe_allow_html=True)
                deck_name, data = st.session_state["deck"]
                st.download_button("Download deck (.pptx)", data=data, file_name=deck_name,
                                   mime=PPTX_MIME, type="primary")

        if results and not not_found:
            st.markdown("### Sources")
            st.caption("Strongest match first. The answer and slides draw on all of these passages.")
            st.markdown(source_list_html(results), unsafe_allow_html=True)

# ---- How it works ------------------------------------------------------------
with tab_how:
    st.markdown(f'<div style="background:#fff;padding:1.4rem;border-radius:6px">'
                f'{ui.img_tag(ui.pipeline_svg(), "PaperDeck pipeline from papers to a cited deck")}</div>',
                unsafe_allow_html=True)
    st.markdown("""
**1. Papers.** Each PDF is split into 250-word passages that overlap by 50 words. Every passage keeps its paper ID and page number, and reference lists are skipped.

**2. Hybrid search.** Two searches run side by side: BM25 finds exact terms and acronyms, and MiniLM embeddings in FAISS find passages with the same meaning. Reciprocal Rank Fusion merges the two rankings. If nothing is relevant enough, PaperDeck says the papers don't cover the question instead of guessing.

**3. Grounded answer.** The language model sees only the retrieved passages and must cite `[paper, page]` for every claim.

**4. Citation check.** Any citation pointing to a page that wasn't retrieved is removed before it reaches you.

**5. Deck and summary.** The model returns the slides as structured data, and python-pptx draws them on one fixed template, so every deck looks the same. The references slide lists only verified pages.
""")

# ---- Evaluation --------------------------------------------------------------
with tab_eval:
    st.markdown("### Retrieval")
    st.caption("16 hand-labeled questions with a known source paper, plus 3 out-of-scope questions.")
    st.table({
        "Metric": ["Hit@1", "Hit@5", "MRR", "Out-of-scope rejected", "Average latency"],
        "Dense only": ["15/16", "16/16", "0.969", "3/3", "14 ms"],
        "Hybrid": ["16/16", "16/16", "1.000", "3/3", "16 ms"],
    })
    st.markdown("Hybrid search fixed the one question dense search ranked wrong: *Why do models "
                "struggle to use documents placed in the middle of the prompt?* On a corpus this small, "
                "paper-level retrieval is near its ceiling; passage-level scoring on a larger corpus is next.")
    st.markdown("### Faithfulness")
    st.caption("16 answers scored by hand against a rubric set in advance: 1 fully supported, 0.5 partly, 0 not supported.")
    m1, m2, m3 = st.columns(3)
    m1.metric("Fully supported", "75%")
    m2.metric("Average score", "0.84")
    m3.metric("Valid citations", "35 / 35")
    st.markdown("The one unsupported answer quoted a real result from the DPR paper, 41.5% vs 33.3%, "
                "but attributed the baseline to BM25. The paper compares against ORQA. Catching "
                "claim-level errors like this is the job of the planned verifier step.")

# ---- Papers ------------------------------------------------------------------
with tab_papers:
    st.markdown(f"PaperDeck currently searches {len(paper_ids)} open-access arXiv papers "
                f"({len(engine.chunks)} passages).")
    for pid in paper_ids:
        st.markdown(f"- [{paper_title(pid)}](https://arxiv.org/abs/{pid})")

st.markdown('<p class="pd-note">PaperDeck is a portfolio demo. Answers come only from the indexed papers; '
            "check the cited page before relying on a claim.</p>", unsafe_allow_html=True)
