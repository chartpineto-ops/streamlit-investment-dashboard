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
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.rt-value {
  color: var(--text);
  font-size: 1.48rem;
  font-weight: 850;
  line-height: 1.18;
  margin-top: 0.22rem;
  overflow-wrap: anywhere;
}
.rt-caption {
  color: var(--muted);
  font-size: 0.86rem;
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
  font-size: 0.78rem;
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
.pt-hero-card,
.pt-scenario-card {
  box-sizing: border-box;
}
.pt-identity-lockup,
.pt-logo-column,
.pt-company-logo,
.pt-logo-placeholder {
  box-sizing: border-box;
  flex: 0 0 auto;
  box-shadow: 0 10px 22px rgba(0,0,0,0.22);
}
.pt-company-logo img {
  display: block;
}
.pt-company-header-logo {
  width: 72px !important;
  height: 72px !important;
  min-width: 72px !important;
  border-radius: 16px !important;
  font-size: 1.2rem !important;
  box-shadow: 0 10px 22px rgba(0,0,0,0.24);
}
.pt-quarterly-metric-card {
  min-height: 150px !important;
  display: flex;
  flex-direction: column;
}
.pt-quarterly-metric-card .rt-caption {
  min-height: 2.2rem;
}
.pt-trend-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.46rem;
  border-top: 1px solid var(--border);
  margin-top: auto;
  padding-top: 0.58rem;
}
.pt-trend-chip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.35rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: rgba(255,255,255,0.025);
  padding: 0.32rem 0.42rem;
  min-width: 0;
}
.pt-trend-period {
  color: var(--muted);
  font-size: 0.76rem;
  font-weight: 850;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.pt-trend-value {
  font-size: 0.88rem;
  font-weight: 900;
  white-space: nowrap;
}
.pt-trend-good .pt-trend-value {
  color: var(--green);
}
.pt-trend-bad .pt-trend-value {
  color: var(--red);
}
.pt-trend-neutral .pt-trend-value {
  color: var(--muted);
}
.pt-company-dashboard {
  margin-top: 0.8rem;
}
.pt-dashboard-top-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(380px, 1fr);
  gap: 1rem;
  align-items: stretch;
}
.pt-company-identity-card,
.pt-score-summary-card,
.pt-executive-banner,
.pt-financial-highlights-card,
.pt-quick-snapshot-card,
.pt-scenario-decision-card {
  background: linear-gradient(135deg, rgba(16,27,34,0.98), rgba(7,26,61,0.55));
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: 0 18px 34px rgba(0,0,0,0.20);
  box-sizing: border-box;
}
.pt-company-identity-card {
  padding: 1.22rem 1.35rem 1.14rem;
  min-height: 330px;
}
.pt-identity-row {
  display: flex;
  align-items: center;
  gap: 1.22rem;
  min-width: 0;
}
.pt-dashboard-logo {
  border-radius: 18px !important;
  box-shadow: 0 10px 24px rgba(0,0,0,0.28);
  background: rgba(234,240,242,0.96) !important;
  border-color: rgba(169,182,188,0.72) !important;
}
.pt-dashboard-logo img,
.pt-company-logo img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  image-rendering: auto;
}
.pt-identity-main {
  min-width: 0;
}
.pt-ticker-line {
  display: flex;
  align-items: center;
  gap: 0.95rem;
  flex-wrap: wrap;
}
.pt-dashboard-ticker {
  color: var(--text);
  font-size: clamp(3.1rem, 5.2vw, 5.05rem);
  font-weight: 980;
  line-height: 0.9;
  letter-spacing: 0.01em;
}
.pt-change-badge {
  border: 1px solid rgba(30,52,64,0.95);
  border-radius: 999px;
  padding: 0.2rem 0.58rem;
  font-size: 0.9rem;
  font-weight: 940;
  background: rgba(255,255,255,0.035);
  white-space: nowrap;
}
.pt-change-badge.good {
  color: var(--green);
  border-color: rgba(109,187,90,0.48);
  background: rgba(109,187,90,0.12);
}
.pt-change-badge.bad {
  color: var(--red);
  border-color: rgba(229,115,104,0.48);
  background: rgba(229,115,104,0.12);
}
.pt-change-badge.neutral {
  color: var(--muted);
}
.pt-dashboard-company {
  color: var(--text);
  font-size: 1.28rem;
  font-weight: 850;
  margin-top: 0.45rem;
  overflow-wrap: anywhere;
}
.pt-dashboard-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-top: 1rem;
}
.pt-dashboard-info-row {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(150px, 0.7fr) minmax(150px, 0.7fr);
  gap: 0.8rem;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  margin-top: 1.08rem;
  padding: 0.84rem 0;
}
.pt-dashboard-info-row div {
  min-width: 0;
}
.pt-dashboard-info-row span,
.pt-score-detail-row span {
  display: block;
  color: var(--muted);
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.pt-dashboard-info-row strong {
  display: block;
  color: var(--text);
  font-size: 0.98rem;
  line-height: 1.25;
  margin-top: 0.2rem;
  overflow-wrap: anywhere;
}
.pt-dashboard-info-row em {
  color: var(--muted-2);
  font-style: normal;
  margin-left: 0.25rem;
}
.pt-dashboard-stat-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.58rem;
  margin-top: 0.86rem;
}
.pt-stat-note {
  color: var(--muted);
  font-size: 0.76rem;
  font-weight: 760;
  margin-top: 0.18rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pt-score-summary-card {
  border-color: rgba(229,167,42,0.55);
  padding: 1.08rem 1.14rem;
  display: grid;
  grid-template-columns: minmax(250px, 1fr) minmax(230px, 1fr);
  gap: 1.14rem;
  align-items: center;
  overflow: visible;
}
.pt-score-left {
  text-align: center;
  min-width: 0;
}
.pt-score-gauge {
  position: relative;
  width: min(100%, 282px);
  height: 218px;
  margin: 0 auto;
  overflow: visible;
}
.pt-half-donut {
  display: block;
  position: absolute;
  left: 50%;
  top: 0;
  transform: translateX(-50%);
  width: 100%;
  height: 185px;
  overflow: visible;
}
.pt-gauge-bg,
.pt-gauge-fill {
  fill: none;
  stroke-width: 36;
  stroke-linecap: round;
}
.pt-gauge-bg {
  stroke: rgba(30,52,64,0.92);
}
.pt-gauge-fill {
  stroke-dashoffset: 0;
  transition: stroke-dasharray 240ms ease;
}
.pt-score-gauge-center {
  position: absolute;
  left: 0;
  right: 0;
  top: 84px;
  text-align: center;
}
.pt-score-number {
  color: var(--text);
  font-size: clamp(3.05rem, 4.1vw, 4.35rem);
  line-height: 0.95;
  font-weight: 980;
}
.pt-score-rating {
  font-size: clamp(1.02rem, 1.22vw, 1.2rem);
  font-weight: 980;
  line-height: 1.12;
  margin-top: 0.38rem;
}
.pt-score-rating.good { color: var(--green); }
.pt-score-rating.warn,
.pt-score-rating.neutral { color: var(--yellow); }
.pt-score-rating.bad { color: var(--red); }
.pt-score-details {
  border-left: 1px solid var(--border);
  padding-left: 0.9rem;
}
.pt-score-detail-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.7rem;
  border-bottom: 1px solid rgba(30,52,64,0.72);
  padding: 0.46rem 0;
}
.pt-score-detail-row strong {
  color: var(--text);
  font-size: 0.98rem;
  text-align: right;
  white-space: nowrap;
}
.pt-stance-gauge {
  grid-column: 1 / -1;
  margin-top: 0.42rem;
}
.pt-stance-track {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  height: 7px;
  border-radius: 999px;
  overflow: visible;
}
.pt-stance-track span {
  display: block;
}
.pt-stance-track .bear { background: var(--red); border-radius: 999px 0 0 999px; }
.pt-stance-track .neutral { background: var(--yellow); }
.pt-stance-track .bull { background: var(--green); border-radius: 0 999px 999px 0; }
.pt-stance-track i {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 14px;
  height: 14px;
  border-radius: 999px;
  background: var(--yellow);
  border: 2px solid rgba(6,16,20,0.96);
  box-shadow: 0 0 0 1px rgba(229,167,42,0.45);
}
.pt-stance-labels {
  display: flex;
  justify-content: space-between;
  color: var(--muted);
  font-size: 0.8rem;
  margin-top: 0.48rem;
}
.pt-score-why {
  grid-column: 1 / -1;
  border-top: 1px solid var(--border);
  padding-top: 0.62rem;
}
.pt-mini-title {
  color: var(--text);
  font-size: 0.8rem;
  font-weight: 950;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 0.4rem;
}
.pt-score-why > div:not(.pt-mini-title) {
  display: flex;
  align-items: flex-start;
  gap: 0.42rem;
  margin-top: 0.34rem;
  flex-wrap: wrap;
}
.pt-score-why span:first-child {
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 850;
  min-width: 72px;
}
.pt-driver-chip {
  display: inline-flex;
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0.2rem 0.5rem;
  color: var(--muted);
  font-size: 0.76rem;
  font-weight: 800;
  background: rgba(255,255,255,0.03);
}
.pt-driver-chip.good {
  color: var(--green);
  border-color: rgba(109,187,90,0.35);
  background: rgba(109,187,90,0.10);
}
.pt-driver-chip.warn {
  color: var(--yellow);
  border-color: rgba(229,167,42,0.35);
  background: rgba(229,167,42,0.10);
}
.pt-executive-banner {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-top: 0.72rem;
  padding: 0.72rem 0.95rem;
  border-color: rgba(125,199,232,0.32);
}
.pt-executive-banner span,
.pt-panel-title {
  color: var(--text);
  font-size: 0.9rem;
  font-weight: 950;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.pt-executive-banner strong {
  color: var(--text);
  font-size: 1.05rem;
  line-height: 1.32;
  font-weight: 780;
}
.pt-investment-decision {
  background: linear-gradient(135deg, rgba(16,27,34,0.98), rgba(7,26,61,0.52));
  border: 1px solid rgba(125,199,232,0.28);
  border-radius: 14px;
  padding: 0.8rem 0.95rem;
  margin-top: 0.72rem;
}
.pt-current-view {
  color: var(--muted);
  font-size: 0.95rem;
  margin-top: 0.25rem;
}
.pt-current-view strong {
  color: var(--yellow);
}
.pt-decision-trigger-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.78rem;
  margin-top: 0.62rem;
}
.pt-decision-trigger-grid > div {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.62rem 0.72rem;
  background: rgba(11,23,29,0.82);
}
.pt-decision-trigger-grid .upgrade {
  border-color: rgba(109,187,90,0.38);
}
.pt-decision-trigger-grid .downgrade {
  border-color: rgba(229,115,104,0.38);
}
.pt-decision-trigger-grid span {
  color: var(--text);
  font-size: 0.84rem;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.pt-decision-trigger-grid .upgrade span {
  color: var(--green);
}
.pt-decision-trigger-grid .downgrade span {
  color: var(--red);
}
.pt-decision-trigger-grid ul {
  margin: 0.45rem 0 0 1rem;
  padding: 0;
  color: var(--muted);
  font-size: 0.88rem;
  line-height: 1.35;
}
.pt-lower-dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 290px;
  gap: 0.9rem;
  margin-top: 0.72rem;
  align-items: stretch;
}
.pt-scenario-quick-grid {
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(280px, 1fr);
  gap: 1rem;
  margin-top: 1rem;
  align-items: start;
}
.pt-financial-highlights-card,
.pt-quick-snapshot-card,
.pt-scenario-decision-card {
  padding: 1rem 1.08rem;
}
.pt-financial-highlights-card {
  margin-top: 0.9rem;
}
.pt-panel-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
}
.pt-panel-title small {
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: none;
  margin-left: 0.5rem;
}
.pt-view-financials {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(109,187,90,0.42);
  border-radius: 8px;
  color: var(--green) !important;
  background: rgba(109,187,90,0.08);
  text-decoration: none !important;
  font-size: 0.8rem;
  font-weight: 900;
  padding: 0.34rem 0.58rem;
  white-space: nowrap;
}
.pt-view-financials:hover {
  border-color: var(--yellow);
  color: var(--yellow) !important;
}
.pt-financial-highlights-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 0.8rem;
  margin-top: 0.82rem;
}
.pt-financial-highlight {
  display: flex;
  align-items: center;
  gap: 0.72rem;
  min-width: 0;
  border: 1px solid rgba(30,52,64,0.85);
  border-radius: 12px;
  background: rgba(11,23,29,0.58);
  padding: 0.82rem 0.78rem;
  min-height: 118px;
}
.pt-highlight-icon {
  width: 42px;
  height: 42px;
  border-radius: 999px;
  border: 1px solid rgba(109,187,90,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--green);
  font-size: 0.86rem;
  font-weight: 920;
  flex: 0 0 auto;
  background: rgba(109,187,90,0.1);
}
.pt-highlight-copy {
  min-width: 0;
}
.pt-highlight-label {
  color: var(--muted);
  font-size: 0.76rem;
  font-weight: 820;
}
.pt-highlight-value {
  color: var(--text);
  font-size: 1.38rem;
  font-weight: 900;
  line-height: 1.18;
  margin-top: 0.1rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pt-highlight-trend {
  display: flex;
  gap: 0.35rem;
  color: var(--muted);
  font-size: 0.84rem;
  margin-top: 0.16rem;
}
.pt-highlight-trend strong {
  font-weight: 900;
}
.pt-highlight-period {
  color: var(--muted-2);
  font-size: 0.76rem;
  font-weight: 760;
  margin-top: 0.12rem;
}
.pt-highlight-note {
  color: var(--yellow);
  margin-left: 0.35rem;
}
.pt-quick-snapshot-card {
  height: auto;
}
.pt-data-health-card {
  background: linear-gradient(135deg, rgba(16,27,34,0.98), rgba(7,26,61,0.55));
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: 0 18px 34px rgba(0,0,0,0.18);
  box-sizing: border-box;
  padding: 0.86rem 0.95rem;
  margin-top: 0.72rem;
}
.pt-snapshot-row {
  display: flex;
  justify-content: space-between;
  gap: 0.8rem;
  border: 1px solid rgba(30,52,64,0.72);
  border-bottom: 0;
  padding: 0.56rem 0.62rem;
}
.pt-snapshot-row:first-of-type {
  margin-top: 0.7rem;
  border-radius: 9px 9px 0 0;
}
.pt-snapshot-row:nth-last-of-type(1) {
  border-bottom: 1px solid rgba(30,52,64,0.72);
  border-radius: 0 0 9px 9px;
}
.pt-snapshot-row span {
  color: var(--muted);
  font-size: 0.82rem;
}
.pt-snapshot-row strong {
  color: var(--text);
  font-size: 0.84rem;
  text-align: right;
  overflow-wrap: anywhere;
}
.pt-profile-button {
  display: block;
  margin-top: 0.9rem;
  border: 1px solid var(--border);
  border-radius: 9px;
  color: var(--text) !important;
  text-decoration: none !important;
  text-align: center;
  padding: 0.58rem 0.65rem;
  font-size: 0.9rem;
  font-weight: 820;
  background: rgba(255,255,255,0.025);
}
.pt-profile-button.disabled {
  color: var(--muted-2) !important;
}
.pt-empty-panel {
  border: 1px dashed rgba(30,52,64,0.95);
  border-radius: 10px;
  color: var(--muted);
  background: rgba(255,255,255,0.02);
  font-size: 0.86rem;
  line-height: 1.35;
  padding: 0.72rem;
  margin-top: 0.72rem;
}
.pt-health-status {
  color: var(--yellow);
  font-size: 1.08rem;
  font-weight: 930;
  margin-top: 0.45rem;
}
.pt-health-status strong {
  color: var(--green);
  margin-left: 0.35rem;
}
.pt-health-note {
  color: var(--muted);
  font-size: 0.84rem;
  line-height: 1.35;
  margin-top: 0.3rem;
}
.pt-health-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.2fr);
  gap: 0.3rem 0.55rem;
  border-top: 1px solid var(--border);
  margin-top: 0.62rem;
  padding-top: 0.55rem;
}
.pt-health-grid span {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 820;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.pt-health-grid strong {
  color: var(--text);
  font-size: 0.78rem;
  text-align: right;
  overflow-wrap: anywhere;
}
.pt-scenario-decision-card {
  margin-top: 0.72rem;
}
.pt-scenario-decision-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.65rem;
  margin-top: 0.65rem;
}
.pt-decision-card {
  border: 1px solid var(--border);
  border-radius: 11px;
  background: rgba(11,23,29,0.78);
  overflow: hidden;
}
.pt-decision-card.bear { border-color: rgba(229,115,104,0.55); }
.pt-decision-card.base { border-color: rgba(229,167,42,0.55); }
.pt-decision-card.bull { border-color: rgba(109,187,90,0.55); }
.pt-case-eyebrow {
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 900;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  padding: 0.72rem 0.82rem 0;
}
.pt-case-label {
  color: var(--yellow);
  font-size: 1.05rem;
  font-weight: 920;
  padding: 0.25rem 0.82rem 0;
}
.pt-decision-card.bear .pt-case-label { color: var(--red); }
.pt-decision-card.bull .pt-case-label { color: var(--green); }
.pt-decision-card ul {
  color: var(--muted);
  font-size: 0.9rem;
  line-height: 1.35;
  min-height: 4.3rem;
  margin: 0.55rem 0.8rem 0.65rem 1.6rem;
  padding: 0;
}
.pt-case-footer {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-top: 1px solid var(--border);
}
.pt-case-footer span {
  padding: 0.52rem 0.55rem;
  border-right: 1px solid var(--border);
  text-align: center;
}
.pt-case-footer span:last-child {
  border-right: 0;
}
.pt-case-footer small {
  display: block;
  color: var(--muted);
  font-size: 0.74rem;
}
.pt-case-footer strong {
  display: block;
  color: var(--text);
  font-size: 0.92rem;
  margin-top: 0.12rem;
}
.pt-dashboard-source-line {
  color: var(--muted);
  font-size: 0.76rem;
  margin: 0.55rem 0 0.2rem;
}
.pt-data-asof {
  color: var(--muted);
  font-size: 0.82rem;
  font-weight: 780;
  padding-left: 0.5rem;
}
.pt-chip,
.pt-entry-signal,
.pt-signal-badge,
.pt-hero-meta,
.pt-case-card {
  box-sizing: border-box;
}
.pt-three-statement-grid,
.pt-statement-column,
.pt-statement-card-block,
.pt-statement-chart-block,
.pt-statement-footer-block,
.pt-statement-metrics,
.pt-statement-metric-card,
.pt-chart-placeholder {
  box-sizing: border-box;
}
.pt-statement-metrics {
  display: grid;
  grid-template-rows: repeat(6, 84px);
  gap: 0.44rem;
  margin-bottom: 0.76rem;
}
.pt-statement-metrics .rt-card.small {
  height: 84px;
  min-height: 84px;
  overflow: hidden;
}
.pt-statement-metrics .rt-label,
.pt-statement-metrics .rt-caption {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pt-statement-metrics .rt-value {
  font-size: 1.22rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pt-chart-placeholder {
  min-height: 260px;
}
@media (max-width: 1050px) {
  .pt-dashboard-top-grid,
  .pt-lower-dashboard-grid,
  .pt-scenario-quick-grid {
    grid-template-columns: 1fr;
  }
  .pt-financial-highlights-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .pt-financial-highlight {
    border: 1px solid rgba(30,52,64,0.85);
    padding: 0.82rem 0.78rem;
  }
  .pt-scenario-decision-grid {
    grid-template-columns: 1fr;
  }
  .pt-decision-trigger-grid {
    grid-template-columns: 1fr;
  }
  .pt-score-summary-card {
    grid-template-columns: 1fr;
  }
  .pt-score-details {
    border-left: 0;
    padding-left: 0;
  }
  .pt-dashboard-info-row {
    grid-template-columns: 1fr;
  }
  .pt-hero-grid,
  .pt-scenario-grid {
    grid-template-columns: 1fr !important;
  }
  .pt-logo-column {
    justify-content: flex-start !important;
  }
  .pt-quick-stat-row {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  }
}
@media (max-width: 640px) {
  .pt-identity-row,
  .pt-executive-banner {
    align-items: flex-start;
    flex-direction: column;
  }
  .pt-dashboard-stat-grid,
  .pt-financial-highlights-grid {
    grid-template-columns: 1fr;
  }
  .pt-identity-lockup {
    align-items: flex-start !important;
  }
  .pt-company-logo {
    width: 62px !important;
    height: 62px !important;
    min-width: 62px !important;
  }
  .pt-score-meta-grid,
  .pt-quick-stat-row {
    grid-template-columns: 1fr !important;
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
