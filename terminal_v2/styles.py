from __future__ import annotations

import streamlit as st


CSS = r"""
<style>
:root {
  --pt-bg: #060a0f;
  --pt-panel: #0b1118;
  --pt-panel-2: #101823;
  --pt-line: #243142;
  --pt-line-soft: #162230;
  --pt-text: #edf2f7;
  --pt-muted: #8f9cac;
  --pt-faint: #5f6d7e;
  --pt-amber: #f4b942;
  --pt-green: #43c981;
  --pt-red: #ff6673;
  --pt-blue: #5aa7ff;
}
html, body, [class*="css"] { font-family: "Segoe UI", Inter, Arial, sans-serif; }
.stApp { background: var(--pt-bg); color: var(--pt-text); }
[data-testid="stHeader"] { background: transparent; height: 0; }
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer { display: none !important; }
[data-testid="stSidebar"] { background: #080d13; border-right: 1px solid var(--pt-line); min-width: 232px; max-width: 232px; }
[data-testid="stSidebar"] > div:first-child { width: 232px; padding-top: 0; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.35rem; }
[data-testid="stSidebar"] .stButton > button {
  height: 36px; border: 0; border-left: 2px solid transparent; border-radius: 0;
  color: #aeb8c5; background: transparent; text-align: left; justify-content: flex-start;
  font-size: 0.79rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase;
}
[data-testid="stSidebar"] .stButton > button:hover { color: white; background: #101923; border-left-color: var(--pt-amber); }
.block-container { max-width: none; padding: 0.65rem 1rem 2.25rem 1rem; }
[data-testid="stVerticalBlock"] { gap: 0.65rem; }
[data-testid="stHorizontalBlock"] { gap: 0.65rem; align-items: stretch; }
h1, h2, h3, h4, p { letter-spacing: 0; }
h1 { font-size: 1.45rem !important; margin: 0 !important; }
h2 { font-size: 1rem !important; }
h3 { font-size: 0.82rem !important; }
.pt-brand { padding: 18px 16px 13px; border-bottom: 1px solid var(--pt-line); margin: 0 -1rem 0.55rem; }
.pt-brand-name { color: white; font-size: 1.03rem; font-weight: 800; letter-spacing: 0; }
.pt-brand-mark { color: var(--pt-amber); margin-right: 7px; }
.pt-brand-sub { color: var(--pt-faint); font-size: 0.62rem; font-weight: 800; letter-spacing: 0.14em; margin-top: 3px; }
.pt-side-label { color: var(--pt-faint); font-size: 0.62rem; font-weight: 800; letter-spacing: 0.12em; margin: 12px 2px 4px; }
.pt-side-foot { margin-top: 16px; padding: 12px 3px 2px; border-top: 1px solid var(--pt-line-soft); color: var(--pt-muted); font-size: 0.68rem; line-height: 1.55; }
.pt-live-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--pt-green); display: inline-block; margin-right: 6px; }
.pt-command-row { display: flex; min-height: 50px; border: 1px solid var(--pt-line); background: #080e15; align-items: center; padding: 0 12px; }
.pt-page-code { color: var(--pt-amber); font: 800 0.72rem Consolas, monospace; letter-spacing: 0.08em; min-width: 92px; }
.pt-page-title { color: white; font-size: 1.08rem; font-weight: 800; }
.pt-page-sub { color: var(--pt-muted); font-size: 0.7rem; margin-left: 12px; }
.pt-asof { margin-left: auto; text-align: right; color: var(--pt-muted); font: 0.67rem Consolas, monospace; }
.pt-panel { background: var(--pt-panel); border: 1px solid var(--pt-line); border-radius: 3px; padding: 12px 14px; min-height: 100%; }
.pt-panel-tight { background: var(--pt-panel); border: 1px solid var(--pt-line); border-radius: 3px; padding: 9px 11px; }
.pt-section-head { display:flex; align-items:center; border-bottom: 1px solid var(--pt-line); padding-bottom: 8px; margin-bottom: 9px; }
.pt-section-title { color: #f5f7fa; font-size: 0.76rem; font-weight: 850; letter-spacing: 0.06em; text-transform: uppercase; }
.pt-section-meta { margin-left:auto; color: var(--pt-muted); font: 0.64rem Consolas, monospace; }
.pt-kpi-grid { display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border:1px solid var(--pt-line); background:var(--pt-panel); }
.pt-kpi { padding: 10px 12px; border-right:1px solid var(--pt-line); min-width:0; }
.pt-kpi:last-child { border-right:0; }
.pt-kpi-label { color:var(--pt-muted); font-size:0.62rem; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; }
.pt-kpi-value { color:var(--pt-text); font:700 1.18rem Consolas, monospace; margin-top:5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.pt-kpi-note { color:var(--pt-muted); font-size:0.66rem; margin-top:4px; }
.pt-up { color:var(--pt-green)!important; }.pt-down{ color:var(--pt-red)!important; }.pt-flat{ color:var(--pt-muted)!important; }.pt-warn{ color:var(--pt-amber)!important; }
.pt-table { width:100%; border-collapse:collapse; table-layout:fixed; }
.pt-table th { color:var(--pt-muted); font-size:0.59rem; text-transform:uppercase; letter-spacing:0.06em; font-weight:800; text-align:left; padding:6px 7px; border-bottom:1px solid var(--pt-line); background:#0c141d; }
.pt-table td { color:#dbe2ea; font-size:0.69rem; padding:7px; border-bottom:1px solid var(--pt-line-soft); vertical-align:middle; overflow:hidden; text-overflow:ellipsis; }
.pt-table tr:last-child td { border-bottom:0; }
.pt-table tr:hover td { background:#101923; }
.pt-mono { font-family:Consolas, "SFMono-Regular", monospace!important; font-variant-numeric:tabular-nums; }
.pt-strong { color:white; font-weight:800; }
.pt-muted { color:var(--pt-muted)!important; }
.pt-badge { display:inline-block; border:1px solid var(--pt-line); border-radius:2px; padding:2px 6px; color:#cdd5df; background:#111a24; font-size:0.58rem; font-weight:800; text-transform:uppercase; letter-spacing:0.04em; white-space:nowrap; }
.pt-badge.ok { color:#76dda3; border-color:#245b3d; background:#0e2419; }
.pt-badge.warn { color:#f4c761; border-color:#6b5322; background:#241d0e; }
.pt-badge.bad { color:#ff8490; border-color:#6d2d35; background:#261217; }
.pt-badge.info { color:#82baff; border-color:#284f79; background:#101f31; }
.pt-tape { overflow:hidden; white-space:nowrap; border:1px solid var(--pt-line); background:#071019; height:34px; display:flex; align-items:center; }
.pt-tape-track { display:inline-flex; min-width:max-content; animation: ptTape 42s linear infinite; }
.pt-tape:hover .pt-tape-track { animation-play-state:paused; }
.pt-tape-item { font:700 0.69rem Consolas,monospace; padding:0 18px; border-right:1px solid var(--pt-line); line-height:32px; }
@keyframes ptTape { from { transform:translateX(-50%); } to { transform:translateX(0); } }
.pt-brief { color:#dbe3ec; font-size:0.76rem; line-height:1.5; }
.pt-brief strong { color:white; }
.pt-call { border-left:3px solid var(--pt-amber); background:#111721; padding:12px 14px; }
.pt-call-label { color:var(--pt-amber); font-size:0.6rem; text-transform:uppercase; font-weight:900; letter-spacing:0.1em; }
.pt-call-value { color:white; font-size:1.5rem; font-weight:850; margin:4px 0; }
.pt-call-copy { color:#bdc7d3; font-size:0.74rem; line-height:1.45; }
.pt-score { display:flex; align-items:center; gap:8px; margin:7px 0; }
.pt-score-label { width:110px; color:var(--pt-muted); font-size:0.63rem; }
.pt-score-track { flex:1; height:4px; background:#1b2938; }
.pt-score-fill { height:4px; background:var(--pt-amber); }
.pt-score-value { width:36px; color:white; text-align:right; font:0.67rem Consolas,monospace; }
.pt-grid-2 { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }
.pt-grid-3 { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; }
.pt-stat { border-top:2px solid var(--pt-line); background:#0d141d; padding:9px 10px; }
.pt-stat.amber { border-top-color:var(--pt-amber); }.pt-stat.green{border-top-color:var(--pt-green)}.pt-stat.red{border-top-color:var(--pt-red)}.pt-stat.blue{border-top-color:var(--pt-blue)}
.pt-stat-label { color:var(--pt-muted); font-size:0.59rem; font-weight:800; text-transform:uppercase; }
.pt-stat-value { color:white; font:800 1rem Consolas,monospace; margin:5px 0 3px; }
.pt-stat-note { color:#aab5c2; font-size:0.64rem; line-height:1.4; }
.pt-risk-row { display:grid; grid-template-columns:105px 82px 1fr; gap:8px; padding:8px 0; border-bottom:1px solid var(--pt-line-soft); align-items:start; }
.pt-risk-row:last-child { border-bottom:0; }
.pt-wire { display:grid; grid-template-columns:82px 88px minmax(260px,1fr) 92px 120px; gap:8px; padding:8px 5px; border-bottom:1px solid var(--pt-line-soft); font-size:0.68rem; align-items:start; }
.pt-wire-head { color:var(--pt-muted); background:#0c141d; font-size:0.58rem; font-weight:800; text-transform:uppercase; }
.pt-source-line { display:flex; gap:8px; align-items:center; color:var(--pt-muted); font-size:0.63rem; }
.pt-integrity { display:grid; grid-template-columns:110px minmax(180px,1fr) 110px 92px 72px; gap:8px; padding:8px; border-bottom:1px solid var(--pt-line-soft); align-items:center; font-size:0.67rem; }
.pt-integrity.head { color:var(--pt-muted); font-size:0.57rem; font-weight:800; text-transform:uppercase; background:#0c141d; }
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stSelectbox"] [data-baseweb="select"] > div {
  background:#0c131c!important; border-color:var(--pt-line)!important; color:var(--pt-text)!important; border-radius:2px!important;
}
.stButton > button { background:#111a24; color:#dfe6ee; border:1px solid #314055; border-radius:2px; min-height:34px; font-weight:750; }
.stButton > button:hover { border-color:var(--pt-amber); color:white; }
.stTabs [data-baseweb="tab-list"] { gap:0; border-bottom:1px solid var(--pt-line); }
.stTabs [data-baseweb="tab"] { border-radius:0; height:34px; color:var(--pt-muted); font-size:0.67rem; font-weight:800; text-transform:uppercase; padding:0 14px; }
.stTabs [aria-selected="true"] { color:var(--pt-amber)!important; border-bottom:2px solid var(--pt-amber); }
[data-testid="stDataFrame"] { border:1px solid var(--pt-line); border-radius:2px; }
[data-testid="stExpander"] { border:1px solid var(--pt-line)!important; border-radius:2px!important; background:var(--pt-panel)!important; }
[data-testid="stMetric"] { background:var(--pt-panel); border:1px solid var(--pt-line); padding:10px; border-radius:2px; }
[data-testid="stMetricValue"] { font-family:Consolas,monospace; font-size:1.08rem; }
@media (max-width: 900px) {
  [data-testid="stSidebar"] { min-width:190px; max-width:190px; }
  [data-testid="stSidebar"] > div:first-child { width:190px; }
  .block-container { padding-left:0.55rem; padding-right:0.55rem; }
  .pt-page-sub, .pt-asof { display:none; }
  .pt-kpi-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .pt-kpi:nth-child(2) { border-right:0; }
  .pt-kpi:nth-child(-n+2) { border-bottom:1px solid var(--pt-line); }
  .pt-grid-2,.pt-grid-3 { grid-template-columns:1fr; }
  .pt-wire { grid-template-columns:66px 66px minmax(150px,1fr); }
  .pt-wire > :nth-child(n+4) { display:none; }
  .pt-integrity { grid-template-columns:80px minmax(120px,1fr) 74px; }
  .pt-integrity > :nth-child(n+4) { display:none; }
}
</style>
"""


def inject_styles() -> None:
    st.markdown(CSS, unsafe_allow_html=True)

