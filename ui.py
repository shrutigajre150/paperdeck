"""
Visual layer for the PaperDeck app: theme CSS, original SVG illustrations,
citation highlighting and live slide thumbnails. No external images are used.

Design idea: "ink and highlighter". Research papers are ink on white paper;
the one bold colour is the yellow highlighter that marks where every claim
came from. Citations look the same everywhere: in answers, sources and slides.
"""
import base64
import html
import re

INK = "#1B2B4B"       # headings, slide headers
BLUE = "#2E6FD8"      # links, primary actions
SLATE = "#5B6578"     # secondary text
MIST = "#EEF1F5"      # page background
PAPER = "#FFFFFF"     # paper surfaces
HIGHLIGHT = "#FFE066"  # the highlighter: citations only

CITE_RE = re.compile(r"\[(\d{4}\.\d{4,5}),\s*p\.\s*([\d\-–]+(?:\s*[;,]\s*(?:\d{4}\.\d{4,5},\s*)?p\.\s*[\d\-–]+)*)\]")

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,500;8..60,650&family=Source+Sans+3:wght@400;600&display=swap');

html, body, [data-testid="stAppViewContainer"] {{ background: {MIST}; }}
[data-testid="stAppViewContainer"] * {{ font-family: 'Source Sans 3', system-ui, sans-serif; }}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ max-width: 1120px; padding-top: 2rem; }}
h1, h2, h3, .pd-serif {{ font-family: 'Source Serif 4', Georgia, serif !important; color: {INK}; letter-spacing: -0.01em; }}
p, li {{ line-height: 1.55; }}

/* hero */
.pd-hero {{ display: grid; grid-template-columns: 1.05fr 1fr; gap: 2rem; align-items: center;
           background: {PAPER}; border: 1px solid #DCE2EA; border-radius: 6px; padding: 2.2rem 2.4rem; margin-bottom: 1.2rem; }}
.pd-hero h1 {{ font-size: 2.7rem; line-height: 1.08; margin: 0 0 .8rem 0; font-weight: 650; }}
.pd-hero p {{ color: {SLATE}; font-size: 1.12rem; max-width: 34em; margin: 0 0 1rem 0; }}
.pd-hero img {{ width: 100%; height: auto; display: block; }}
.pd-facts {{ display: flex; gap: 1.6rem; flex-wrap: wrap; color: {INK}; font-size: .98rem; }}
.pd-facts b {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 1.35rem; display: block; }}
@media (max-width: 760px) {{ .pd-hero {{ grid-template-columns: 1fr; padding: 1.4rem; }} .pd-hero h1 {{ font-size: 2rem; }} }}

/* the highlighter */
.pd-cite {{ background: linear-gradient(transparent 12%, {HIGHLIGHT} 12%, {HIGHLIGHT} 88%, transparent 88%);
           color: {INK}; font-weight: 600; padding: 0 .3em; border-radius: 2px; white-space: nowrap;
           font-variant-numeric: tabular-nums; }}

/* answer reads like a page of a paper */
.pd-answer {{ background: {PAPER}; border-left: 4px solid {INK}; padding: 1.3rem 1.6rem; border-radius: 0 4px 4px 0;
             font-family: 'Source Serif 4', Georgia, serif !important; font-size: 1.12rem; line-height: 1.7; color: #1d2433; max-width: 46em; }}
.pd-answer * {{ font-family: inherit !important; }}

/* sources as a reference list, not cards */
.pd-src {{ display: grid; grid-template-columns: 9.5rem 1fr; gap: .2rem 1rem; padding: .85rem 0; border-bottom: 1px solid #DCE2EA; }}
.pd-src:last-child {{ border-bottom: none; }}
.pd-src .pd-cite {{ justify-self: start; align-self: start; }}
.pd-src a {{ color: {BLUE}; text-decoration: none; font-weight: 600; }}
.pd-src a:hover {{ text-decoration: underline; }}
.pd-src .q {{ grid-column: 2; color: {SLATE}; font-size: .95rem; }}
.pd-src .rel {{ grid-column: 1; color: {SLATE}; font-size: .85rem; }}
@media (max-width: 760px) {{ .pd-src {{ grid-template-columns: 1fr; }} .pd-src .q, .pd-src .rel {{ grid-column: 1; }} }}

.pd-thumb img {{ width: 100%; border: 1px solid #DCE2EA; border-radius: 3px; background: white; }}
.pd-thumb p {{ color: {SLATE}; font-size: .85rem; margin: .3rem 0 0 0; }}
.pd-note {{ color: {SLATE}; font-size: .92rem; }}

.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{ border-radius: 4px; font-weight: 600; }}
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible {{ outline: 3px solid {HIGHLIGHT}; outline-offset: 2px; }}
[data-testid="stSidebar"] {{ background: {PAPER}; border-right: 1px solid #DCE2EA; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 1.6rem; }}
.stTabs [data-baseweb="tab"] {{ font-size: 1.02rem; }}
</style>
"""


def img_tag(svg, alt):
    data = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f'<img src="data:image/svg+xml;base64,{data}" alt="{html.escape(alt)}">'


def highlight_citations(text):
    """Escape the text, then turn [2005.11401, p.3] style citations into highlighter marks."""
    safe = html.escape(text)
    safe = CITE_RE.sub(lambda m: f'<span class="pd-cite">{m.group(1)}, p.{m.group(2)}</span>', safe)
    paragraphs = [p.strip() for p in safe.split("\n") if p.strip()]
    return "".join(f"<p>{p}</p>" for p in paragraphs)


# ---- Hero illustration: a highlighted line on a paper becomes a cited slide -----
HERO_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 380" role="img">
<defs>
  <marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
    <path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>
</defs>
<g transform="rotate(-5 140 200)"><rect x="40" y="48" width="200" height="270" rx="3" fill="#E3E8EF"/></g>
<g transform="rotate(-1.5 150 200)">
  <rect x="52" y="40" width="210" height="290" rx="3" fill="#fff" stroke="#C9D1DC"/>
  <text x="70" y="66" font-family="Georgia, serif" font-size="10" fill="{SLATE}">arXiv:2005.11401</text>
  <rect x="70" y="78" width="150" height="9" rx="2" fill="{INK}"/>
  <rect x="70" y="93" width="110" height="9" rx="2" fill="{INK}"/>
  <g fill="#C3CBD6">
    <rect x="70" y="118" width="170" height="5" rx="2"/><rect x="70" y="130" width="160" height="5" rx="2"/>
    <rect x="70" y="142" width="172" height="5" rx="2"/><rect x="70" y="154" width="140" height="5" rx="2"/>
  </g>
  <rect x="66" y="168" width="180" height="27" rx="2" fill="{HIGHLIGHT}"/>
  <g fill="#8A6A00"><rect x="70" y="174" width="168" height="5" rx="2"/><rect x="70" y="185" width="120" height="5" rx="2"/></g>
  <g fill="#C3CBD6">
    <rect x="70" y="206" width="166" height="5" rx="2"/><rect x="70" y="218" width="172" height="5" rx="2"/>
    <rect x="70" y="230" width="150" height="5" rx="2"/><rect x="70" y="252" width="170" height="5" rx="2"/>
    <rect x="70" y="264" width="160" height="5" rx="2"/><rect x="70" y="276" width="100" height="5" rx="2"/>
  </g>
  <text x="150" y="314" text-anchor="middle" font-family="Georgia, serif" font-size="10" fill="{SLATE}">3</text>
</g>
<path d="M252 182 C 278 182, 268 198, 294 198" fill="none" stroke="{INK}" stroke-width="2" stroke-dasharray="5 5" marker-end="url(#ah)"/>
<g>
  <rect x="300" y="128" width="236" height="140" rx="4" fill="#fff" stroke="#C9D1DC" transform="translate(12 12)"/>
  <rect x="300" y="128" width="236" height="140" rx="4" fill="#fff" stroke="#C9D1DC"/>
  <path d="M300 132 a4 4 0 0 1 4 -4 h228 a4 4 0 0 1 4 4 v30 h-236 z" fill="{INK}"/>
  <rect x="314" y="140" width="120" height="8" rx="2" fill="#fff"/>
  <circle cx="320" cy="181" r="3" fill="{INK}"/><rect x="330" y="178" width="150" height="6" rx="2" fill="#AEB8C6"/>
  <circle cx="320" cy="199" r="3" fill="{INK}"/><rect x="330" y="196" width="170" height="6" rx="2" fill="#AEB8C6"/>
  <circle cx="320" cy="217" r="3" fill="{INK}"/><rect x="330" y="214" width="130" height="6" rx="2" fill="#AEB8C6"/>
  <rect x="314" y="240" width="92" height="16" rx="2" fill="{HIGHLIGHT}"/>
  <text x="360" y="252" text-anchor="middle" font-family="Arial, sans-serif" font-size="10" font-weight="700" fill="{INK}">2005.11401, p.3</text>
</g>
<g font-family="Arial, sans-serif" font-size="12" fill="{SLATE}">
  <text x="150" y="358" text-anchor="middle">the paper</text>
  <text x="430" y="304" text-anchor="middle">your slide, with the page it came from</text>
</g>
</svg>"""


# ---- Pipeline diagram (a real sequence, so the steps are numbered) ------------
def _step(x, n, title, sub, icon):
    return f"""<g transform="translate({x} 0)">
  <circle cx="70" cy="62" r="44" fill="#fff" stroke="{INK}" stroke-width="2"/>
  <g transform="translate(46 38)" fill="none" stroke="{INK}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">{icon}</g>
  <circle cx="104" cy="28" r="13" fill="{INK}"/>
  <text x="104" y="33" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#fff">{n}</text>
  <text x="70" y="136" text-anchor="middle" font-family="Georgia, serif" font-size="16" font-weight="700" fill="{INK}">{title}</text>
  <text x="70" y="157" text-anchor="middle" font-family="Arial, sans-serif" font-size="12.5" fill="{SLATE}">{sub}</text>
</g>"""


ICONS = {
    "doc": '<path d="M10 4h18l10 10v30H10z"/><path d="M28 4v10h10"/><path d="M16 24h16M16 31h16M16 38h10"/>',
    "search": '<circle cx="21" cy="21" r="12"/><path d="M30 30l11 11"/><path d="M15 21h12"/>',
    "answer": '<path d="M6 8h36v24H22l-10 9v-9H6z"/><path d="M13 17h22M13 24h14"/>',
    "check": '<path d="M24 4l17 6v12c0 11-8 18-17 22C15 40 7 33 7 22V10z"/><path d="M16 24l6 6 11-12"/>',
    "deck": '<rect x="5" y="9" width="38" height="26" rx="2"/><path d="M5 16h38"/><path d="M12 23h18M12 29h12"/><path d="M24 35v8M16 43h16"/>',
}

STEPS = [
    ("doc", "Papers", "618 passages, page-tagged"),
    ("search", "Hybrid search", "keywords + meaning"),
    ("answer", "Grounded answer", "only from passages"),
    ("check", "Citation check", "unretrieved pages dropped"),
    ("deck", "Deck + summary", "fixed template"),
]


def pipeline_svg():
    gap = 214
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {gap * 4 + 160} 175" role="img">']
    for i in range(4):
        x1 = 20 + i * gap + 118
        x2 = 20 + (i + 1) * gap + 22
        parts.append(f'<path d="M{x1} 62 H{x2}" stroke="#AEB8C6" stroke-width="2"/>'
                     f'<path d="M{x2 - 8} 56 L{x2} 62 L{x2 - 8} 68" fill="none" stroke="#AEB8C6" stroke-width="2"/>')
    for i, (icon, title, sub) in enumerate(STEPS):
        parts.append(_step(20 + i * gap, i + 1, title, sub, ICONS[icon]))
    parts.append("</svg>")
    return "".join(parts)


# ---- Live slide thumbnails, drawn from the deck JSON -----------------------
def _wrap(text, width):
    words, lines, line = str(text).split(), [], ""
    for w in words:
        if len(line) + len(w) + 1 > width and line:
            lines.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        lines.append(line)
    return lines


def _t(x, y, s, size, color, weight="400", family="Arial, sans-serif", anchor="start"):
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'fill="{color}" text-anchor="{anchor}">{html.escape(s)}</text>')


def title_slide_svg(content):
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1333 750"><rect width="1333" height="750" fill="#1F2A44"/>']
    lines = _wrap(content.get("title", "Untitled"), 38)[:3]
    y0 = 340 - 64 * (len(lines) - 1)
    for i, line in enumerate(lines):
        out.append(_t(90, y0 + i * 64, line, 54, "#fff", "700"))
    out.append('<rect x="90" y="372" width="160" height="8" fill="#2E86DE"/>')
    for i, line in enumerate(_wrap(content.get("subtitle", ""), 70)[:2]):
        out.append(_t(90, 430 + i * 34, line, 26, "#C9D6EA"))
    out.append("</svg>")
    return "".join(out)


def content_slide_svg(slide):
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1333 750"><rect width="1333" height="750" fill="#fff"/>'
           '<rect width="1333" height="120" fill="#1F2A44"/>']
    out.append(_t(70, 76, (_wrap(slide.get("title", ""), 52) or [""])[0], 40, "#fff", "700"))
    y = 205
    for bullet in slide.get("bullets", [])[:5]:
        lines = _wrap(bullet, 58)[:2]
        out.append('<circle cx="84" cy="%d" r="6" fill="#222"/>' % (y - 10))
        for j, line in enumerate(lines):
            out.append(_t(108, y + j * 40, line, 30, "#222222"))
        y += 40 * len(lines) + 30
    if slide.get("sources"):
        src = "Sources: " + "; ".join(slide["sources"])
        out.append(_t(70, 700, src[:110], 18, "#6B7280"))
    out.append("</svg>")
    return "".join(out)
