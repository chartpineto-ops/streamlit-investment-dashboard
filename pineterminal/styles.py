from __future__ import annotations

import streamlit as st


CSS = """
<style>
:root {
  --bg: #050b12;
  --bg-2: #07111d;
  --panel: #0b1624;
  --panel-2: #111f31;
  --panel-3: #142235;
  --border: #223249;
  --border-soft: rgba(122, 152, 184, 0.22);
  --text: #eef4fb;
  --muted: #9eacbd;
  --faint: #647286;
  --green: #31d17c;
  --green-2: #69de93;
  --red: #ff5c70;
  --yellow: #f0c24a;
  --blue: #5bb6ff;
  --teal: #44d0c8;
}
.stApp {
  background:
    radial-gradient(circle at 12% -12%, rgba(32, 189, 122, 0.12), transparent 28rem),
    linear-gradient(180deg, #050b12 0%, #07111d 100%);
  color: var(--text);
}
.stApp .block-container {
  max-width: none;
  padding: 1rem 1.25rem 2rem;
}
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #07111d 0%, #06101a 100%);
  border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] .block-container {
  padding-top: 1.1rem;
}
h1, h2, h3, p {
  letter-spacing: 0;
}
button, input, textarea, select {
  border-radius: 7px !important;
}
[data-testid="stTextInput"] {
  margin-bottom: 0.25rem;
}
[data-testid="stTextInput"] label p {
  color: var(--faint);
  font-size: 0.72rem;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
[data-testid="stTextInput"] input {
  min-height: 2.35rem;
  background: #091523;
  border: 1px solid var(--border);
  color: var(--text);
  font-size: 0.92rem;
  font-weight: 900;
  text-transform: uppercase;
  box-shadow: 0 0 0 1px rgba(49, 209, 124, 0.06);
}
[data-testid="stTextInput"] input:focus {
  border-color: var(--green);
  box-shadow: 0 0 0 1px rgba(49, 209, 124, 0.35);
}
[data-testid="stMetricValue"] {
  color: var(--text);
}
.pt-brand {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  margin-bottom: 0.8rem;
}
.pt-brand-mark {
  width: 1.65rem;
  height: 1.65rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: #02100a;
  background: linear-gradient(135deg, var(--green), #108653);
  font-weight: 950;
}
.pt-brand strong {
  font-size: 1.26rem;
  line-height: 1;
}
.pt-brand strong span {
  color: var(--green);
}
.pt-side-title {
  color: var(--faint);
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
  margin: 1rem 0 0.45rem;
}
.pt-watch-row {
  display: grid;
  grid-template-columns: 3.5rem 1fr auto;
  gap: 0.35rem;
  padding: 0.34rem 0;
  border-top: 1px solid rgba(122, 152, 184, 0.13);
  font-size: 0.79rem;
}
.pt-watch-row:first-child {
  border-top: 0;
}
.pt-watch-row b {
  color: var(--text);
}
.pt-watch-row span {
  color: var(--muted);
  text-align: right;
}
.good { color: var(--green) !important; }
.bad { color: var(--red) !important; }
.warn { color: var(--yellow) !important; }
.info { color: var(--blue) !important; }
.neutral { color: var(--muted) !important; }
.pt-topbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 1rem;
  align-items: center;
  margin: 0 0 0.8rem;
}
.pt-breadcrumb {
  color: var(--muted);
  font-size: 0.8rem;
}
.pt-breadcrumb b {
  color: var(--text);
  font-weight: 800;
}
.pt-top-meta {
  color: var(--faint);
  margin-left: 0.5rem;
}
.pt-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
  flex-wrap: wrap;
}
.pt-action {
  border: 1px solid var(--border);
  background: #0a1522;
  color: var(--text);
  padding: 0.46rem 0.75rem;
  border-radius: 7px;
  font-size: 0.78rem;
  font-weight: 800;
}
.pt-shell {
  display: flex;
  flex-direction: column;
  gap: 0.68rem;
}
.pt-card,
.pt-header,
.pt-section {
  border: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(13, 25, 40, 0.96), rgba(7, 16, 27, 0.96));
  border-radius: 8px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.18);
}
.pt-header {
  display: grid;
  grid-template-columns: 1.45fr 2.1fr 1.9fr;
  gap: 1rem;
  padding: 0.8rem;
}
.pt-company-title {
  display: flex;
  gap: 0.7rem;
  align-items: center;
}
.pt-ticker {
  color: var(--text);
  font-size: 1.9rem;
  font-weight: 950;
  line-height: 1;
}
.pt-company-title small,
.pt-muted {
  color: var(--muted);
}
.pt-tags {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
  margin-top: 0.55rem;
}
.pt-tag,
.pt-pill,
.pt-status-pill {
  border: 1px solid rgba(91, 182, 255, 0.24);
  background: rgba(91, 182, 255, 0.08);
  color: var(--muted);
  border-radius: 999px;
  padding: 0.18rem 0.45rem;
  font-size: 0.68rem;
  font-weight: 800;
}
.pt-status-pill {
  border-color: rgba(240, 194, 74, 0.28);
  background: rgba(240, 194, 74, 0.08);
  color: var(--yellow);
}
.pt-pill.good {
  border-color: rgba(49, 209, 124, 0.34);
  background: rgba(49, 209, 124, 0.12);
}
.pt-pill.bad {
  border-color: rgba(255, 92, 112, 0.34);
  background: rgba(255, 92, 112, 0.12);
}
.pt-pill.warn {
  border-color: rgba(240, 194, 74, 0.34);
  background: rgba(240, 194, 74, 0.12);
}
.pt-data-label {
  display: inline-flex;
  width: max-content;
  border: 1px solid rgba(122, 152, 184, 0.24);
  border-radius: 999px;
  padding: 0.06rem 0.32rem;
  color: var(--faint);
  background: rgba(122, 152, 184, 0.07);
  font-size: 0.58rem;
  font-weight: 850;
  text-transform: uppercase;
  margin-left: 0.25rem;
}
.pt-summary-grid,
.pt-signal-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.6rem;
}
.pt-signal-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.pt-kpi {
  border-left: 1px solid var(--border-soft);
  padding-left: 0.65rem;
}
.pt-kpi:first-child {
  border-left: 0;
  padding-left: 0;
}
.pt-kpi span,
.pt-mini-label {
  display: block;
  color: var(--muted);
  font-size: 0.68rem;
  font-weight: 800;
}
.pt-kpi strong {
  display: block;
  color: var(--text);
  font-size: 1.08rem;
  margin-top: 0.15rem;
}
.pt-kpi b {
  font-size: 0.75rem;
  font-weight: 850;
}
.pt-kpi small {
  display: block;
  color: var(--muted);
  font-size: 0.68rem;
  margin-top: 0.12rem;
}
.pt-market-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.55rem;
  color: var(--muted);
  font-size: 0.72rem;
}
.pt-market-line span,
.pt-market-line b {
  border: 1px solid var(--border-soft);
  border-radius: 999px;
  padding: 0.16rem 0.42rem;
  background: rgba(122, 152, 184, 0.07);
}
.pt-range {
  margin-top: 0.35rem;
}
.pt-range-track {
  position: relative;
  height: 0.35rem;
  background: #132235;
  border-radius: 999px;
  overflow: hidden;
  margin: 0.18rem 0;
}
.pt-range-track i {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 0.45rem;
  border-radius: 999px;
  background: var(--green);
  box-shadow: 0 0 0 3px rgba(49, 209, 124, 0.12);
}
.pt-score-big strong {
  color: var(--text);
  font-size: 1.95rem;
}
.pt-gauge {
  width: 5rem;
  height: 2.5rem;
  border-radius: 5rem 5rem 0 0;
  background: conic-gradient(from 270deg, var(--green) 0deg, var(--green) 54deg, var(--yellow) 54deg, var(--yellow) 112deg, #26354a 112deg, #26354a 180deg);
  position: relative;
  overflow: hidden;
  margin-top: 0.2rem;
}
.pt-gauge:after {
  content: "";
  position: absolute;
  left: 18%;
  right: 18%;
  bottom: 0;
  height: 64%;
  background: #0c1726;
  border-radius: 5rem 5rem 0 0;
}
.pt-section {
  padding: 0.72rem;
}
.pt-section-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.8rem;
  color: var(--text);
  font-size: 0.83rem;
  font-weight: 950;
  text-transform: uppercase;
  margin-bottom: 0.6rem;
}
.pt-section-title small {
  color: var(--muted);
  font-size: 0.68rem;
  text-transform: none;
  font-weight: 800;
}
.pt-quality-grid {
  display: grid;
  grid-template-columns: repeat(8, minmax(0, 1fr));
  gap: 0.55rem;
}
.pt-quality-summary,
.pt-thesis-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 0.55rem;
  margin-bottom: 0.6rem;
}
.pt-thesis-grid {
  grid-template-columns: 0.9fr 1.25fr 1.25fr 0.8fr;
  margin-bottom: 0;
}
.pt-thesis-callout {
  border: 1px solid var(--border-soft);
  background: rgba(20, 34, 53, 0.72);
  border-radius: 7px;
  padding: 0.65rem;
}
.pt-thesis-callout strong {
  display: block;
  font-size: 1.2rem;
}
.pt-thesis-callout b {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.78rem;
}
.pt-metric-card,
.pt-scenario-card,
.pt-row-card {
  border: 1px solid var(--border-soft);
  background: linear-gradient(180deg, rgba(20, 34, 53, 0.86), rgba(10, 20, 32, 0.86));
  border-radius: 7px;
  padding: 0.65rem;
}
.pt-metric-card strong {
  display: block;
  color: var(--text);
  font-size: 1.05rem;
  margin-top: 0.2rem;
}
.pt-metric-card em,
.pt-scenario-card em {
  display: block;
  color: var(--muted);
  font-size: 0.67rem;
  font-style: normal;
}
.pt-metric-card .pt-data-label,
.pt-scenario-card .pt-data-label {
  margin: 0.45rem 0 0;
}
.pt-progress {
  height: 0.35rem;
  border-radius: 999px;
  background: #17263a;
  margin-top: 0.55rem;
  overflow: hidden;
}
.pt-progress i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #1eb36c, #60da8c);
}
.pt-progress.bad i {
  background: linear-gradient(90deg, #ad3140, var(--yellow));
}
.pt-progress.warn i {
  background: linear-gradient(90deg, #b37d2d, var(--yellow));
}
.pt-grid-two {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(420px, 1fr);
  gap: 0.68rem;
}
.pt-grid-three {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.68rem;
}
.pt-scenario-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.5rem;
}
.pt-scenario-card.bad {
  border-color: rgba(255, 92, 112, 0.36);
}
.pt-scenario-card.info {
  border-color: rgba(91, 182, 255, 0.34);
}
.pt-scenario-card.good {
  border-color: rgba(49, 209, 124, 0.35);
}
.pt-scenario-card h4 {
  margin: 0 0 0.55rem;
  font-size: 0.86rem;
}
.pt-scenario-card dl,
.pt-data-list {
  display: grid;
  gap: 0.38rem;
  margin: 0;
}
.pt-scenario-card div,
.pt-data-list div {
  display: flex;
  justify-content: space-between;
  gap: 0.6rem;
  border-bottom: 1px solid rgba(122, 152, 184, 0.13);
  padding-bottom: 0.25rem;
}
.pt-scenario-card span,
.pt-data-list span {
  color: var(--muted);
  font-size: 0.72rem;
}
.pt-scenario-card b,
.pt-data-list b {
  color: var(--text);
  font-size: 0.8rem;
}
.pt-expected {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.55rem;
  align-items: center;
  border: 1px solid var(--border-soft);
  border-radius: 7px;
  padding: 0.7rem;
  margin-top: 0.55rem;
  background: rgba(91, 182, 255, 0.08);
}
.pt-expected strong {
  display: block;
  color: var(--green);
  font-size: 1.75rem;
}
.pt-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.74rem;
}
.pt-table th,
.pt-table td {
  border-bottom: 1px solid rgba(122, 152, 184, 0.18);
  padding: 0.48rem 0.5rem;
  vertical-align: top;
  text-align: left;
}
.pt-table th {
  color: var(--muted);
  font-size: 0.67rem;
  text-transform: uppercase;
  background: rgba(20, 34, 53, 0.46);
}
.pt-table strong {
  color: var(--text);
}
.pt-table small {
  display: block;
  color: var(--muted);
  margin-top: 0.16rem;
}
.pt-check-row,
.pt-risk-row,
.pt-update-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 0.55rem;
  border-bottom: 1px solid rgba(122, 152, 184, 0.14);
  padding: 0.45rem 0;
}
.pt-check-row:last-child,
.pt-risk-row:last-child,
.pt-update-row:last-child {
  border-bottom: 0;
}
.pt-check {
  width: 1.1rem;
  height: 1.1rem;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(49, 209, 124, 0.18);
  color: var(--green);
  font-size: 0.7rem;
  font-weight: 950;
}
.pt-check.warn {
  background: rgba(240, 194, 74, 0.14);
}
.pt-check.bad {
  background: rgba(255, 92, 112, 0.13);
}
.pt-bridge-row {
  display: flex;
  justify-content: space-between;
  gap: 0.6rem;
  border-bottom: 1px solid rgba(122, 152, 184, 0.16);
  padding: 0.42rem 0;
}
.pt-bridge-row.final {
  border-top: 1px solid var(--border);
  border-bottom: 0;
  margin-top: 0.35rem;
  padding-top: 0.65rem;
}
.pt-bridge-row small {
  display: block;
  color: var(--muted);
  font-size: 0.68rem;
  margin-top: 0.1rem;
}
.pt-banner {
  border-radius: 7px;
  padding: 0.58rem 0.72rem;
  margin-top: 0.58rem;
  font-weight: 850;
  font-size: 0.78rem;
}
.pt-banner.good {
  border: 1px solid rgba(49, 209, 124, 0.32);
  background: rgba(49, 209, 124, 0.12);
}
.pt-banner.bad {
  border: 1px solid rgba(255, 92, 112, 0.32);
  background: rgba(255, 92, 112, 0.12);
}
.pt-banner.warn {
  border: 1px solid rgba(240, 194, 74, 0.32);
  background: rgba(240, 194, 74, 0.12);
}
.pt-update-row {
  grid-template-columns: auto minmax(0, 1fr) auto auto;
}
.pt-update-icon {
  width: 1.35rem;
  height: 1.35rem;
  border-radius: 5px;
  background: rgba(49, 209, 124, 0.14);
}
.pt-update-icon.bad {
  background: rgba(255, 92, 112, 0.14);
}
.pt-risk-row {
  grid-template-columns: 1.3rem minmax(0, 1fr) auto;
}
.pt-risk-row b:first-child {
  color: var(--muted);
}
.pt-sensitivity {
  overflow-x: auto;
}
.pt-sensitivity td.base {
  background: rgba(91, 182, 255, 0.18);
  color: var(--blue);
  box-shadow: inset 0 0 0 1px rgba(91, 182, 255, 0.4);
}
.pt-sensitivity td.upside:not(.base) {
  color: var(--green);
}
.pt-sensitivity td.downside:not(.base) {
  color: var(--red);
}
.pt-final-grid {
  display: grid;
  grid-template-columns: 1fr 1.6fr;
  gap: 0.8rem;
}
.pt-signal-callout strong {
  color: var(--green);
  font-size: 1.55rem;
}
.pt-score-breakdown {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0.55rem;
}
.pt-theme-map {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.5rem;
  margin: 0.6rem 0;
}
.pt-theme-map-card {
  border: 1px solid var(--border-soft);
  background: rgba(20, 34, 53, 0.56);
  border-radius: 7px;
  padding: 0.6rem;
}
.pt-theme-map-card strong,
.pt-theme-map-card span,
.pt-theme-map-card b {
  display: block;
}
.pt-theme-map-card strong {
  color: var(--text);
}
.pt-theme-map-card span,
.pt-theme-map-card p {
  color: var(--muted);
  font-size: 0.72rem;
  margin: 0.18rem 0;
}
.pt-theme-map-card b {
  color: var(--blue);
  font-size: 0.7rem;
}
.pt-trigger-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.55rem;
  margin-top: 0.6rem;
}
.pt-trigger-grid > div {
  border: 1px solid var(--border-soft);
  border-radius: 7px;
  padding: 0.6rem;
  background: rgba(20, 34, 53, 0.48);
}
.pt-trigger-grid ul {
  margin: 0.35rem 0 0;
  padding-left: 1rem;
  color: var(--muted);
  font-size: 0.75rem;
}
.pt-tape {
  display: flex;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 7px;
  background: #081321;
  white-space: nowrap;
}
.pt-tape-inner {
  display: inline-flex;
  min-width: max-content;
  animation: ticker 36s linear infinite;
}
.pt-tape span {
  padding: 0.62rem 0.85rem;
  border-right: 1px solid rgba(122, 152, 184, 0.18);
  font-size: 0.78rem;
}
@keyframes ticker {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}
.pt-mover-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.68rem;
}
.pt-home-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 0.68rem;
}
.pt-placeholder {
  color: var(--muted);
  font-size: 0.82rem;
  line-height: 1.55;
}
.pt-section-title > div {
  display: inline-flex;
  align-items: baseline;
  gap: 0.65rem;
  margin-left: auto;
}
.pt-section-action,
.pt-section-footer {
  color: var(--blue);
  font-size: 0.68rem;
  font-weight: 850;
  text-align: center;
}
.pt-section-footer {
  border-top: 1px solid rgba(122, 152, 184, 0.16);
  background: rgba(91, 182, 255, 0.08);
  margin: 0.38rem -0.72rem -0.72rem;
  padding: 0.38rem 0.72rem;
}
.pt-watch-star,
.pt-header-star {
  color: var(--yellow);
  font-weight: 950;
}
.pt-add-ticker {
  border: 1px solid var(--border);
  border-radius: 7px;
  margin-top: 0.65rem;
  padding: 0.46rem 0.55rem;
  color: var(--text);
  background: rgba(20, 34, 53, 0.62);
  font-size: 0.76rem;
  font-weight: 850;
}
[data-testid="stSidebar"] [role="radiogroup"] {
  display: grid;
  gap: 0.16rem;
}
[data-testid="stSidebar"] [role="radiogroup"] label {
  border-radius: 7px;
  min-height: 2rem;
  padding: 0.2rem 0.35rem;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {
  background: rgba(122, 152, 184, 0.08);
}
.pt-shell {
  gap: 0.52rem;
}
.pt-section {
  padding: 0.62rem;
}
.pt-section-title {
  font-size: 0.78rem;
  margin-bottom: 0.48rem;
}
.pt-section-title small {
  font-size: 0.64rem;
}
.pt-header {
  grid-template-columns: minmax(220px, 1.15fr) minmax(460px, 2.25fr) minmax(470px, 2.2fr);
  gap: 0.8rem;
  padding: 0.7rem;
  align-items: center;
}
.pt-company-block {
  min-width: 0;
}
.pt-company-title {
  align-items: flex-start;
}
.pt-company-title strong {
  display: block;
  color: var(--text);
  font-size: 0.82rem;
  line-height: 1.2;
}
.pt-company-title small {
  display: block;
  margin-top: 0.28rem;
  font-size: 0.72rem;
}
.pt-ticker {
  font-size: 1.9rem;
}
.pt-header-star {
  margin-left: auto;
  font-size: 1rem;
}
.pt-header-market {
  display: grid;
  grid-template-columns: minmax(110px, 0.9fr) minmax(110px, 0.8fr) minmax(120px, 0.85fr) minmax(160px, 1.15fr);
  gap: 0.55rem;
}
.pt-header-signal {
  display: grid;
  grid-template-columns: minmax(120px, 0.9fr) minmax(130px, 1fr) minmax(160px, 1.2fr) 74px;
  gap: 0.55rem;
  align-items: center;
}
.pt-kpi {
  min-width: 0;
}
.pt-kpi span,
.pt-mini-label {
  font-size: 0.64rem;
}
.pt-kpi strong {
  font-size: 1rem;
}
.pt-current-price strong,
.pt-score-big strong {
  font-size: 1.72rem;
}
.pt-gauge {
  width: 4.4rem;
  height: 2.2rem;
}
.pt-quality-grid {
  grid-template-columns: repeat(8, minmax(116px, 1fr));
  gap: 0.45rem;
}
.pt-metric-card,
.pt-scenario-card,
.pt-row-card {
  padding: 0.52rem;
}
.pt-metric-head {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.42rem;
  align-items: center;
}
.pt-metric-icon {
  width: 1.45rem;
  height: 1.45rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  color: #03140c;
  background: linear-gradient(135deg, var(--green), #1a8d62);
  font-size: 0.58rem;
  font-weight: 950;
}
.pt-metric-card strong {
  font-size: 1rem;
  margin-top: 0.24rem;
}
.pt-progress {
  height: 0.31rem;
  margin-top: 0.42rem;
}
.pt-row-valuation,
.pt-row-assumptions,
.pt-row-impact,
.pt-row-bottom {
  display: grid;
  gap: 0.52rem;
  align-items: stretch;
}
.pt-row-valuation {
  grid-template-columns: minmax(0, 1.16fr) minmax(0, 0.94fr);
}
.pt-row-assumptions {
  grid-template-columns: minmax(0, 0.3fr) minmax(0, 0.25fr) minmax(0, 0.45fr);
}
.pt-row-impact {
  grid-template-columns: minmax(0, 0.38fr) minmax(0, 0.22fr) minmax(0, 0.4fr);
}
.pt-row-bottom {
  grid-template-columns: minmax(0, 0.52fr) minmax(0, 0.24fr) minmax(0, 0.24fr);
}
.pt-row-valuation > .pt-section,
.pt-row-assumptions > .pt-section,
.pt-row-impact > .pt-section,
.pt-row-bottom > .pt-section {
  min-width: 0;
}
.pt-fv-grid {
  display: grid;
  grid-template-columns: minmax(0, 2.2fr) minmax(180px, 0.82fr);
  gap: 0.5rem;
}
.pt-scenario-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.44rem;
}
.pt-scenario-card h4 {
  margin-bottom: 0.42rem;
}
.pt-scenario-card dl,
.pt-data-list {
  gap: 0.3rem;
}
.pt-scenario-card div,
.pt-data-list div {
  gap: 0.42rem;
  padding-bottom: 0.2rem;
}
.pt-expected-card {
  border: 1px solid var(--border-soft);
  border-radius: 7px;
  background: rgba(91, 182, 255, 0.08);
  padding: 0.6rem;
}
.pt-expected-card strong {
  display: block;
  color: var(--green);
  font-size: 1.75rem;
  margin: 0.2rem 0 0.45rem;
}
.pt-table {
  font-size: 0.69rem;
}
.pt-table th,
.pt-table td {
  padding: 0.34rem 0.42rem;
}
.pt-table th {
  font-size: 0.61rem;
}
.pt-table small {
  margin-top: 0.1rem;
  font-size: 0.63rem;
}
.pt-check-row,
.pt-risk-row,
.pt-update-row,
.pt-bridge-row {
  padding: 0.35rem 0;
}
.pt-check-row {
  grid-template-columns: 1.1rem minmax(0, 1fr);
}
.pt-check-row strong,
.pt-risk-row strong,
.pt-update-row strong {
  color: var(--text);
  font-size: 0.76rem;
}
.pt-check {
  width: 0.95rem;
  height: 0.95rem;
  font-size: 0.54rem;
}
.pt-bridge-row small {
  display: none;
}
.pt-banner {
  padding: 0.48rem 0.6rem;
  font-size: 0.72rem;
}
.pt-update-icon {
  width: 1.1rem;
  height: 1.1rem;
}
.pt-update-row {
  grid-template-columns: auto minmax(0, 1fr) auto 3.6rem;
}
.pt-arrow-stack small,
.pt-arrow-stack b {
  display: block;
  text-align: center;
  font-size: 0.62rem;
}
.pt-risk-row {
  grid-template-columns: 1rem minmax(0, 1fr) auto;
}
.pt-sensitivity .pt-table td,
.pt-sensitivity .pt-table th {
  text-align: right;
}
.pt-sensitivity .pt-table th:first-child {
  text-align: left;
}
.pt-final-grid {
  grid-template-columns: minmax(150px, 0.75fr) minmax(0, 1.6fr);
  gap: 0.6rem;
}
.pt-score-breakdown {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.45rem;
}
.pt-signal-callout strong {
  font-size: 1.42rem;
}
.pt-signal-callout .pt-placeholder {
  margin: 0.35rem 0;
}
.pt-key-stats-grid {
  grid-template-columns: 1fr 1fr;
  column-gap: 0.7rem;
}
@media (max-width: 1280px) {
  .pt-quality-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
  .pt-header,
  .pt-grid-two,
  .pt-grid-three,
  .pt-row-valuation,
  .pt-row-assumptions,
  .pt-row-impact,
  .pt-row-bottom,
  .pt-fv-grid,
  .pt-final-grid,
  .pt-home-grid,
  .pt-thesis-grid {
    grid-template-columns: 1fr;
  }
  .pt-header-market,
  .pt-header-signal {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 760px) {
  .stApp .block-container {
    padding-left: 0.75rem;
    padding-right: 0.75rem;
  }
  .pt-quality-grid,
  .pt-quality-summary,
  .pt-summary-grid,
  .pt-signal-grid,
  .pt-scenario-grid,
  .pt-score-breakdown,
  .pt-header-market,
  .pt-header-signal,
  .pt-mover-grid,
  .pt-trigger-grid {
    grid-template-columns: 1fr;
  }
  .pt-topbar {
    grid-template-columns: 1fr;
  }
  .pt-actions {
    justify-content: flex-start;
  }
}
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
