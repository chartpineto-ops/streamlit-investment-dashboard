from __future__ import annotations

import streamlit as st


BRAND_COLORS = {
    "background": "#061014",
    "card": "#101B22",
    "card_alt": "#0B171D",
    "border": "#1E3440",
    "pine": "#2F7D3A",
    "pine_bright": "#6DBB5A",
    "pine_dark": "#1F5A2E",
    "navy": "#071A3D",
    "gold": "#E5A72A",
    "text": "#EAF0F2",
    "text_secondary": "#A9B6BC",
    "muted": "#6F7E86",
    "red": "#E57368",
    "warning": "#E5C558",
}


TERMINAL_CSS = """
<style>
:root {
  --bg: #061014;
  --panel: #101B22;
  --panel-2: #0B171D;
  --border: #1E3440;
  --text: #EAF0F2;
  --muted: #A9B6BC;
  --muted-2: #6F7E86;
  --pine: #2F7D3A;
  --pine-bright: #6DBB5A;
  --pine-dark: #1F5A2E;
  --navy: #071A3D;
  --green: #6DBB5A;
  --red: #E57368;
  --yellow: #E5A72A;
}
.stApp {
  background: radial-gradient(circle at top left, rgba(47, 125, 58, 0.22), transparent 28rem), radial-gradient(circle at top right, rgba(7, 26, 61, 0.44), transparent 30rem), var(--bg);
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
  color: var(--pine-bright);
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
  background: linear-gradient(180deg, #061014 0%, #071A3D 160%);
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
.brand-lockup {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  margin: 0.35rem 0 0.25rem;
}
.brand-wordmark {
  font-size: 1.35rem;
  font-weight: 950;
  line-height: 1;
}
.brand-pine { color: var(--pine-bright); }
.brand-terminal { color: var(--text); }
.brand-subtitle {
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 1rem;
}
.rt-card {
  background: linear-gradient(180deg, rgba(16, 27, 34, 0.98), rgba(7, 16, 20, 0.98));
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.85rem 0.95rem;
  box-shadow: 0 0 0 1px rgba(109, 187, 90, 0.04), 0 12px 26px rgba(0,0,0,0.18);
  min-height: 92px;
  height: 100%;
  box-sizing: border-box;
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
  overflow-wrap: anywhere;
}
.rt-caption {
  color: var(--muted);
  font-size: 0.78rem;
  margin-top: 0.22rem;
  line-height: 1.25;
  overflow-wrap: anywhere;
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
  border-color: rgba(109,187,90,0.42);
  background: rgba(109,187,90,0.12);
}
.rt-badge.bad {
  color: var(--red);
  border-color: rgba(229,115,104,0.44);
  background: rgba(229,115,104,0.12);
}
.rt-badge.warn {
  color: var(--yellow);
  border-color: rgba(229,167,42,0.42);
  background: rgba(229,167,42,0.10);
}
.quote-card {
  display: flex;
  gap: 0.85rem;
  align-items: center;
  background: linear-gradient(90deg, rgba(16, 27, 34, 0.98), rgba(7, 26, 61, 0.78));
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
  color: var(--pine-bright);
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
.company-hero-card {
  background: linear-gradient(120deg, rgba(16, 27, 34, 0.98), rgba(7, 26, 61, 0.82));
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 0.9rem 1rem;
  box-shadow: 0 0 0 1px rgba(109, 187, 90, 0.05), 0 16px 30px rgba(0,0,0,0.22);
}
.company-hero-grid {
  display: grid;
  grid-template-columns: minmax(260px, 0.95fr) minmax(320px, 1.45fr) minmax(230px, 0.85fr);
  gap: 1rem;
  align-items: center;
}
.hero-identity {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  min-width: 0;
}
.hero-logo {
  flex: 0 0 auto;
}
.hero-identity-copy {
  min-width: 0;
}
.hero-price {
  color: var(--text) !important;
}
.hero-mini-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.45rem;
}
.hero-mini-stats span {
  border: 1px solid rgba(30, 52, 64, 0.92);
  border-radius: 999px;
  padding: 0.16rem 0.48rem;
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 800;
  white-space: nowrap;
  background: rgba(255,255,255,0.025);
}
.hero-mini-stats strong {
  color: var(--text);
  margin-left: 0.18rem;
}
.hero-quick-read {
  min-width: 0;
  border-left: 1px solid rgba(30, 52, 64, 0.82);
  border-right: 1px solid rgba(30, 52, 64, 0.82);
  padding: 0 1rem;
}
.hero-stat-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.48rem;
  margin-top: 0.48rem;
}
.hero-stat-chip {
  border: 1px solid var(--border);
  border-radius: 9px;
  padding: 0.43rem 0.5rem;
  background: rgba(6,16,20,0.42);
  min-width: 0;
  box-sizing: border-box;
}
.hero-stat-chip span {
  display: block;
  color: var(--muted);
  font-size: 0.66rem;
  font-weight: 850;
  letter-spacing: 0.035em;
  line-height: 1.1;
  text-transform: uppercase;
  margin-bottom: 0.16rem;
}
.hero-stat-chip strong {
  display: block;
  color: var(--text);
  font-size: 0.9rem;
  font-weight: 920;
  line-height: 1.16;
  overflow-wrap: anywhere;
}
.hero-stat-chip.good {
  border-color: rgba(109,187,90,0.42);
  background: rgba(109,187,90,0.10);
}
.hero-stat-chip.good strong { color: var(--green); }
.hero-stat-chip.bad {
  border-color: rgba(229,115,104,0.44);
  background: rgba(229,115,104,0.10);
}
.hero-stat-chip.bad strong { color: var(--red); }
.hero-stat-chip.warn {
  border-color: rgba(229,167,42,0.42);
  background: rgba(229,167,42,0.10);
}
.hero-stat-chip.warn strong { color: var(--yellow); }
.hero-signal-panel {
  display: grid;
  gap: 0.46rem;
  justify-items: stretch;
}
.hero-signal-card {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.46rem 0.56rem;
  background: rgba(255,255,255,0.035);
  min-width: 0;
}
.hero-signal-card span {
  display: block;
  color: var(--muted);
  font-size: 0.66rem;
  font-weight: 850;
  text-transform: uppercase;
  letter-spacing: 0.035em;
  margin-bottom: 0.16rem;
}
.hero-signal-card strong {
  display: block;
  color: var(--text);
  font-size: 0.9rem;
  font-weight: 920;
  line-height: 1.16;
  overflow-wrap: anywhere;
}
.hero-signal-card.good {
  border-color: rgba(109,187,90,0.42);
  background: rgba(109,187,90,0.13);
}
.hero-signal-card.good strong { color: var(--green); }
.hero-signal-card.bad {
  border-color: rgba(229,115,104,0.44);
  background: rgba(229,115,104,0.12);
}
.hero-signal-card.bad strong { color: var(--red); }
.hero-signal-card.warn {
  border-color: rgba(229,167,42,0.42);
  background: rgba(229,167,42,0.12);
}
.hero-signal-card.warn strong { color: var(--yellow); }
.hero-signal-stat-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.42rem;
}
.hero-signal-mini {
  border: 1px solid rgba(30,52,64,0.9);
  border-radius: 8px;
  padding: 0.38rem 0.45rem;
  background: rgba(6,16,20,0.44);
  min-width: 0;
}
.hero-signal-mini span {
  display: block;
  color: var(--muted);
  font-size: 0.64rem;
  font-weight: 850;
  text-transform: uppercase;
}
.hero-signal-mini strong {
  display: block;
  color: var(--text);
  font-size: 0.82rem;
  font-weight: 900;
  margin-top: 0.1rem;
  overflow-wrap: anywhere;
}
.hero-exec-summary {
  border-top: 1px solid rgba(30, 52, 64, 0.82);
  margin-top: 0.9rem;
  padding-top: 0.75rem;
}
.hero-summary-sentence {
  color: var(--text);
  font-size: 1.02rem;
  font-weight: 820;
  line-height: 1.32;
  margin-top: 0.24rem;
  overflow-wrap: anywhere;
}
@media (max-width: 1100px) {
  .company-hero-grid {
    grid-template-columns: 1fr;
    align-items: start;
  }
  .hero-quick-read {
    border-left: 0;
    border-right: 0;
    border-top: 1px solid rgba(30, 52, 64, 0.82);
    border-bottom: 1px solid rgba(30, 52, 64, 0.82);
    padding: 0.85rem 0;
  }
}
@media (max-width: 640px) {
  .hero-stat-grid,
  .hero-signal-stat-grid {
    grid-template-columns: 1fr;
  }
}
.terminal-company-card,
.terminal-scenario-card {
  background: linear-gradient(135deg, rgba(16,27,34,0.98), rgba(11,20,26,0.98));
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: 0 0 0 1px rgba(109,187,90,0.05), 0 18px 34px rgba(0,0,0,0.24);
}
.terminal-company-card {
  padding: 1.05rem 1.1rem;
}
.terminal-header-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(260px, 0.78fr);
  gap: 1.2rem;
  align-items: stretch;
}
.terminal-identity-panel {
  min-width: 0;
}
.terminal-ticker-row {
  display: flex;
  align-items: baseline;
  gap: 0.8rem;
  flex-wrap: wrap;
}
.terminal-ticker {
  color: var(--text);
  font-size: clamp(2.6rem, 5vw, 4.8rem);
  line-height: 0.95;
  font-weight: 980;
  letter-spacing: 0.02em;
}
.terminal-daily-move {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0.22rem 0.58rem;
  font-size: 0.85rem;
  font-weight: 930;
  background: rgba(255,255,255,0.035);
}
.terminal-daily-move.good {
  color: var(--green);
  border-color: rgba(109,187,90,0.42);
  background: rgba(109,187,90,0.10);
}
.terminal-daily-move.bad {
  color: var(--red);
  border-color: rgba(229,115,104,0.42);
  background: rgba(229,115,104,0.10);
}
.terminal-company-name {
  color: var(--text);
  font-size: 1.18rem;
  font-weight: 850;
  margin-top: 0.35rem;
  overflow-wrap: anywhere;
}
.terminal-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.78rem;
}
.terminal-chip {
  display: inline-flex;
  align-items: center;
  border: 1px solid rgba(30,52,64,0.95);
  border-radius: 999px;
  padding: 0.24rem 0.58rem;
  color: var(--text-secondary);
  background: rgba(123,199,232,0.075);
  font-size: 0.72rem;
  font-weight: 900;
  line-height: 1.1;
  text-transform: uppercase;
  white-space: nowrap;
}
.terminal-chip strong {
  margin-left: 0.18rem;
  color: var(--text);
}
.terminal-chip.good {
  color: var(--green);
  border-color: rgba(109,187,90,0.44);
  background: rgba(109,187,90,0.12);
}
.terminal-chip.warn {
  color: var(--yellow);
  border-color: rgba(229,167,42,0.44);
  background: rgba(229,167,42,0.11);
}
.terminal-chip.bad {
  color: var(--red);
  border-color: rgba(229,115,104,0.44);
  background: rgba(229,115,104,0.11);
}
.terminal-sector-line,
.terminal-price-line,
.entry-signal-row {
  color: var(--muted);
  font-size: 0.92rem;
  font-weight: 780;
  margin-top: 0.5rem;
}
.terminal-price-line {
  color: var(--text);
  font-size: 1.02rem;
}
.terminal-price-line span {
  color: var(--muted);
  margin-left: 0.32rem;
}
.entry-signal-badge {
  display: inline-flex;
  align-items: center;
  margin-left: 0.32rem;
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0.18rem 0.56rem;
  background: rgba(255,255,255,0.035);
  color: var(--muted);
  font-size: 0.74rem;
  font-weight: 940;
  letter-spacing: 0.035em;
}
.entry-signal-badge.good {
  color: var(--green);
  border-color: rgba(109,187,90,0.44);
  background: rgba(109,187,90,0.12);
}
.entry-signal-badge.warn {
  color: var(--yellow);
  border-color: rgba(229,167,42,0.44);
  background: rgba(229,167,42,0.12);
}
.entry-signal-badge.bad {
  color: var(--red);
  border-color: rgba(229,115,104,0.44);
  background: rgba(229,115,104,0.12);
}
.terminal-score-panel {
  border: 1px solid rgba(30,52,64,0.96);
  border-radius: 14px;
  padding: 0.95rem;
  background: radial-gradient(circle at top right, rgba(109,187,90,0.14), transparent 42%), rgba(6,16,20,0.54);
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}
.terminal-score-panel.warn {
  background: radial-gradient(circle at top right, rgba(229,167,42,0.16), transparent 42%), rgba(6,16,20,0.54);
}
.terminal-score-panel.bad {
  background: radial-gradient(circle at top right, rgba(229,115,104,0.16), transparent 42%), rgba(6,16,20,0.54);
}
.terminal-score-number {
  color: var(--text);
  font-size: clamp(3rem, 6vw, 5.2rem);
  line-height: 0.9;
  font-weight: 980;
  letter-spacing: -0.02em;
}
.terminal-rating {
  color: var(--green);
  font-size: 1.15rem;
  font-weight: 940;
  margin-top: 0.45rem;
}
.terminal-score-panel.neutral .terminal-rating {
  color: var(--muted);
}
.terminal-score-panel.warn .terminal-rating {
  color: var(--yellow);
}
.terminal-score-panel.bad .terminal-rating {
  color: var(--red);
}
.terminal-score-detail {
  color: var(--muted);
  font-size: 0.84rem;
  font-weight: 850;
  margin-top: 0.24rem;
}
.terminal-score-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.45rem;
  margin-top: 0.85rem;
}
.terminal-score-meta div,
.terminal-stat {
  border: 1px solid rgba(30,52,64,0.92);
  border-radius: 10px;
  background: rgba(11,20,26,0.86);
  padding: 0.48rem 0.55rem;
  min-width: 0;
}
.terminal-score-meta span,
.terminal-stat span {
  display: block;
  color: var(--muted);
  font-size: 0.66rem;
  font-weight: 880;
  letter-spacing: 0.035em;
  text-transform: uppercase;
  margin-bottom: 0.16rem;
}
.terminal-score-meta strong,
.terminal-stat strong {
  display: block;
  color: var(--text);
  font-size: 0.9rem;
  font-weight: 930;
  line-height: 1.15;
  overflow-wrap: anywhere;
}
.terminal-quick-stat-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.55rem;
  margin-top: 0.95rem;
}
.terminal-stat.good strong { color: var(--green); }
.terminal-stat.warn strong { color: var(--yellow); }
.terminal-stat.bad strong { color: var(--red); }
.terminal-scenario-card {
  margin-top: 0.85rem;
  padding: 0.95rem 1.05rem;
}
.terminal-exec-summary {
  border-bottom: 1px solid rgba(30,52,64,0.9);
  padding-bottom: 0.78rem;
  margin-bottom: 0.82rem;
}
.terminal-exec-summary div:last-child {
  color: var(--text);
  font-size: 1.03rem;
  line-height: 1.32;
  font-weight: 830;
  margin-top: 0.24rem;
  overflow-wrap: anywhere;
}
.terminal-scenario-title {
  color: var(--text);
  font-size: 0.95rem;
  font-weight: 940;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin-bottom: 0.55rem;
}
.terminal-scenario-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.7rem;
}
.scenario-card {
  border: 1px solid rgba(30,52,64,0.95);
  border-radius: 12px;
  padding: 0.78rem 0.82rem;
  background: rgba(6,16,20,0.44);
  min-width: 0;
}
.scenario-card.good {
  border-color: rgba(109,187,90,0.34);
}
.scenario-card.warn {
  border-color: rgba(229,167,42,0.38);
}
.scenario-card.bad {
  border-color: rgba(229,115,104,0.36);
}
.scenario-title {
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 900;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.scenario-label {
  color: var(--text);
  font-size: 0.96rem;
  font-weight: 930;
  line-height: 1.18;
  margin-top: 0.24rem;
}
.scenario-card.good .scenario-label { color: var(--green); }
.scenario-card.warn .scenario-label { color: var(--yellow); }
.scenario-card.bad .scenario-label { color: var(--red); }
.scenario-card ul {
  margin: 0.5rem 0 0 1rem;
  padding: 0;
  color: var(--text-secondary);
  font-size: 0.8rem;
  line-height: 1.35;
}
@media (max-width: 1050px) {
  .terminal-header-grid,
  .terminal-scenario-grid {
    grid-template-columns: 1fr;
  }
  .terminal-quick-stat-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 640px) {
  .terminal-score-meta,
  .terminal-quick-stat-row {
    grid-template-columns: 1fr;
  }
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
  background: linear-gradient(180deg, var(--pine-bright), var(--pine)) !important;
  border: 1px solid var(--pine-bright) !important;
  color: #061014 !important;
  font-weight: 850 !important;
}
button[kind="primary"]:hover {
  border-color: var(--yellow) !important;
  box-shadow: 0 0 0 1px rgba(229,167,42,0.22);
}
[data-testid="stSidebar"] button {
  border-color: var(--pine) !important;
}
</style>
"""


def apply_brand_theme() -> None:
    st.markdown(TERMINAL_CSS, unsafe_allow_html=True)


def apply_terminal_style() -> None:
    apply_brand_theme()
