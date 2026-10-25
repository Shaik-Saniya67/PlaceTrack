"""PlaceTrack visual theme: refined, flat and premium. Drop-in replacement for ui/theme.py.

Design language: deep ink background with two soft static glows, hairline borders, restrained violet
accent, an editorial serif for page titles and Inter for everything else. No 3D shapes, no
perpetual animation (only a one-time gentle fade-in). Pure CSS, no JavaScript or images.

The public API is unchanged: inject_theme(). All class names used by ui/components.py and app.py
(pt-hero, pt-eyebrow, pt-metrics, pt-metric, pt-chip, pt-drive-title, pt-sub, pt-userchip, pt-avatar)
are kept, so no other file needs to change.
"""
import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Instrument+Serif:ital@0;1&display=swap');

:root {
  --bg: #07080d;
  --panel: rgba(255,255,255,.028);
  --panel-hi: rgba(255,255,255,.05);
  --line: rgba(255,255,255,.08);
  --line-strong: rgba(255,255,255,.16);
  --ink: #eceef6;
  --ink-soft: #c3c7d9;
  --muted: #8a8fa8;
  --accent: #8b6cff;
  --accent-soft: rgba(139,108,255,.14);
  --cyan: #22d3ee;
  --ok: #6ee7a8;  --bad: #ff8b9f;  --warn: #f5cf7a;  --info: #8fd8ff;  --pink: #f08be0;
  --radius: 16px;
}

/* ---------- canvas ---------- */
html, body, .stApp {
  background: var(--bg) !important;
  color: var(--ink);
  font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
[data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stBottom"] { background: transparent !important; }
[data-testid="stHeader"] { backdrop-filter: blur(10px); border-bottom: 1px solid transparent; }

/* two soft, static light pools: depth without decoration */
.stApp::before {
  content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background:
    radial-gradient(900px 520px at 8% -6%, rgba(139,108,255,.14), transparent 62%),
    radial-gradient(760px 480px at 100% 0%, rgba(34,211,238,.07), transparent 60%);
}
[data-testid="stMain"], [data-testid="stSidebar"], [data-testid="stHeader"] { position: relative; z-index: 1; }

[data-testid="stMainBlockContainer"] {
  max-width: 1180px; padding-top: 2.6rem; padding-bottom: 4rem;
  animation: pt-rise .5s cubic-bezier(.2,.7,.2,1) both;
}
@keyframes pt-rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }

h1, h2, h3, h4 { font-family: 'Inter', sans-serif !important; letter-spacing: -.022em; color: var(--ink); }
h2, h3 { font-weight: 600 !important; }
h3 { font-size: 1.12rem !important; margin-top: .6rem; }
p, li, label, .stMarkdown { color: var(--ink-soft); }
strong, b { color: var(--ink); font-weight: 600; }
a { color: #b6a6ff; text-decoration: none; } a:hover { color: #d2c8ff; text-decoration: underline; }
[data-testid="stCaptionContainer"], .stCaption, small { color: var(--muted) !important; }
hr { border-color: var(--line) !important; margin: 1.6rem 0 !important; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] { background: #090a10 !important; border-right: 1px solid var(--line); }
[data-testid="stSidebar"] > div:first-child { padding-top: .6rem; }
[data-testid="stSidebarNavLink"] {
  border-radius: 10px; margin: 2px 0; padding: .5rem .7rem; color: var(--muted) !important; font-weight: 500;
  transition: background .18s ease, color .18s ease;
}
[data-testid="stSidebarNavLink"]:hover { background: var(--panel-hi); color: var(--ink) !important; }
[data-testid="stSidebarNavLink"][aria-current="page"] {
  background: var(--accent-soft); color: #fff !important; box-shadow: inset 2px 0 0 var(--accent);
}
[data-testid="stSidebarNavSeparator"], [data-testid="stSidebarNav"] span[class*="Header"] { color: var(--muted); letter-spacing: .12em; }
.pt-brand { font-family: 'Instrument Serif', serif; font-size: 1.7rem; color: var(--ink); margin: .2rem 0 1rem; }
.pt-userchip {
  display: flex; gap: .75rem; align-items: center; padding: .75rem .8rem; margin-bottom: .8rem;
  border: 1px solid var(--line); border-radius: 14px; background: var(--panel);
}
.pt-avatar {
  flex: none; width: 38px; height: 38px; border-radius: 50%; display: grid; place-items: center;
  font-weight: 600; font-size: .85rem; color: #fff; letter-spacing: .02em;
  background: linear-gradient(145deg, #8b6cff, #5b46d6); box-shadow: 0 0 0 1px rgba(255,255,255,.18) inset;
}
.pt-userchip b { display: block; font-size: .9rem; line-height: 1.15; color: var(--ink); }
.pt-userchip small { display: block; margin-top: 2px; font-size: .76rem; color: var(--muted); word-break: break-all; }

/* ---------- page header ---------- */
.pt-hero { padding: .2rem 0 1.1rem; margin-bottom: .4rem; border-bottom: 1px solid var(--line); }
.pt-eyebrow {
  display: inline-block; margin-bottom: .75rem; font-size: .7rem; font-weight: 600; letter-spacing: .2em;
  text-transform: uppercase; color: #b6a6ff;
}
.pt-eyebrow::before { content: ""; display: inline-block; width: 22px; height: 1px; margin-right: .6rem; vertical-align: middle; background: #b6a6ff; opacity: .7; }
.pt-hero h1 {
  margin: 0; padding: 0; font-family: 'Instrument Serif', Georgia, serif !important; font-weight: 400 !important;
  font-size: clamp(2.3rem, 4.4vw, 3.5rem); line-height: 1.04; letter-spacing: -.015em; color: #fff;
}
.pt-hero p { margin: .65rem 0 0; max-width: 720px; font-size: 1rem; line-height: 1.6; color: var(--muted); }

/* ---------- metric cards ---------- */
.pt-metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(176px, 1fr)); gap: 14px; margin: 1.3rem 0 1.8rem; }
.pt-metric {
  position: relative; padding: 1.15rem 1.2rem 1.05rem; border: 1px solid var(--line); border-radius: var(--radius);
  background: linear-gradient(180deg, var(--panel-hi), var(--panel));
  transition: border-color .25s ease, transform .25s ease, background .25s ease;
}
.pt-metric::before {
  content: ""; position: absolute; left: 1.2rem; top: 0; width: 34px; height: 2px; border-radius: 0 0 2px 2px;
  background: linear-gradient(90deg, var(--accent), var(--cyan));
}
.pt-metric:hover { border-color: var(--line-strong); transform: translateY(-2px); }
.pt-metric .lbl { display: block; font-size: .7rem; font-weight: 600; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); }
.pt-metric .val {
  display: block; margin: .5rem 0 .2rem; font-size: 2.1rem; font-weight: 600; line-height: 1.1; color: #fff;
  letter-spacing: -.03em; font-variant-numeric: tabular-nums;
}
.pt-metric .hint { display: block; font-size: .78rem; color: var(--muted); }

/* ---------- chips ---------- */
.pt-chip {
  display: inline-block; margin: 0 .35rem .3rem 0; padding: .17rem .65rem; border-radius: 999px;
  font-size: .72rem; font-weight: 600; letter-spacing: .01em; line-height: 1.5;
  color: var(--ink-soft); border: 1px solid var(--line-strong); background: var(--panel);
}
.pt-chip.ok     { color: var(--ok);   border-color: rgba(110,231,168,.3); background: rgba(110,231,168,.07); }
.pt-chip.bad    { color: var(--bad);  border-color: rgba(255,139,159,.3); background: rgba(255,139,159,.07); }
.pt-chip.warn   { color: var(--warn); border-color: rgba(245,207,122,.3); background: rgba(245,207,122,.07); }
.pt-chip.info   { color: var(--info); border-color: rgba(143,216,255,.3); background: rgba(143,216,255,.07); }
.pt-chip.sample { color: var(--pink); border-color: rgba(240,139,224,.32); background: rgba(240,139,224,.07); }
.pt-drive-title { margin: 0 0 .35rem; font-size: 1.12rem; font-weight: 600; letter-spacing: -.015em; color: #fff; }
.pt-sub { font-size: .85rem; color: var(--muted); }

/* ---------- buttons ---------- */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button, .stLinkButton > a {
  border-radius: 11px !important; border: 1px solid var(--line-strong) !important; background: var(--panel) !important;
  color: var(--ink) !important; font-weight: 550 !important; font-size: .9rem !important; letter-spacing: .005em;
  transition: background .18s ease, border-color .18s ease, transform .18s ease, box-shadow .18s ease !important;
}
.stButton > button:hover, .stFormSubmitButton > button:hover, .stLinkButton > a:hover, .stDownloadButton > button:hover {
  background: var(--panel-hi) !important; border-color: rgba(139,108,255,.65) !important; color: #fff !important; transform: translateY(-1px);
}
.stButton > button:active, .stFormSubmitButton > button:active { transform: translateY(0); }
.stButton > button:disabled { opacity: .4; transform: none; }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"], .stFormSubmitButton > button[kind="primaryFormSubmit"] {
  border: 1px solid rgba(255,255,255,.18) !important; color: #fff !important;
  background: linear-gradient(180deg, #9a82ff 0%, #7254f0 100%) !important;
  box-shadow: 0 1px 0 rgba(255,255,255,.28) inset, 0 8px 22px -6px rgba(114,84,240,.55);
}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primaryFormSubmit"]:hover {
  background: linear-gradient(180deg, #a692ff 0%, #7d62f5 100%) !important; box-shadow: 0 1px 0 rgba(255,255,255,.3) inset, 0 12px 26px -6px rgba(114,84,240,.7);
}

/* ---------- inputs: light field, dark text (always readable) ---------- */
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div, [data-baseweb="textarea"],
.stTextInput input, .stNumberInput input, .stDateInput input, .stTimeInput input, .stTextArea textarea,
.stSelectbox [data-baseweb="select"] > div, .stMultiSelect [data-baseweb="select"] > div {
  background: #f3f4f9 !important; color: #0b0d12 !important; border-radius: 11px !important;
}
.stTextInput input, .stNumberInput input, .stDateInput input, .stTimeInput input, .stTextArea textarea,
[data-baseweb="input"] input, [data-baseweb="base-input"] input, [data-baseweb="textarea"] textarea,
[data-baseweb="select"] input {
  color: #0b0d12 !important; -webkit-text-fill-color: #0b0d12 !important; caret-color: #5b46d6 !important;
  background: transparent !important; font-weight: 500;
}
[data-baseweb="select"] *, .stNumberInput button, .stNumberInput button * { color: #0b0d12 !important; }
[data-baseweb="select"] svg, .stNumberInput svg, .stDateInput svg, .stTimeInput svg { fill: #3a3f55 !important; color: #3a3f55 !important; }
::placeholder, input::placeholder, textarea::placeholder { color: #6b7088 !important; -webkit-text-fill-color: #6b7088 !important; opacity: 1 !important; }
input:-webkit-autofill, input:-webkit-autofill:focus {
  -webkit-text-fill-color: #0b0d12 !important; -webkit-box-shadow: 0 0 0 1000px #f3f4f9 inset !important; caret-color: #5b46d6;
}
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] { border: 1px solid rgba(255,255,255,.22) !important; transition: border-color .18s, box-shadow .18s; }
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within, [data-baseweb="textarea"]:focus-within {
  border-color: rgba(139,108,255,.9) !important; box-shadow: 0 0 0 3px rgba(139,108,255,.28);
}
label[data-testid="stWidgetLabel"] p { font-size: .8rem; font-weight: 550; letter-spacing: .01em; color: var(--ink-soft); }
[data-baseweb="tag"] { background: #e3dcff !important; border-radius: 8px !important; }
[data-baseweb="tag"] * { color: #1b1340 !important; }
/* dropdown menus stay dark, so their text stays light */
[data-baseweb="popover"] [role="listbox"], [data-baseweb="popover"] ul { background: #14151f !important; }
[data-baseweb="popover"] li, [data-baseweb="popover"] li * { color: #eceef6 !important; }
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] li[aria-selected="true"] { background: rgba(139,108,255,.22) !important; }

/* ---------- tabs ---------- */
[data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--line); }
button[data-baseweb="tab"] { background: transparent !important; color: var(--muted); font-weight: 550; padding: .55rem .9rem; transition: color .18s; }
button[data-baseweb="tab"]:hover { color: var(--ink); }
button[data-baseweb="tab"][aria-selected="true"] { color: #fff; }
[data-baseweb="tab-highlight"] { background: linear-gradient(90deg, var(--accent), var(--cyan)) !important; height: 2px !important; }
[data-baseweb="tab-border"] { background: transparent !important; }

/* ---------- containers ---------- */
[data-testid="stExpander"] { border: 1px solid var(--line) !important; border-radius: 14px !important; background: var(--panel); overflow: hidden; }
[data-testid="stExpander"] summary { padding: .7rem 1rem; font-weight: 550; color: var(--ink-soft); }
[data-testid="stExpander"] summary:hover { color: #fff; }
[data-testid="stForm"] { border: 1px solid var(--line) !important; border-radius: var(--radius) !important; background: var(--panel); padding: 1.3rem 1.4rem; }
[data-testid="stAlert"] { border-radius: 13px; border: 1px solid var(--line); background: var(--panel-hi); }
[data-testid="stDataFrame"], [data-testid="stTable"] { border: 1px solid var(--line); border-radius: 13px; overflow: hidden; }
[data-testid="stPlotlyChart"] { border-radius: 14px; }
[data-testid="stToast"] { border-radius: 12px; border: 1px solid var(--line-strong); }
[data-testid="stSlider"] [role="slider"] { box-shadow: 0 0 0 4px var(--accent-soft); }

/* ---------- misc ---------- */
::selection { background: rgba(139,108,255,.4); color: #fff; }
::-webkit-scrollbar { width: 9px; height: 9px; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,.14); border-radius: 8px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,.24); }

@media (max-width: 760px) {
  [data-testid="stMainBlockContainer"] { padding-top: 1.4rem; }
  .pt-metrics { grid-template-columns: repeat(2, 1fr); }
}
@media (prefers-reduced-motion: reduce) {
  [data-testid="stMainBlockContainer"] { animation: none; }
  * { transition: none !important; }
}
</style>
"""


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
