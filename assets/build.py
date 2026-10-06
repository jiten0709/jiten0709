"""Generate the profile's SVG cards in the Modern Spectrum theme, one light and one dark file each.

Run: python3 assets/build.py  ->  assets/<name>-light.svg, assets/<name>-dark.svg
README.md switches between them with <picture>, which follows GitHub's theme setting.
"""
import re
from base64 import b64encode
from functools import cache, partial
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape, unescape

OUT = Path(__file__).parent

TOKENS = {
    "light": {
        "surface": "#FFFFFF", "elevated": "#F1F5F9", "border": "#E2E8F0",
        "text": "#0F172A", "text2": "#475569", "muted": "#94A3B8",
        "indigo": "#4F46E5", "teal": "#0891B2", "emerald": "#059669",
        "amber": "#D97706", "rose": "#E11D48", "purple": "#9333EA",
        "tint": 0.10, "glow": 0.08, "name_glow": 0, "accent_text": False,
    },
    "dark": {
        "surface": "#151D2A", "elevated": "#1E293B", "border": "#1E293B",
        "text": "#F8FAFC", "text2": "#94A3B8", "muted": "#64748B",
        "indigo": "#6366F1", "teal": "#22D3EE", "emerald": "#34D399",
        "amber": "#FBBF24", "rose": "#FB7185", "purple": "#C084FC",
        "tint": 0.15, "glow": 0.22, "name_glow": 0.35, "accent_text": True,
    },
}

TECH = [
    ("Languages", "indigo", ["Python", "JavaScript", "TypeScript", "SQL"]),
    ("Generative AI & Agents", "purple", ["LangChain", "LangGraph", "LlamaIndex", "MCP", "RAG", "AI Agents", "Prompt Engineering"]),
    ("LLM Engineering", "teal", ["Hugging Face", "vLLM", "Ollama", "LoRA", "PEFT", "Fine-tuning", "LLM APIs"]),
    ("Evaluation & Observability", "amber", ["RAGAS", "TruLens", "LangSmith"]),
    ("Machine Learning & CV", "rose", ["PyTorch", "TensorFlow", "Scikit-learn", "CNN", "NLP", "OpenCV", "YOLO"]),
    ("Vector Search & Data", "emerald", ["Qdrant", "Pinecone", "Weaviate", "Milvus", "FAISS", "ChromaDB", "LanceDB", "PostgreSQL", "MongoDB"]),
    ("Backend & APIs", "indigo", ["FastAPI", "Flask", "Django", "Node.js", "NestJS", "RESTful APIs"]),
    ("Frontend & AI Interfaces", "purple", ["React.js", "Next.js", "Vue.js", "Streamlit", "Chainlit"]),
    ("Cloud & MLOps", "teal", ["GCP (Vertex AI, AutoML)", "AWS", "Azure", "MLflow", "Docker", "Kubernetes", "CI/CD", "Git"]),
    ("Workflow Automation", "amber", ["n8n", "Make", "Zapier"]),
]

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
# class -> (Google Fonts family, axes, extra CSS). GitHub shows SVGs via <img>, which blocks external
# fonts, so each SVG embeds base64 subsets holding only the glyphs it uses (see font_css).
FONTS = {
    "display": ("Space Grotesk", "wght@700", f"font-family: 'Space Grotesk', {SANS}; font-weight: 700;"),
    "serif": ("Instrument Serif", "ital@1", "font-family: 'Instrument Serif', Georgia, serif; font-style: italic;"),
    "sans": ("Inter", "wght@400;600", f"font-family: Inter, {SANS};"),
    "mono": ("JetBrains Mono", "wght@400", "font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;"),
}
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/120 Safari/537.36"}  # gets woff2, not ttf

CSS = "".join(f"\n.{cls} {{ {rule} }}" for cls, (_, _, rule) in FONTS.items()) + """
.drift { animation: drift 16s ease-in-out infinite alternate; }
@keyframes drift { to { transform: translate(-60px, 30px); } }
.pulse { transform-box: fill-box; transform-origin: center; animation: pulse 2s ease-out infinite; }
@keyframes pulse { from { transform: scale(1); opacity: .7; } to { transform: scale(2.6); opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .drift, .pulse { animation: none; } }
"""

# Monospace advance per em: SF Mono/Menlo ~0.60, Consolas 0.55. Rounded up so chip text never overflows.
CH = 0.61


@cache
def fetch(url):
    with urlopen(Request(url, headers=UA)) as r:
        return r.read()


def font_css(svg):
    """@font-face rules with each family subset (Google Fonts `text=`) to the glyphs its class uses in this SVG."""
    # ponytail: build needs network; cache files under assets/fonts/ if offline builds matter
    out = []
    for cls, (family, axes, _) in FONTS.items():
        found = re.findall(rf'<text class="{cls}"[^>]*>(.*?)</text>', svg)
        text = "".join(sorted(set(unescape(re.sub("<[^>]+>", "", "".join(found))))))
        if text:
            face = fetch("https://fonts.googleapis.com/css2?" + urlencode({"family": f"{family}:{axes}", "text": text})).decode()
            out.append(re.sub(r"url\((.*?)\)", lambda m: f"url(data:font/woff2;base64,{b64encode(fetch(m[1])).decode()})", face))
    return "".join(out)


def chip(x, y, text, accent, t, size=15):
    """One pill: accent tint behind, accent text in dark mode, dark text in light mode (theme rule 2)."""
    w, h, c = round(len(text) * size * CH + size * 1.4), size * 2, t[accent]
    fg = c if t["accent_text"] else t["text"]
    return w, (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}" fill="{c}" fill-opacity="{t["tint"]}" stroke="{c}" stroke-opacity=".4"/>'
        f'<text class="mono" x="{x + w / 2}" y="{y + h / 2 + size * 0.35:.1f}" font-size="{size}" fill="{fg}" text-anchor="middle">{escape(text)}</text>'
    )


def chip_row(x, y, items, t, size=15, gap=10):
    out = []
    for text, accent in items:
        w, s = chip(x, y, text, accent, t, size)
        out.append(s)
        x += w + gap
    return "".join(out)


def frame(w, h, title, t, body, extra_bg=""):
    """Card shell: surface fill, 1px border, a soft drifting indigo tint (no drop shadows)."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="t">
  <title id="t">{escape(title)}</title>
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t['indigo']}"/><stop offset="1" stop-color="{t['purple']}"/></linearGradient>
    <radialGradient id="gi"><stop offset="0" stop-color="{t['indigo']}" stop-opacity="{t['glow']}"/><stop offset="1" stop-color="{t['indigo']}" stop-opacity="0"/></radialGradient>
    <radialGradient id="gp"><stop offset="0" stop-color="{t['purple']}" stop-opacity="{t['glow']}"/><stop offset="1" stop-color="{t['purple']}" stop-opacity="0"/></radialGradient>
    <pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="{t['muted']}" fill-opacity=".3"/></pattern>
    <filter id="blur" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="12"/></filter>
    <clipPath id="c"><rect width="{w}" height="{h}" rx="18"/></clipPath>
  </defs>
  <style>{CSS}</style>
  <g clip-path="url(#c)">
    <rect width="{w}" height="{h}" fill="{t['surface']}"/>{extra_bg}
    <circle class="drift" cx="{w - 60}" cy="0" r="{min(h, 300)}" fill="url(#gi)"/>
  </g>
  <rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="17.5" fill="none" stroke="{t['border']}"/>
{body}
</svg>
"""


def hero(t):
    skills = [("GenAI", "systems", "indigo"), ("Agentic AI", "workflows", "purple"), ("RAG", "pipelines", "teal")]
    tiles = "".join(
        f'<rect x="{x}" y="212" width="292" height="96" rx="14" fill="{t["elevated"]}" stroke="{t["border"]}"/>'
        f'<rect x="{x + 25}" y="229" width="9" height="9" rx="1.5" fill="{t[c]}" transform="rotate(45 {x + 29.5} 233.5)"/>'
        f'<text class="display" x="{x + 22}" y="272" font-size="32" fill="{t[c]}">{name}</text>'
        f'<text class="sans" x="{x + 24}" y="296" font-size="17" fill="{t["text2"]}">{label}</text>'
        for x, (name, label, c) in zip((40, 354, 668), skills)
    )
    name = '<text class="display" x="44" y="140" font-size="64" fill="url(#g)"{}>Jiten Parmar</text>'
    glow = name.format(f' opacity="{t["name_glow"]}" filter="url(#blur)"') if t["name_glow"] else ""
    e = t["emerald"]
    body = f"""
  <rect x="772" y="44" width="180" height="40" rx="20" fill="{e}" fill-opacity="{t['tint']}" stroke="{e}" stroke-opacity=".5"/>
  <circle class="pulse" cx="796" cy="64" r="5" fill="{e}"/>
  <circle cx="796" cy="64" r="5" fill="{e}"/>
  <text class="sans" x="812" y="70" font-size="18" font-weight="600" fill="{e if t['accent_text'] else t['text']}">Open to work</text>
  <text class="mono" x="48" y="72" font-size="18" letter-spacing="4" fill="{t['indigo']}">HI, I'M</text>
  {glow}{name.format('')}
  <text class="serif" x="48" y="182" font-size="30" fill="{t['text2']}">AI Engineer · Published Researcher</text>
  {tiles}"""
    bg = '\n    <rect width="1000" height="340" fill="url(#dots)"/><circle class="drift" cx="120" cy="340" r="280" fill="url(#gp)"/>'
    return frame(1000, 340, "Jiten Parmar, AI Engineer and Published Researcher. Open to work.", t, body, bg)


def project(t, kicker, name, lines, chips, tag=None):
    pitch = "".join(f'<tspan x="28" y="{124 + 24 * i}">{escape(line)}</tspan>' for i, line in enumerate(lines))
    tag_svg = ""
    if tag:
        w, tag_svg = chip(0, 0, tag, "amber", t, size=13)
        tag_svg = f'<g transform="translate({426 - w} 31)">{tag_svg}</g>'
    body = f"""
  <text class="mono" x="28" y="46" font-size="16" letter-spacing="2" fill="{t['indigo']}">{escape(kicker)}</text>
  {tag_svg}<text class="sans" x="452" y="48" font-size="22" fill="{t['muted']}" text-anchor="end">↗</text>
  <text class="display" x="28" y="88" font-size="34" fill="url(#g)">{escape(name)}</text>
  <text class="sans" font-size="18" fill="{t['text2']}">{pitch}</text>
  {chip_row(28, 192, chips, t)}"""
    title = f"{name}{' (work in progress)' if tag else ''}: {' '.join(lines)}"
    return frame(480, 240, title, t, body)


def paper(t):
    title = "Smart Diagnosis: Using CNN to Identify Skin Conditions"
    chips = [("Xception CNN", "rose"), ("15 skin conditions", "teal"), ("56% → 90% val. accuracy", "emerald")]
    body = f"""
  <text class="mono" x="40" y="44" font-size="16" letter-spacing="2" fill="{t['indigo']}">TAYLOR &amp; FRANCIS (CRC PRESS) · 2026</text>
  <text class="sans" x="960" y="46" font-size="20" fill="{t['muted']}" text-anchor="end">DOI ↗</text>
  <text class="display" x="40" y="86" font-size="26" fill="url(#g)">{title}</text>
  <text class="sans" x="40" y="118" font-size="19" fill="{t['text2']}">Artificial Intelligence and Sustainable Innovation</text>
  {chip_row(40, 140, chips, t)}"""
    return frame(1000, 190, f"Published research: {title}. Taylor and Francis (CRC Press), 2026.", t, body)


def tech(t, W=1000, gap=16, pad=24, size=14):
    """2-column grid of category cards; chips wrap inside each card, each row takes its taller card's height."""
    cw, ch = (W - gap) // 2, size * 2

    def layout(x, items):  # -> (chip svg at y=0, chip block height)
        out, cx, cy = [], x + pad, 0
        for text, accent in items:
            w, _ = chip(0, 0, text, accent, t, size)
            if cx + w > x + cw - pad:
                cx, cy = x + pad, cy + ch + 8
            assert cx + w <= x + cw - pad, f"chip wider than card: {text}"
            out.append(chip(cx, cy, text, accent, t, size)[1])
            cx += w + 8
        return "".join(out), cy + ch

    parts, y = [], 0
    for row in (TECH[i:i + 2] for i in range(0, len(TECH), 2)):
        laid = [layout(col * (cw + gap), [(s, accent) for s in items]) for col, (_, accent, items) in enumerate(row)]
        h = 64 + max(bh for _, bh in laid) + pad
        for col, ((cat, accent, _), (chips, _)) in enumerate(zip(row, laid)):
            x = col * (cw + gap)
            parts.append(
                f'<rect x="{x + .5}" y="{y + .5}" width="{cw - 1}" height="{h - 1}" rx="16" fill="{t["surface"]}" stroke="{t["border"]}"/>'
                f'<circle cx="{x + pad + 5}" cy="{y + 34}" r="5" fill="{t[accent]}"/>'
                f'<text class="sans" x="{x + pad + 20}" y="{y + 40}" font-size="17" font-weight="600" fill="{t["text"]}">{escape(cat)}</text>'
                f'<g transform="translate(0 {y + 60})">{chips}</g>'
            )
        y += h + gap
    H = y - gap
    title = "Technical ecosystem. " + " ".join(f"{cat}: {', '.join(items)}." for cat, _, items in TECH)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t">
  <title id="t">{escape(title)}</title>
  <style>{CSS}</style>
  {"".join(parts)}
</svg>
"""


def heading(t, kicker, title, W=1000):
    """Section header: numbered mono kicker, bold title, short indigo→purple rule. Transparent so it sits on the page."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="100" viewBox="0 0 {W} 100" role="img" aria-labelledby="t">
  <title id="t">{escape(title)}</title>
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t['indigo']}"/><stop offset="1" stop-color="{t['purple']}"/></linearGradient></defs>
  <style>{CSS}</style>
  <text class="mono" x="{W / 2}" y="28" font-size="15" letter-spacing="4" fill="{t['indigo']}" text-anchor="middle">{escape(kicker)}</text>
  <text class="display" x="{W / 2}" y="70" font-size="32" fill="{t['text']}" text-anchor="middle">{escape(title)}</text>
  <rect x="{W / 2 - 32}" y="86" width="64" height="4" rx="2" fill="url(#g)"/>
</svg>
"""


HEADINGS = {
    "projects": ("01 · PROJECTS", "Currently Building"),
    "research": ("02 · RESEARCH", "Published Research"),
    "stack": ("03 · STACK", "Technical Ecosystem"),
    "activity": ("04 · ACTIVITY", "GitHub Activity"),
}

CARDS = {
    **{f"heading-{slug}": partial(heading, kicker=k, title=s) for slug, (k, s) in HEADINGS.items()},
    "hero": hero,
    "card-testragic": lambda t: project(
        t, "AI · QA AUTOMATION", "TestRAGic",
        ["Turns unstructured video transcripts", "into structured QA test cases, with", "a multi-provider LLM fallback chain."],
        [("LangChain", "purple"), ("FAISS", "emerald"), ("RAG", "teal")]),
    "card-surakshasetu": lambda t: project(
        t, "AGENTIC AI · INSURANCE", "SurakshaSetu",
        ["Life-insurance advisor where the LLM", "handles the conversation and every", "decision comes from auditable rules."],
        [("FastAPI", "emerald"), ("LangGraph", "purple"), ("Spring Boot", "amber")], tag="WIP"),
    "card-paper": paper,
    "tech": tech,
}

if __name__ == "__main__":
    for mode, t in TOKENS.items():
        for name, make in CARDS.items():
            svg = make(t)
            (OUT / f"{name}-{mode}.svg").write_text(svg.replace("<style>", "<style>" + font_css(svg), 1), encoding="utf-8")
    print(f"wrote {len(CARDS) * len(TOKENS)} SVGs to {OUT}")
