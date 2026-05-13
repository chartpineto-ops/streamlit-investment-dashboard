from __future__ import annotations

import streamlit as st


TERMINAL_CSS = """
<style>
:root {
  --bg: #071013;
  --panel: #0c171d;
  --panel-2: #101f27;
  --border: #24404d;
  --text: #e8f2f4;
  --muted: #9fb0b6;
  --blue: #7dd3fc;
  --green: #7bd88f;
  --red: #ff7b72;
  --yellow: #f4d35e;
}
.stApp {
  background: radial-gradient(circle at top left, rgba(20, 65, 78, 0.34), transparent 28rem), var(--bg);
  color: var(--text);
}
.block-container {
  max-width: 1480px;
  padding-top: 1.1rem;
  padding-bottom: 2.5rem;
}
h1, h2, h3 {
  letter-spacing: 0;
}
h1 {
  color: var(--blue);
  font-size: 2rem !important;
  margin-bottom: 0.1rem !important;
}
h2 {
  color: var(--text);
  font-size: 1.25rem !important;
}
h3 {
  color: var(--text);
  font-size: 1rem !important;
}
[data-testid="stSidebar"] {
  background: #061015;
  border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] * {
  color: var(--text);
}
.terminal-subtitle {
  color: var(--muted);
  font-size: 0.95rem;
  margin-bottom: 1rem;
}
.rt-card {
  background: linear-gradient(180deg, rgba(18, 34, 42, 0.98), rgba(10, 20, 25, 0.98));
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.85rem 0.95rem;
  box-shadow: 0 0 0 1px rgba(125, 211, 252, 0.03), 0 12px 26px rgba(0,0,0,0.18);
  min-height: 92px;
}
.rt-card.small {
  min-height: 72px;
  padding: 0.7rem 0.8rem;
}
.rt-label {
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.rt-value {
  color: var(--text);
  font-size: 1.36rem;
  font-weight: 850;
  line-height: 1.18;
  margin-top: 0.22rem;
}
.rt-caption {
  color: var(--muted);
  font-size: 0.78rem;
  margin-top: 0.22rem;
}
.rt-good { color: var(--green) !important; }
.rt-bad { color: var(--red) !important; }
.rt-neutral { color: var(--muted) !important; }
.rt-warn { color: var(--yellow) !important; }
.rt-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0.15rem 0.48rem;
  font-size: 0.72rem;
  font-weight: 850;
  text-transform: uppercase;
  color: var(--muted);
  background: rgba(255,255,255,0.035);
  white-space: nowrap;
}
.rt-badge.good {
  color: var(--green);
  border-color: rgba(123,216,143,0.42);
  background: rgba(123,216,143,0.12);
}
.rt-badge.bad {
  color: var(--red);
  border-color: rgba(255,123,114,0.44);
  background: rgba(255,123,114,0.12);
}
.rt-badge.warn {
  color: var(--yellow);
  border-color: rgba(244,211,94,0.42);
  background: rgba(244,211,94,0.10);
}
.quote-card {
  display: flex;
  gap: 0.85rem;
  align-items: center;
  background: linear-gradient(90deg, rgba(17, 33, 42, 0.98), rgba(9, 17, 22, 0.98));
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 0.75rem 0.9rem;
}
.quote-logo {
  width: 58px;
  height: 58px;
  border-radius: 14px;
  border: 1px solid #385c6d;
  background: #0a141a;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  color: var(--blue);
  font-weight: 900;
  font-size: 1.05rem;
}
.quote-logo img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #fff;
}
.quote-main {
  font-size: 1.6rem;
  font-weight: 900;
  line-height: 1.05;
}
.quote-sub {
  color: var(--muted);
  font-size: 0.92rem;
  font-weight: 700;
  margin-top: 0.22rem;
}
.source-line {
  color: var(--muted);
  font-size: 0.78rem;
  margin: 0.25rem 0 0.75rem 0;
}
.section-rule {
  border-top: 1px solid var(--border);
  margin: 1rem 0 0.8rem 0;
}
.stDataFrame {
  border: 1px solid var(--border);
  border-radius: 8px;
}
button[kind="primary"] {
  border: 1px solid #5fa8cc !important;
}
</style>
"""


def apply_terminal_style() -> None:
    st.markdown(TERMINAL_CSS, unsafe_allow_html=True)
