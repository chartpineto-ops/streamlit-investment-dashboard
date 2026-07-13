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
.pt-watch-price,
.pt-watch-change {
  color: var(--muted);
  font-size: 0.82rem;
  font-weight: 850;
  line-height: 1.9rem;
  text-align: right;
  white-space: nowrap;
}
.pt-watch-separator {
  border-top: 1px solid rgba(122, 152, 184, 0.13);
  margin: 0.08rem 0 0.18rem;
}
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="stButton"] button {
  min-height: 1.9rem;
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  color: var(--text) !important;
  padding: 0.1rem 0.15rem !important;
  font-size: 0.82rem;
  font-weight: 900;
  text-align: left;
}
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="stButton"] button:hover {
  background: rgba(122, 152, 184, 0.08) !important;
  color: var(--green) !important;
}
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="stButton"] button[title^="Remove"] {
  color: var(--faint) !important;
  text-align: center;
}
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="secondary"] {
  border: 1px solid rgba(122, 152, 184, 0.22) !important;
  background: rgba(20, 34, 53, 0.52) !important;
}
[data-testid="stButton"] button p {
  white-space: nowrap;
}
.good { color: var(--green) !important; }
.bad { color: var(--red) !important; }
.warn { color: var(--yellow) !important; }
.info { color: var(--blue) !important; }
.neutral { color: var(--muted) !important; }
.pt-topbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
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
.pt-scenario-card .pt-kv-row,
.pt-data-list .pt-kv-row {
  display: flex;
  justify-content: space-between;
  gap: 0.6rem;
  border-bottom: 1px solid rgba(122, 152, 184, 0.13);
  padding-bottom: 0.25rem;
}
.pt-scenario-card .pt-kv-row span,
.pt-data-list .pt-kv-row span {
  color: var(--muted);
  font-size: 0.72rem;
}
.pt-scenario-card .pt-kv-row b,
.pt-data-list .pt-kv-row b {
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
.pt-watch-tape {
  display: flex;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: linear-gradient(90deg, rgba(7, 16, 28, 0.94), rgba(13, 27, 45, 0.94));
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.18);
  white-space: nowrap;
  margin: 0.58rem 0 0.72rem;
}
.pt-watch-tape-inner {
  display: inline-flex;
  min-width: max-content;
  animation: watchlist-ticker-ltr 40s linear infinite;
}
.pt-watch-tape:hover .pt-watch-tape-inner {
  animation-play-state: paused;
}
.pt-watch-tape span {
  padding: 0.62rem 1rem;
  border-right: 1px solid rgba(122, 152, 184, 0.18);
  color: var(--muted);
  font-size: 0.8rem;
}
.pt-watch-tape b:first-child {
  color: var(--text);
  margin-right: 0.35rem;
}
@keyframes watchlist-ticker-ltr {
  from { transform: translateX(-50%); }
  to { transform: translateX(0); }
}
.pt-market-marquee em {
  font-size: 0.72rem;
  font-style: normal;
  font-weight: 850;
  margin: 0 0.25rem 0 0.35rem;
}
.pt-market-marquee small {
  font-size: 0.66rem;
  font-weight: 850;
  margin-left: 0.38rem;
}
.pt-market-marquee-empty {
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--muted);
  font-size: 0.76rem;
  margin: 0.58rem 0 0.72rem;
  padding: 0.62rem 0.75rem;
}
.pt-live-ticker-shell {
  margin: 0.58rem 0 0.72rem;
}
.pt-live-ticker-shell .pt-watch-tape {
  margin: 0;
}
.pt-live-ticker-caption {
  align-items: center;
  color: var(--muted);
  display: flex;
  flex-wrap: wrap;
  font-size: 0.68rem;
  gap: 0.55rem;
  justify-content: flex-end;
  padding: 0.22rem 0.15rem 0;
}
.pt-live-ticker-caption span:first-child {
  color: var(--green);
}
.pt-refresh-status-row {
  align-items: center;
  display: grid;
  gap: 0.5rem;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: -0.15rem 0 0.72rem;
}
.pt-refresh-status-row span {
  background: rgba(16, 28, 45, 0.76);
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.42rem 0.58rem;
}
.pt-refresh-status-row b {
  color: var(--text);
  font-size: 0.7rem;
  text-transform: uppercase;
}
.pt-refresh-status-row em {
  font-size: 0.68rem;
  font-style: normal;
  font-weight: 850;
}
.pt-live-section {
  margin-bottom: 0.72rem;
}
.pt-live-section-head {
  align-items: center;
  border-bottom: 1px solid rgba(122, 152, 184, 0.16);
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.65rem;
  padding-bottom: 0.5rem;
}
.pt-live-section-head h2 {
  color: var(--text);
  font-size: 1rem;
  letter-spacing: 0.02em;
  margin: 0;
  text-transform: uppercase;
}
.pt-live-section-head p {
  color: var(--muted);
  font-size: 0.76rem;
  margin: 0.16rem 0 0;
}
.pt-live-section-head > span {
  border: 1px solid var(--border-soft);
  border-radius: 999px;
  color: var(--green);
  font-size: 0.68rem;
  font-weight: 900;
  padding: 0.28rem 0.55rem;
  white-space: nowrap;
}
.pt-live-mover-grid {
  display: grid;
  gap: 0.58rem;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.pt-live-panel {
  background: rgba(8, 17, 29, 0.56);
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  overflow: hidden;
}
.pt-live-panel h3 {
  color: var(--text);
  font-size: 0.78rem;
  letter-spacing: 0.03em;
  margin: 0;
  padding: 0.62rem 0.72rem;
  text-transform: uppercase;
}
.pt-live-table {
  font-size: 0.72rem;
}
.pt-live-table small {
  color: var(--muted);
  display: block;
  font-size: 0.66rem;
  line-height: 1.35;
  margin-top: 0.18rem;
}
.pt-news-live-table th:nth-child(2),
.pt-news-live-table td:nth-child(2) {
  min-width: 18rem;
}
.pt-live-badge {
  border: 1px solid var(--border-soft);
  border-radius: 6px;
  display: inline-block;
  font-size: 0.66rem;
  font-weight: 900;
  padding: 0.18rem 0.38rem;
}
.pt-live-badge.good {
  background: rgba(39, 201, 116, 0.12);
  border-color: rgba(39, 201, 116, 0.34);
  color: var(--green);
}
.pt-live-badge.bad {
  background: rgba(255, 93, 105, 0.12);
  border-color: rgba(255, 93, 105, 0.34);
  color: var(--red);
}
.pt-live-badge.warn,
.pt-live-badge.neutral {
  background: rgba(247, 181, 0, 0.1);
  border-color: rgba(247, 181, 0, 0.32);
  color: var(--yellow);
}
.pt-sector-panel {
  margin-top: 0.58rem;
}
.pt-sector-live-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  padding: 0 0.72rem 0.72rem;
}
.pt-sector-live-strip span {
  background: rgba(20, 34, 53, 0.72);
  border: 1px solid rgba(122, 152, 184, 0.16);
  border-radius: 999px;
  color: var(--muted);
  font-size: 0.7rem;
  padding: 0.28rem 0.5rem;
}
.pt-sector-live-strip b {
  color: var(--text);
}
.pt-sector-live-strip em {
  font-style: normal;
  font-weight: 900;
  margin-left: 0.18rem;
}
.pt-active-quote-card {
  background: rgba(8, 17, 29, 0.5);
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  display: grid;
  gap: 0.6rem;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 0.72rem;
  padding: 0.68rem;
}
.pt-active-quote-card > div {
  border-right: 1px solid rgba(122, 152, 184, 0.14);
  min-width: 0;
  padding-right: 0.55rem;
}
.pt-active-quote-card > div:last-child {
  border-right: 0;
}
.pt-active-quote-card span {
  color: var(--muted);
  display: block;
  font-size: 0.66rem;
  font-weight: 900;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}
.pt-active-quote-card strong {
  color: var(--text);
  display: block;
  font-size: 1rem;
  margin: 0.18rem 0;
}
.pt-active-quote-card small {
  color: var(--muted);
  display: block;
  font-size: 0.7rem;
}
.pt-social-section-head {
  align-items: center;
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}
.pt-social-market-shell {
  margin-bottom: 0.72rem;
}
.pt-social-metric-grid {
  display: grid;
  gap: 0.58rem;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  margin-top: 0.68rem;
}
.pt-social-subhead {
  color: var(--text);
  font-size: 0.9rem;
  letter-spacing: 0.03em;
  margin: 0.35rem 0 0.5rem;
  text-transform: uppercase;
}
.pt-social-market-table {
  min-width: 860px;
}
.pt-social-theme-grid {
  display: grid;
  gap: 0.58rem;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-bottom: 0.75rem;
}
.pt-social-theme-card {
  background: linear-gradient(135deg, rgba(16, 29, 48, 0.9), rgba(8, 17, 29, 0.92));
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  padding: 0.72rem;
}
.pt-social-theme-card strong {
  color: var(--text);
  display: block;
  font-size: 0.86rem;
}
.pt-social-theme-card span {
  color: var(--green);
  display: block;
  font-size: 0.68rem;
  font-weight: 900;
  margin-top: 0.28rem;
}
.pt-social-theme-card p {
  color: var(--muted);
  font-size: 0.7rem;
  line-height: 1.42;
  margin: 0.42rem 0;
}
.pt-social-theme-card em {
  color: var(--faint);
  display: block;
  font-size: 0.64rem;
  font-style: normal;
  font-weight: 850;
}
.pt-social-section-head strong {
  color: var(--text);
  display: block;
  font-size: 1rem;
}
.pt-social-section-head p {
  color: var(--muted);
  font-size: 0.72rem;
  margin: 0.18rem 0 0;
}
.pt-social-source {
  align-items: flex-end;
  display: grid;
  gap: 0.12rem;
  justify-items: end;
  min-width: 9rem;
}
.pt-social-source b,
.pt-social-source em {
  border: 1px solid rgba(49, 209, 124, 0.25);
  border-radius: 999px;
  color: var(--green);
  font-size: 0.62rem;
  font-style: normal;
  font-weight: 900;
  padding: 0.16rem 0.42rem;
}
.pt-social-source span {
  color: var(--faint);
  font-size: 0.6rem;
}
.pt-social-source em {
  border-color: rgba(240, 194, 74, 0.28);
  color: var(--yellow);
}
.pt-social-table-wrap {
  border: 1px solid var(--border-soft);
  border-radius: 7px;
  overflow-x: auto;
}
.pt-social-table {
  border-collapse: collapse;
  min-width: 1320px;
  width: 100%;
}
.pt-social-table th,
.pt-social-table td {
  border-bottom: 1px solid rgba(122, 152, 184, 0.14);
  color: var(--muted);
  font-size: 0.65rem;
  padding: 0.38rem 0.42rem;
  text-align: left;
  vertical-align: middle;
}
.pt-social-table th {
  color: var(--faint);
  font-size: 0.57rem;
  font-weight: 900;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}
.pt-social-name {
  align-items: center;
  display: flex;
  gap: 0.36rem;
}
.pt-social-name i,
.pt-social-readthrough .pt-sector-beneficiary-logo {
  align-items: center;
  background: rgba(122, 152, 184, 0.12);
  border: 1px solid rgba(122, 152, 184, 0.18);
  border-radius: 6px;
  display: inline-flex;
  font-style: normal;
  height: 24px;
  justify-content: center;
  overflow: hidden;
  width: 24px;
}
.pt-social-name i img {
  height: 100%;
  object-fit: contain;
  width: 100%;
}
.pt-social-name i span {
  color: var(--text);
  font-size: 0.52rem;
  font-weight: 950;
}
.pt-social-name b {
  color: var(--text);
  font-size: 0.68rem;
}
.pt-social-badge {
  border: 1px solid rgba(122, 152, 184, 0.22);
  border-radius: 999px;
  display: inline-block;
  font-size: 0.56rem;
  font-weight: 900;
  line-height: 1;
  padding: 0.22rem 0.4rem;
  white-space: nowrap;
}
.pt-social-badge.good {
  background: rgba(49, 209, 124, 0.11);
  border-color: rgba(49, 209, 124, 0.3);
}
.pt-social-badge.bad {
  background: rgba(255, 92, 112, 0.11);
  border-color: rgba(255, 92, 112, 0.3);
}
.pt-social-badge.warn {
  background: rgba(240, 194, 74, 0.1);
  border-color: rgba(240, 194, 74, 0.32);
}
.pt-social-score {
  align-items: center;
  display: flex;
  gap: 0.36rem;
  min-width: 7rem;
}
.pt-social-score b {
  color: var(--text);
  font-size: 0.68rem;
  min-width: 1.6rem;
}
.pt-social-score i {
  background: rgba(122, 152, 184, 0.16);
  border-radius: 999px;
  flex: 1;
  height: 0.3rem;
  overflow: hidden;
}
.pt-social-score i::before {
  background: linear-gradient(90deg, var(--green), var(--blue));
  border-radius: inherit;
  content: "";
  display: block;
  height: 100%;
  width: var(--score);
}
.pt-social-readthrough {
  display: grid;
  gap: 0.68rem;
  grid-template-columns: minmax(0, 1fr) minmax(290px, 0.8fr);
}
.pt-social-metrics {
  display: grid;
  gap: 0.42rem;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.pt-social-interpretation {
  background: rgba(20, 34, 53, 0.42);
  border: 1px solid var(--border-soft);
  border-radius: 7px;
  padding: 0.62rem;
}
.pt-social-interpretation strong {
  color: var(--text);
  display: block;
  font-size: 0.82rem;
}
.pt-social-interpretation p,
.pt-social-interpretation em {
  color: var(--muted);
  display: block;
  font-size: 0.69rem;
  font-style: normal;
  line-height: 1.45;
  margin: 0.38rem 0 0;
}
.pt-social-interpretation em {
  color: var(--yellow);
  font-size: 0.62rem;
}
.pt-social-interpretation div {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-top: 0.5rem;
}
.pt-social-interpretation div span {
  background: rgba(122, 152, 184, 0.12);
  border: 1px solid rgba(122, 152, 184, 0.16);
  border-radius: 999px;
  color: var(--text);
  font-size: 0.59rem;
  font-weight: 850;
  padding: 0.2rem 0.42rem;
}
.pt-sector-title {
  align-items: flex-end;
  display: flex;
  justify-content: space-between;
  margin: 0.15rem 0 0.65rem;
}
.pt-sector-title h1 {
  color: var(--text);
  font-size: 1.7rem;
  line-height: 1;
  margin: 0;
}
.pt-sector-title p {
  color: var(--muted);
  font-size: 0.8rem;
  margin: 0.25rem 0 0;
}
.pt-sector-brief {
  background: linear-gradient(180deg, rgba(15, 31, 50, 0.98), rgba(8, 18, 30, 0.98));
  border: 1px solid var(--border);
  border-radius: 8px;
  display: grid;
  gap: 0.8rem;
  grid-template-columns: minmax(260px, 1.35fr) minmax(390px, 1.6fr) minmax(150px, 0.55fr);
  margin-bottom: 0.68rem;
  padding: 0.8rem;
}
.pt-sector-brief-main {
  border-right: 1px solid var(--border-soft);
  padding-right: 0.8rem;
}
.pt-sector-brief-main p {
  color: var(--text);
  font-size: 0.8rem;
  font-weight: 800;
  line-height: 1.45;
  margin: 0.32rem 0;
}
.pt-sector-brief-main ul {
  color: var(--muted);
  font-size: 0.67rem;
  line-height: 1.4;
  margin: 0.35rem 0 0;
  padding-left: 1rem;
}
.pt-sector-brief-stats {
  display: grid;
  gap: 0.45rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.pt-sector-brief-stats > div {
  background: rgba(20, 34, 53, 0.5);
  border: 1px solid var(--border-soft);
  border-radius: 7px;
  padding: 0.5rem;
}
.pt-sector-brief-stats span,
.pt-sector-conviction span {
  color: var(--faint);
  display: block;
  font-size: 0.61rem;
  font-weight: 850;
  text-transform: uppercase;
}
.pt-sector-brief-stats b {
  color: var(--text);
  display: block;
  font-size: 0.72rem;
  margin-top: 0.2rem;
}
.pt-sector-conviction {
  align-content: center;
  display: grid;
  gap: 0.25rem;
  text-align: center;
}
.pt-sector-conviction strong {
  font-size: 2rem;
  line-height: 1;
}
.pt-sector-conviction b {
  color: var(--muted);
  font-size: 0.68rem;
}
.pt-sector-conviction > div,
.pt-sector-score-bar {
  background: rgba(122, 152, 184, 0.16);
  border-radius: 999px;
  height: 0.28rem;
  overflow: hidden;
}
.pt-sector-conviction > div i,
.pt-sector-score-bar i {
  background: var(--green);
  border-radius: inherit;
  display: block;
  height: 100%;
}
.pt-sector-meaning {
  display: grid;
  gap: 0.52rem;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.pt-sector-meaning > div {
  background: rgba(20, 34, 53, 0.46);
  border: 1px solid var(--border-soft);
  border-radius: 7px;
  min-height: 72px;
  padding: 0.55rem;
}
.pt-sector-meaning span {
  color: var(--muted);
  display: block;
  font-size: 0.63rem;
  font-weight: 900;
  text-transform: uppercase;
}
.pt-sector-meaning ul,
.pt-sector-meaning p {
  color: var(--text);
  font-size: 0.69rem;
  line-height: 1.4;
  margin: 0.3rem 0 0;
  padding-left: 0.95rem;
}
.pt-sector-meaning p {
  padding-left: 0;
}
.pt-sector-meaning strong {
  color: var(--text);
  display: block;
  font-size: 0.9rem;
  margin-top: 0.32rem;
}
.pt-sector-flow-heatmap {
  display: grid;
  gap: 0.42rem;
  grid-template-columns: repeat(6, minmax(0, 1fr));
}
.pt-sector-heat-tile {
  border: 1px solid rgba(151, 174, 201, 0.2);
  border-radius: 7px;
  display: grid;
  gap: 0.12rem;
  min-height: 96px;
  padding: 0.5rem;
}
.pt-sector-heat-tile span,
.pt-sector-heat-tile em,
.pt-sector-heat-tile small {
  color: rgba(238, 244, 251, 0.7);
  font-size: 0.58rem;
  font-style: normal;
}
.pt-sector-heat-tile strong {
  color: var(--text);
  font-size: 0.7rem;
}
.pt-sector-heat-tile strong i {
  color: rgba(238, 244, 251, 0.78);
  font-size: 0.72rem;
  font-style: normal;
  margin-left: 0.18rem;
}
.pt-sector-heat-tile b {
  color: var(--text);
  font-size: 1.05rem;
  line-height: 1.1;
}
.pt-sector-research-list {
  display: grid;
  gap: 0.28rem;
}
.pt-sector-research-row {
  align-items: center;
  background: rgba(20, 34, 53, 0.34);
  border: 1px solid rgba(122, 152, 184, 0.13);
  border-radius: 6px;
  display: grid;
  gap: 0.4rem;
  grid-template-columns: 22px 30px minmax(120px, 1.25fr) minmax(110px, 1fr) repeat(4, minmax(72px, 0.62fr)) minmax(100px, auto);
  min-height: 48px;
  padding: 0.36rem 0.45rem;
}
.pt-sector-research-row > b {
  color: var(--faint);
  font-size: 0.62rem;
}
.pt-sector-research-row > div:not(.pt-sector-beneficiary-logo):not(.pt-sector-risk-icon) span,
.pt-sector-research-row > div:not(.pt-sector-beneficiary-logo):not(.pt-sector-risk-icon) strong,
.pt-sector-research-row > div:not(.pt-sector-beneficiary-logo):not(.pt-sector-risk-icon) small {
  display: block;
}
.pt-sector-research-row > div:not(.pt-sector-beneficiary-logo):not(.pt-sector-risk-icon) span {
  color: var(--faint);
  font-size: 0.55rem;
  text-transform: uppercase;
}
.pt-sector-research-row > div:not(.pt-sector-beneficiary-logo):not(.pt-sector-risk-icon) strong {
  color: var(--text);
  font-size: 0.64rem;
  margin-top: 0.08rem;
}
.pt-sector-research-row > div:not(.pt-sector-beneficiary-logo):not(.pt-sector-risk-icon) small {
  color: var(--faint);
  font-size: 0.53rem;
  margin-top: 0.08rem;
}
.pt-sector-research-row em {
  border: 1px solid rgba(49, 209, 124, 0.28);
  border-radius: 999px;
  font-size: 0.57rem;
  font-style: normal;
  font-weight: 850;
  padding: 0.22rem 0.36rem;
  text-align: center;
}
.pt-sector-risk-row em {
  border-color: rgba(255, 92, 112, 0.28);
}
.pt-sector-risk-icon {
  align-items: center;
  background: rgba(255, 92, 112, 0.12);
  border: 1px solid rgba(255, 92, 112, 0.3);
  border-radius: 50%;
  color: var(--red);
  display: flex;
  font-size: 0.68rem;
  font-weight: 900;
  height: 26px;
  justify-content: center;
  width: 26px;
}
.pt-sector-rotation-summary {
  display: grid;
  gap: 0.5rem;
  grid-template-columns: repeat(2, minmax(150px, 0.8fr)) repeat(2, minmax(180px, 1fr));
}
.pt-sector-rotation-summary > div {
  background: rgba(20, 34, 53, 0.42);
  border: 1px solid var(--border-soft);
  border-radius: 7px;
  padding: 0.55rem;
}
.pt-sector-rotation-summary span {
  color: var(--faint);
  display: block;
  font-size: 0.6rem;
  font-weight: 900;
  text-transform: uppercase;
}
.pt-sector-rotation-summary ul {
  color: var(--text);
  font-size: 0.68rem;
  line-height: 1.45;
  margin: 0.28rem 0 0;
  padding-left: 0.95rem;
}
.pt-sector-rotation-summary strong {
  color: var(--text);
  display: block;
  font-size: 0.78rem;
  margin-top: 0.3rem;
}
.pt-sector-rotation-summary small {
  color: var(--muted);
  display: block;
  font-size: 0.6rem;
  margin-top: 0.18rem;
}
.pt-sector-drivers {
  display: grid;
  gap: 0.4rem;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.pt-sector-drivers > div {
  align-items: flex-start;
  background: rgba(20, 34, 53, 0.42);
  border: 1px solid var(--border-soft);
  border-radius: 7px;
  display: flex;
  gap: 0.45rem;
  padding: 0.55rem;
}
.pt-sector-drivers b {
  align-items: center;
  background: rgba(91, 182, 255, 0.12);
  border-radius: 50%;
  color: var(--blue);
  display: flex;
  flex: 0 0 22px;
  font-size: 0.58rem;
  height: 22px;
  justify-content: center;
}
.pt-sector-drivers p {
  color: var(--text);
  font-size: 0.67rem;
  line-height: 1.4;
  margin: 0;
}
.pt-sector-next {
  display: grid;
  gap: 0.6rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.pt-sector-next section {
  background: rgba(20, 34, 53, 0.3);
  border: 1px solid var(--border-soft);
  border-radius: 7px;
  padding: 0.55rem;
}
.pt-sector-next h4 {
  font-size: 0.72rem;
  margin: 0 0 0.3rem;
}
.pt-sector-next section > div {
  border-top: 1px solid rgba(122, 152, 184, 0.14);
  display: grid;
  gap: 0.1rem 0.4rem;
  grid-template-columns: minmax(0, 1fr) auto;
  padding: 0.36rem 0;
}
.pt-sector-next span,
.pt-sector-next em,
.pt-sector-next small {
  color: var(--faint);
  display: block;
  font-size: 0.57rem;
  font-style: normal;
}
.pt-sector-next strong {
  color: var(--text);
  font-size: 0.66rem;
}
.pt-sector-next b {
  grid-column: 2;
  grid-row: 1 / 3;
}
.pt-sector-next em,
.pt-sector-next small {
  grid-column: 1 / -1;
}
.pt-sector-persistence-takeaway {
  align-items: center;
  background: rgba(20, 34, 53, 0.42);
  border: 1px solid var(--border-soft);
  border-radius: 7px;
  display: grid;
  gap: 0.45rem;
  grid-template-columns: auto minmax(0, 1fr);
  padding: 0.48rem 0.55rem;
}
.pt-sector-persistence-takeaway strong {
  color: var(--blue);
  font-size: 0.68rem;
}
.pt-sector-persistence-takeaway p {
  color: var(--muted);
  font-size: 0.65rem;
  margin: 0;
}
.pt-sector-ranking-wrap {
  overflow-x: auto;
}
.pt-sector-ranking {
  border-collapse: collapse;
  min-width: 1040px;
  width: 100%;
}
.pt-sector-ranking th,
.pt-sector-ranking td {
  border-bottom: 1px solid rgba(122, 152, 184, 0.14);
  color: var(--muted);
  font-size: 0.66rem;
  padding: 0.42rem 0.35rem;
  text-align: left;
  vertical-align: middle;
}
.pt-sector-ranking th {
  color: var(--faint);
  font-size: 0.58rem;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}
.pt-sector-ranking td strong,
.pt-sector-ranking td small {
  color: var(--text);
  display: block;
}
.pt-sector-ranking td small {
  color: var(--faint);
  font-size: 0.58rem;
}
.pt-sector-score-bar {
  align-items: center;
  display: flex;
  height: 0.34rem;
  min-width: 88px;
  overflow: visible;
  position: relative;
}
.pt-sector-score-bar i.warn {
  background: var(--yellow);
}
.pt-sector-score-bar i.bad {
  background: var(--red);
}
.pt-sector-score-bar b {
  font-size: 0.58rem;
  margin-left: 0.32rem;
  min-width: 25px;
}
.pt-sector-hero {
  background: linear-gradient(180deg, rgba(15, 31, 50, 0.96), rgba(8, 18, 30, 0.96));
  border: 1px solid var(--border);
  border-radius: 8px;
  display: grid;
  gap: 1rem;
  grid-template-columns: minmax(260px, 0.75fr) minmax(0, 1.8fr);
  margin-bottom: 0.68rem;
  padding: 0.85rem;
}
.pt-sector-hero > div:first-child {
  border-right: 1px solid var(--border-soft);
  padding-right: 0.85rem;
}
.pt-sector-hero > div:first-child strong {
  display: block;
  font-size: 1.65rem;
  margin-top: 0.2rem;
}
.pt-sector-hero p {
  color: var(--muted);
  font-size: 0.75rem;
  line-height: 1.45;
  margin: 0.35rem 0 0;
}
.pt-sector-hero-stats {
  display: grid;
  gap: 0.55rem;
  grid-template-columns: repeat(6, minmax(0, 1fr));
}
.pt-sector-hero-stats > div,
.pt-sector-mini-grid > div {
  background: rgba(20, 34, 53, 0.5);
  border: 1px solid var(--border-soft);
  border-radius: 7px;
  padding: 0.55rem;
}
.pt-sector-hero-stats span,
.pt-sector-mini-grid span {
  color: var(--muted);
  display: block;
  font-size: 0.64rem;
  font-weight: 850;
  text-transform: uppercase;
}
.pt-sector-hero-stats b,
.pt-sector-mini-grid b {
  color: var(--text);
  display: block;
  font-size: 0.88rem;
  margin-top: 0.2rem;
}
.pt-sector-money-row {
  align-items: center;
  border-bottom: 1px solid rgba(122, 152, 184, 0.14);
  display: grid;
  gap: 0.45rem;
  grid-template-columns: minmax(0, 1fr) auto minmax(100px, 0.7fr);
  padding: 0.42rem 0;
}
.pt-sector-money-row:last-child {
  border-bottom: 0;
}
.pt-sector-money-row span {
  color: var(--text);
  font-size: 0.76rem;
  font-weight: 850;
}
.pt-sector-money-row b {
  font-size: 0.72rem;
  letter-spacing: 0.08rem;
}
.pt-sector-money-row em {
  color: var(--muted);
  font-size: 0.68rem;
  font-style: normal;
  text-align: right;
}
.pt-sector-breadth-head {
  align-items: center;
  display: flex;
  gap: 0.55rem;
  margin-bottom: 0.55rem;
}
.pt-sector-breadth-head b {
  font-size: 1.05rem;
}
.pt-sector-breadth-head span {
  color: var(--muted);
  font-size: 0.7rem;
}
.pt-sector-breadth-copy {
  color: var(--muted);
  font-size: 0.68rem;
  line-height: 1.4;
  margin: 0 0 0.5rem;
}
.pt-sector-mini-grid {
  display: grid;
  gap: 0.45rem;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.pt-sector-theme-grid,
.pt-sector-beneficiary-grid {
  display: grid;
  gap: 0.55rem;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.pt-sector-beneficiary-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.pt-sector-theme-card,
.pt-sector-beneficiary-card {
  background: rgba(20, 34, 53, 0.52);
  border: 1px solid var(--border-soft);
  border-radius: 7px;
  padding: 0.62rem;
}
.pt-sector-theme-card > div,
.pt-sector-beneficiary-title {
  align-items: center;
  display: flex;
  justify-content: space-between;
}
.pt-sector-theme-card strong,
.pt-sector-beneficiary-title strong {
  color: var(--text);
  font-size: 0.78rem;
}
.pt-sector-theme-card span,
.pt-sector-theme-card p,
.pt-sector-theme-card em {
  color: var(--muted);
  display: block;
  font-size: 0.65rem;
  font-style: normal;
  line-height: 1.35;
  margin: 0.28rem 0 0;
}
.pt-sector-theme-scores {
  display: grid !important;
  gap: 0.24rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: 0.38rem;
}
.pt-sector-theme-scores span {
  background: rgba(122, 152, 184, 0.08);
  border-radius: 4px;
  margin: 0;
  padding: 0.25rem;
}
.pt-sector-theme-scores b {
  color: var(--text);
  display: block;
  font-size: 0.68rem;
  margin-top: 0.08rem;
}
.pt-sector-beneficiary-row {
  border-top: 1px solid rgba(122, 152, 184, 0.14);
  display: grid;
  gap: 0.18rem 0.4rem;
  grid-template-columns: auto minmax(0, 1fr) auto;
  margin-top: 0.42rem;
  padding-top: 0.42rem;
}
.pt-sector-beneficiary-logo {
  align-items: center;
  background: rgba(122, 152, 184, 0.12);
  border: 1px solid var(--border-soft);
  border-radius: 6px;
  display: flex;
  height: 30px;
  justify-content: center;
  overflow: hidden;
  width: 30px;
}
.pt-sector-beneficiary-logo img {
  height: 100%;
  object-fit: contain;
  width: 100%;
}
.pt-sector-beneficiary-logo span {
  color: var(--text);
  font-size: 0.58rem;
  font-weight: 900;
}
.pt-sector-beneficiary-company b {
  color: var(--text);
  display: block;
  font-size: 0.72rem;
}
.pt-sector-beneficiary-company span,
.pt-sector-beneficiary-row small {
  color: var(--muted);
  font-size: 0.64rem;
}
.pt-sector-beneficiary-row em {
  font-size: 0.68rem;
  font-style: normal;
  font-weight: 850;
}
.pt-sector-beneficiary-row small {
  grid-column: 1 / -1;
}
.pt-sector-beneficiary-compact {
  min-height: 42px;
}
.pt-sector-beneficiary-compact small {
  grid-column: 2 / -1;
}
.pt-sector-beneficiary-compact small b {
  display: inline;
}
.pt-sector-beneficiary-metrics {
  display: grid;
  gap: 0.22rem;
  grid-column: 1 / -1;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.pt-sector-beneficiary-metrics span {
  background: rgba(122, 152, 184, 0.08);
  border-radius: 4px;
  color: var(--faint);
  display: block;
  font-size: 0.58rem;
  padding: 0.25rem;
}
.pt-sector-beneficiary-metrics b {
  color: var(--text);
  display: block;
  font-size: 0.64rem;
  margin-top: 0.08rem;
}
.pt-sector-money-columns {
  display: grid;
  gap: 0.65rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.pt-sector-money-columns section {
  background: rgba(20, 34, 53, 0.38);
  border: 1px solid var(--border-soft);
  border-radius: 7px;
  padding: 0.5rem;
}
.pt-sector-money-columns section > strong {
  display: block;
  font-size: 0.68rem;
  margin-bottom: 0.25rem;
}
.pt-sector-money-columns section > div {
  align-items: center;
  border-top: 1px solid rgba(122, 152, 184, 0.12);
  display: flex;
  gap: 0.4rem;
  justify-content: space-between;
  padding: 0.3rem 0;
}
.pt-sector-money-columns span {
  color: var(--text);
  font-size: 0.64rem;
}
.pt-sector-money-columns b {
  font-size: 0.58rem;
  letter-spacing: -0.05rem;
}
.pt-sector-timeline {
  display: grid;
  gap: 0.4rem;
  grid-template-columns: repeat(5, minmax(0, 1fr));
}
.pt-sector-timeline > div {
  background: rgba(20, 34, 53, 0.48);
  border: 1px solid var(--border-soft);
  border-radius: 7px;
  display: grid;
  gap: 0.18rem;
  padding: 0.52rem;
}
.pt-sector-timeline span {
  color: var(--faint);
  font-size: 0.62rem;
  font-weight: 850;
  text-transform: uppercase;
}
.pt-sector-timeline strong {
  color: var(--text);
  font-size: 0.69rem;
}
.pt-sector-timeline b {
  font-size: 0.68rem;
}
.pt-sector-insights {
  color: var(--muted);
  display: grid;
  font-size: 0.74rem;
  gap: 0.42rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 0;
  padding-left: 1rem;
}
.pt-sector-bottom-line p {
  color: var(--text);
  font-size: 0.82rem;
  font-weight: 850;
  margin: 0 0 0.55rem;
}
.pt-sector-bottom-line > div,
.pt-sector-health {
  display: grid;
  gap: 0.45rem;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.pt-sector-bottom-line span,
.pt-sector-health span {
  background: rgba(20, 34, 53, 0.48);
  border: 1px solid var(--border-soft);
  border-radius: 7px;
  color: var(--muted);
  font-size: 0.66rem;
  padding: 0.48rem;
}
.pt-sector-bottom-line b,
.pt-sector-health b {
  color: var(--text);
  display: block;
  font-size: 0.76rem;
  margin-top: 0.18rem;
}
.pt-sector-health {
  grid-template-columns: repeat(6, minmax(0, 1fr));
}
.pt-sector-health small {
  color: var(--faint);
  font-size: 0.62rem;
  grid-column: 1 / -1;
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
.pt-calendar {
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  background: rgba(8, 19, 33, 0.72);
}
.pt-calendar-weekdays,
.pt-calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
}
.pt-calendar-weekdays > div {
  background: rgba(20, 34, 53, 0.9);
  border-right: 1px solid rgba(122, 152, 184, 0.14);
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 900;
  letter-spacing: 0.02em;
  padding: 0.48rem 0.55rem;
  text-transform: uppercase;
}
.pt-calendar-day {
  min-height: 11.5rem;
  border-top: 1px solid rgba(122, 152, 184, 0.14);
  border-right: 1px solid rgba(122, 152, 184, 0.14);
  padding: 0.48rem;
  background: rgba(7, 16, 28, 0.58);
}
.pt-calendar-day.muted {
  background: rgba(7, 16, 28, 0.28);
  opacity: 0.48;
}
.pt-calendar-day.today {
  box-shadow: inset 0 0 0 1px rgba(91, 182, 255, 0.7);
  background: rgba(15, 39, 66, 0.68);
}
.pt-calendar-date {
  color: var(--text);
  font-size: 0.84rem;
  font-weight: 950;
  margin-bottom: 0.42rem;
}
.pt-calendar-empty {
  color: var(--faint);
  display: block;
  font-size: 0.68rem;
  margin-top: 0.35rem;
}
.pt-calendar-nav-label {
  align-items: center;
  background: rgba(15, 27, 44, 0.76);
  border: 1px solid var(--border);
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  min-height: 2.42rem;
  padding: 0.48rem 0.68rem;
}
.pt-calendar-nav-label span {
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 900;
  text-transform: uppercase;
}
.pt-calendar-nav-label strong {
  color: var(--text);
  font-size: 0.92rem;
  font-weight: 950;
}
.pt-eco-event {
  border: 1px solid rgba(122, 152, 184, 0.18);
  border-left: 3px solid var(--muted);
  border-radius: 7px;
  background: rgba(20, 34, 53, 0.62);
  margin-bottom: 0.42rem;
  padding: 0.48rem;
}
.pt-eco-event.good { border-left-color: var(--green); }
.pt-eco-event.warn { border-left-color: var(--yellow); }
.pt-eco-event.info { border-left-color: var(--blue); }
.pt-eco-event-head strong {
  color: var(--text);
  display: block;
  font-size: 0.72rem;
  line-height: 1.25;
}
.pt-eco-event-head span {
  color: var(--muted);
  display: block;
  font-size: 0.64rem;
  margin-top: 0.14rem;
}
.pt-eco-values {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.24rem;
  margin: 0.42rem 0;
}
.pt-eco-values span {
  border: 1px solid rgba(122, 152, 184, 0.14);
  border-radius: 5px;
  color: var(--text);
  font-size: 0.66rem;
  padding: 0.28rem;
}
.pt-eco-values b {
  color: var(--muted);
  display: block;
  font-size: 0.58rem;
  text-transform: uppercase;
}
.pt-eco-event p {
  color: var(--muted);
  font-size: 0.66rem;
  line-height: 1.35;
  margin: 0.3rem 0;
}
.pt-eco-event small {
  color: var(--text);
  display: block;
  font-size: 0.62rem;
  line-height: 1.3;
  margin: 0.25rem 0 0.32rem;
  opacity: 0.9;
}
.pt-eco-source {
  align-items: center;
  display: flex;
  gap: 0.45rem;
  justify-content: space-between;
}
.pt-eco-source em {
  color: var(--faint);
  font-size: 0.62rem;
  font-style: normal;
}
.pt-eco-source a {
  color: var(--blue);
  font-size: 0.64rem;
  font-weight: 900;
  text-decoration: none;
}
.pt-calendar-note {
  color: var(--muted);
  font-size: 0.76rem;
  margin: 0.65rem 0 0;
}
.pt-scanner-titlebar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin: 0.2rem 0 0.35rem;
}
.pt-scanner-titlebar h1 {
  margin: 0;
  color: var(--text);
  font-size: 1.75rem;
  line-height: 1.1;
  font-weight: 950;
}
.pt-scanner-titlebar p {
  margin: 0.25rem 0 0;
  color: var(--muted);
  font-size: 0.84rem;
}
.pt-scanner-meta {
  display: flex;
  justify-content: flex-end;
  gap: 0.9rem;
  color: var(--muted);
  font-size: 0.78rem;
}
.pt-scanner-meta span {
  padding-right: 0.9rem;
  border-right: 1px solid rgba(122, 152, 184, 0.22);
}
.pt-scanner-meta span:last-child {
  padding-right: 0;
  border-right: 0;
}
.pt-scanner-meta b {
  color: var(--text);
  margin-left: 0.25rem;
}
.pt-scanner-summary {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.68rem;
  margin: 0.35rem 0 0.72rem;
}
.pt-scanner-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.1rem 0.78rem;
  align-items: center;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.78rem;
  background: linear-gradient(180deg, rgba(17, 31, 49, 0.92), rgba(9, 20, 34, 0.92));
}
.pt-scanner-card-icon {
  grid-row: span 3;
  width: 2.55rem;
  height: 2.55rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-size: 1.45rem;
  font-weight: 950;
  background: rgba(122, 152, 184, 0.1);
}
.pt-scanner-card span {
  color: var(--text);
  font-size: 0.78rem;
  font-weight: 850;
}
.pt-scanner-card strong {
  color: var(--text);
  font-size: 1.65rem;
  line-height: 1;
}
.pt-scanner-card small {
  color: var(--muted);
  font-size: 0.73rem;
}
.pt-scanner-source {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  border: 1px solid rgba(122, 152, 184, 0.18);
  border-radius: 8px;
  padding: 0.52rem 0.68rem;
  margin: 0.55rem 0 0.72rem;
  background: rgba(9, 20, 34, 0.78);
  color: var(--muted);
  font-size: 0.76rem;
}
.pt-scanner-source b {
  color: var(--text);
}
.pt-scanner-source span:last-child {
  color: var(--blue);
  margin-left: auto;
  font-weight: 850;
}
.pt-scanner-header-cell {
  color: var(--muted);
  font-size: 0.68rem;
  font-weight: 950;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  white-space: nowrap;
  padding: 0.28rem 0;
  border-bottom: 1px solid rgba(122, 152, 184, 0.18);
}
.pt-scanner-cell {
  display: block;
  min-height: 1.9rem;
  line-height: 1.9rem;
  color: var(--text);
  font-size: 0.78rem;
  font-weight: 850;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  border-bottom: 1px solid rgba(122, 152, 184, 0.12);
}
.pt-scanner-chip {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  min-height: 1.35rem;
  margin-top: 0.2rem;
  border-radius: 5px;
  padding: 0.14rem 0.38rem;
  font-size: 0.68rem;
  font-weight: 900;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  border: 1px solid rgba(122, 152, 184, 0.2);
  background: rgba(122, 152, 184, 0.08);
  color: var(--muted);
}
.pt-scanner-chip.good {
  border-color: rgba(49, 209, 124, 0.34);
  background: rgba(49, 209, 124, 0.13);
  color: var(--green-2);
}
.pt-scanner-chip.bad {
  border-color: rgba(255, 92, 112, 0.36);
  background: rgba(255, 92, 112, 0.13);
  color: #ff8a96;
}
.pt-scanner-chip.warn {
  border-color: rgba(240, 194, 74, 0.36);
  background: rgba(240, 194, 74, 0.13);
  color: var(--yellow);
}
.pt-scanner-chip.info {
  border-color: rgba(91, 182, 255, 0.34);
  background: rgba(91, 182, 255, 0.12);
  color: #8fceff;
}
.pt-scanner-detail-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.5rem 1rem;
}
.pt-news-title {
  margin: 0.2rem 0 0.55rem;
}
.pt-news-title small {
  color: var(--muted);
  display: block;
  font-size: 0.72rem;
  margin-bottom: 0.48rem;
}
.pt-news-title h1 {
  color: var(--text);
  font-size: 1.7rem;
  font-weight: 950;
  line-height: 1.05;
  margin: 0;
}
.pt-news-title p {
  color: var(--muted);
  font-size: 0.84rem;
  margin: 0.28rem 0 0;
}
.pt-news-data-mode {
  border: 1px solid rgba(122, 152, 184, 0.18);
  border-radius: 8px;
  background: rgba(9, 20, 34, 0.78);
  color: var(--muted);
  font-size: 0.72rem;
  padding: 0.52rem 0.62rem;
  text-align: right;
}
.pt-news-data-mode b {
  color: var(--yellow);
  margin-left: 0.25rem;
}
.pt-news-data-mode span {
  display: block;
  color: var(--faint);
  margin-top: 0.12rem;
}
.pt-news-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.68rem;
  margin: 0.65rem 0 0.72rem;
}
.pt-news-summary-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(17, 31, 49, 0.92), rgba(9, 20, 34, 0.92));
  padding: 0.82rem;
}
.pt-news-summary-card span {
  color: var(--muted);
  display: block;
  font-size: 0.72rem;
  font-weight: 900;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.pt-news-summary-card strong {
  display: block;
  font-size: 1.7rem;
  line-height: 1;
  margin: 0.38rem 0 0.28rem;
}
.pt-news-summary-card small {
  color: var(--muted);
  font-size: 0.72rem;
}
.pt-news-feed-status {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  border: 1px solid rgba(122, 152, 184, 0.18);
  border-radius: 8px;
  padding: 0.5rem 0.68rem;
  margin: 0.58rem 0 0.7rem;
  background: rgba(9, 20, 34, 0.78);
  color: var(--muted);
  font-size: 0.76rem;
}
.pt-news-feed-status b {
  color: var(--text);
}
.pt-news-feed-status span:last-child {
  color: var(--blue);
  margin-left: auto;
  font-weight: 850;
}
.pt-news-header-cell {
  border-bottom: 1px solid rgba(122, 152, 184, 0.2);
  color: var(--muted);
  font-size: 0.66rem;
  font-weight: 950;
  letter-spacing: 0.04em;
  padding: 0.32rem 0;
  text-transform: uppercase;
  white-space: nowrap;
}
.pt-news-cell {
  border-bottom: 1px solid rgba(122, 152, 184, 0.12);
  color: var(--text);
  display: block;
  font-size: 0.73rem;
  font-weight: 780;
  line-height: 1.35;
  min-height: 2.15rem;
  overflow: hidden;
  padding: 0.22rem 0;
  text-overflow: ellipsis;
}
.pt-news-cell small {
  color: var(--muted);
  display: block;
  font-size: 0.64rem;
  font-weight: 650;
  margin-top: 0.12rem;
}
.pt-news-cell.headline {
  font-weight: 850;
}
.pt-news-cell.source a {
  color: var(--blue);
  text-decoration: none;
}
.pt-news-badge {
  display: inline-flex;
  align-items: center;
  border: 1px solid rgba(122, 152, 184, 0.22);
  border-radius: 5px;
  background: rgba(122, 152, 184, 0.08);
  color: var(--muted);
  font-size: 0.66rem;
  font-weight: 900;
  min-height: 1.35rem;
  padding: 0.14rem 0.4rem;
  white-space: nowrap;
}
.pt-news-badge.good {
  border-color: rgba(49, 209, 124, 0.32);
  background: rgba(49, 209, 124, 0.12);
  color: var(--green-2);
}
.pt-news-badge.bad {
  border-color: rgba(255, 92, 112, 0.34);
  background: rgba(255, 92, 112, 0.12);
  color: #ff8a96;
}
.pt-news-badge.warn {
  border-color: rgba(240, 194, 74, 0.34);
  background: rgba(240, 194, 74, 0.12);
  color: var(--yellow);
}
.pt-news-badge.info {
  border-color: rgba(91, 182, 255, 0.32);
  background: rgba(91, 182, 255, 0.11);
  color: #8fceff;
}
.pt-news-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(13, 25, 40, 0.96), rgba(7, 16, 27, 0.96));
  margin-bottom: 0.62rem;
  padding: 0.76rem;
}
.pt-news-card-head {
  align-items: start;
  display: flex;
  gap: 0.75rem;
  justify-content: space-between;
}
.pt-news-card-head strong {
  color: var(--text);
  display: block;
  font-size: 0.94rem;
}
.pt-news-card-head small {
  color: var(--muted);
  display: block;
  font-size: 0.7rem;
  margin-top: 0.22rem;
}
.pt-news-card-meta {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.45rem;
  margin: 0.64rem 0;
}
.pt-news-card-meta span {
  border: 1px solid rgba(122, 152, 184, 0.14);
  border-radius: 6px;
  color: var(--text);
  font-size: 0.72rem;
  padding: 0.42rem;
}
.pt-news-card-meta b {
  color: var(--muted);
  display: block;
  font-size: 0.62rem;
  margin-bottom: 0.18rem;
  text-transform: uppercase;
}
.pt-news-card p {
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.45;
  margin: 0.2rem 0 0;
}
.pt-news-detail-grid {
  display: grid;
  grid-template-columns: 1fr 0.5fr 1.2fr 0.7fr;
  gap: 0.6rem 1rem;
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
.pt-scenario-card .pt-kv-row,
.pt-data-list .pt-kv-row {
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
.pt-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
  line-height: 1;
}
.pt-row-valuation,
.pt-row-assumptions,
.pt-row-impact,
.pt-row-bottom {
  gap: 0.56rem;
  align-items: stretch;
}
.pt-row-valuation > .pt-section,
.pt-row-assumptions > .pt-section,
.pt-row-impact > .pt-section,
.pt-row-bottom > .pt-section {
  align-self: stretch;
}
.pt-row-impact {
  grid-template-columns: minmax(0, 0.36fr) minmax(0, 0.24fr) minmax(0, 0.40fr);
}
.pt-row-bottom {
  grid-template-columns: minmax(0, 0.50fr) minmax(0, 0.25fr) minmax(0, 0.25fr);
}
.pt-section {
  overflow: hidden;
}
.pt-section-title {
  min-height: 1.05rem;
}
.pt-section-title > span {
  min-width: 0;
}
.pt-fv-grid {
  grid-template-columns: minmax(0, 2.05fr) minmax(200px, 0.9fr);
}
.pt-scenario-card {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  gap: 0.42rem;
}
.pt-scenario-title,
.pt-expected-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.45rem;
}
.pt-scenario-card h4 {
  margin: 0;
  min-width: 0;
  font-size: 0.78rem;
  letter-spacing: 0.01em;
  text-transform: uppercase;
}
.pt-scenario-card dl {
  gap: 0.24rem;
}
.pt-scenario-card .pt-kv-row {
  align-items: baseline;
  min-width: 0;
}
.pt-scenario-card .pt-kv-row span,
.pt-data-list .pt-kv-row span {
  min-width: 0;
  line-height: 1.25;
}
.pt-scenario-card .pt-kv-row b,
.pt-data-list .pt-kv-row b {
  flex: 0 0 auto;
  text-align: right;
  line-height: 1.2;
}
.pt-scenario-note {
  display: block;
  margin-top: auto;
  padding-top: 0.35rem;
  color: var(--faint);
  font-size: 0.64rem;
  line-height: 1.28;
}
.pt-expected-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border-color: rgba(91, 182, 255, 0.36);
  background:
    linear-gradient(180deg, rgba(91, 182, 255, 0.11), rgba(8, 19, 32, 0.86));
}
.pt-expected-card strong {
  font-size: 1.95rem;
  line-height: 1;
  margin: 0.42rem 0 0.55rem;
}
.pt-expected-list {
  gap: 0.28rem;
}
.pt-expected-list .pt-kv-row:last-child {
  border-top: 1px solid rgba(122, 152, 184, 0.2);
  border-bottom: 0;
  margin-top: 0.12rem;
  padding-top: 0.3rem;
}
.pt-readthrough-table {
  table-layout: fixed;
}
.pt-readthrough-table th:nth-child(1),
.pt-readthrough-table td:nth-child(1) {
  width: 5.8rem;
}
.pt-readthrough-table th:nth-child(3),
.pt-readthrough-table td:nth-child(3) {
  width: 7.3rem;
}
.pt-readthrough-table th:nth-child(4),
.pt-readthrough-table td:nth-child(4) {
  width: 6.3rem;
  text-align: center;
}
.pt-readthrough-table th:nth-child(5),
.pt-readthrough-table td:nth-child(5) {
  width: 5.4rem;
  text-align: center;
}
.pt-date-cell {
  color: var(--text);
  font-weight: 850;
  white-space: nowrap;
}
.pt-market-copy {
  display: grid;
  gap: 0.12rem;
  min-width: 0;
}
.pt-market-copy strong {
  color: var(--text);
  line-height: 1.25;
}
.pt-market-copy small {
  color: var(--muted);
  line-height: 1.2;
}
.pt-market-copy small:last-child {
  color: var(--faint);
}
.pt-ticker-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.22rem;
}
.pt-ticker-chip {
  border: 1px solid rgba(122, 152, 184, 0.2);
  border-radius: 5px;
  padding: 0.08rem 0.25rem;
  color: var(--text);
  background: rgba(122, 152, 184, 0.07);
  font-size: 0.62rem;
  font-weight: 850;
}
.pt-check-list,
.pt-risk-list {
  display: grid;
  gap: 0;
}
.pt-check-row {
  grid-template-columns: 1.05rem minmax(0, 1fr) auto;
  align-items: start;
  gap: 0.48rem;
  padding: 0.37rem 0;
}
.pt-check-row strong {
  display: block;
  color: var(--text);
  font-size: 0.74rem;
  line-height: 1.25;
}
.pt-check-row small {
  display: block;
  margin-top: 0.08rem;
  color: var(--faint);
  font-size: 0.61rem;
  line-height: 1.15;
}
.pt-row-status {
  align-self: center;
  border: 1px solid rgba(122, 152, 184, 0.22);
  border-radius: 999px;
  padding: 0.13rem 0.36rem;
  color: var(--muted);
  background: rgba(122, 152, 184, 0.06);
  font-size: 0.58rem;
  font-weight: 900;
}
.pt-row-status.good {
  border-color: rgba(49, 209, 124, 0.28);
  color: var(--green);
}
.pt-bridge-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: baseline;
  gap: 0.7rem;
  padding: 0.39rem 0;
}
.pt-bridge-row.start {
  font-weight: 850;
}
.pt-bridge-row span {
  color: var(--text);
  font-size: 0.74rem;
}
.pt-bridge-row b {
  min-width: 4.7rem;
  text-align: right;
  font-size: 0.78rem;
}
.pt-bridge-label {
  min-width: 0;
}
.pt-bridge-label small {
  display: block;
  color: var(--faint);
  font-size: 0.62rem;
  line-height: 1.15;
}
.pt-bridge-row.final {
  margin-top: 0.22rem;
  padding-top: 0.55rem;
}
.pt-bridge-row.final span,
.pt-bridge-row.final b {
  color: var(--blue);
  font-size: 0.86rem;
}
.pt-implied-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.72rem;
}
.pt-implied-side {
  border-left: 1px solid rgba(122, 152, 184, 0.14);
  padding-left: 0.62rem;
}
.pt-implied-side:first-child {
  border-left: 0;
  padding-left: 0;
}
.pt-implied-side > .pt-mini-label {
  margin-bottom: 0.28rem;
}
.pt-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  min-height: 1.9rem;
  line-height: 1.25;
}
.pt-sensitivity {
  margin-bottom: 0.34rem;
}
.pt-sensitivity-table th,
.pt-sensitivity-table td {
  padding: 0.31rem 0.4rem;
}
.pt-table-note {
  display: block;
  color: var(--muted);
  font-size: 0.64rem;
  line-height: 1.25;
}
.pt-risk-row {
  grid-template-columns: 1.15rem minmax(0, 1fr) auto;
  align-items: start;
  gap: 0.48rem;
  padding: 0.42rem 0;
}
.pt-risk-rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.05rem;
  height: 1.05rem;
  border-radius: 4px;
  color: var(--muted);
  background: rgba(122, 152, 184, 0.08);
  font-size: 0.62rem;
}
.pt-risk-copy {
  min-width: 0;
}
.pt-risk-copy strong {
  display: block;
  color: var(--text);
  font-size: 0.74rem;
  line-height: 1.22;
  padding-right: 0.2rem;
}
.pt-risk-copy small {
  display: block;
  margin-top: 0.12rem;
  color: var(--muted);
  font-size: 0.62rem;
  line-height: 1.22;
}
.pt-update-row {
  grid-template-columns: 4.2rem minmax(0, 1fr) auto 4.6rem;
  align-items: center;
  gap: 0.6rem;
  padding: 0.42rem 0;
}
.pt-update-meta {
  display: grid;
  grid-template-columns: 1.1rem minmax(0, 1fr);
  align-items: center;
  gap: 0.32rem;
}
.pt-update-meta small {
  color: var(--faint);
  font-size: 0.59rem;
  line-height: 1.1;
}
.pt-update-copy {
  min-width: 0;
}
.pt-update-copy strong {
  display: block;
  color: var(--text);
  font-size: 0.74rem;
  line-height: 1.2;
}
.pt-update-copy small {
  display: block;
  margin-top: 0.13rem;
  color: var(--muted);
  font-size: 0.63rem;
  line-height: 1.2;
}
.pt-update-copy small b {
  color: var(--faint);
}
.pt-arrow-stack {
  display: grid;
  grid-template-columns: 1fr auto;
  column-gap: 0.34rem;
  row-gap: 0.06rem;
  align-items: baseline;
}
.pt-arrow-stack small {
  color: var(--faint);
  text-align: left;
  font-size: 0.57rem;
}
.pt-arrow-stack b {
  text-align: right;
  font-size: 0.61rem;
}
.pt-final-grid {
  grid-template-columns: minmax(150px, 0.8fr) minmax(0, 1.75fr) minmax(120px, 0.52fr);
  align-items: stretch;
}
.pt-signal-callout,
.pt-total-score-card {
  border-right: 1px solid rgba(122, 152, 184, 0.18);
  padding-right: 0.72rem;
}
.pt-total-score-card {
  border-right: 0;
  padding-right: 0;
}
.pt-signal-callout strong {
  display: block;
  margin-top: 0.18rem;
  font-size: 1.42rem;
  line-height: 1.05;
}
.pt-signal-callout .pt-placeholder {
  margin: 0.38rem 0 0;
  font-size: 0.72rem;
  line-height: 1.35;
}
.pt-score-area {
  min-width: 0;
}
.pt-score-breakdown {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.42rem;
  margin-top: 0.3rem;
}
.pt-score-chip {
  border: 1px solid rgba(122, 152, 184, 0.2);
  border-radius: 7px;
  background: rgba(20, 34, 53, 0.48);
  padding: 0.48rem;
  min-width: 0;
}
.pt-score-chip span {
  display: block;
  color: var(--muted);
  font-size: 0.61rem;
  font-weight: 850;
  line-height: 1.18;
}
.pt-score-chip strong {
  display: block;
  margin-top: 0.18rem;
  font-size: 0.96rem;
  line-height: 1;
}
.pt-score-chip strong small,
.pt-total-score-card strong small {
  color: var(--muted);
  font-size: 0.62rem;
  margin-left: 0.1rem;
}
.pt-score-chip em {
  display: block;
  margin-top: 0.18rem;
  color: var(--faint);
  font-size: 0.6rem;
  font-style: normal;
}
.pt-total-score-card strong {
  display: block;
  margin: 0.22rem 0 0.45rem;
  font-size: 1.55rem;
  line-height: 1;
}
.pt-total-score-card .pt-data-list {
  gap: 0.26rem;
}
.pt-compact-kv {
  gap: 0;
}
.pt-compact-kv .pt-kv-row {
  align-items: baseline;
  padding: 0.31rem 0;
}
.pt-key-stats-grid {
  grid-template-columns: 1fr;
}
.pt-key-stats-grid .pt-kv-row span,
.pt-events-list .pt-kv-row span {
  font-size: 0.68rem;
  line-height: 1.2;
}
.pt-key-stats-grid .pt-kv-row b,
.pt-events-list .pt-kv-row b {
  font-size: 0.72rem;
  text-align: right;
}
.pt-decision-shell {
  max-width: 1520px;
  margin: 0 auto;
  gap: 0.72rem;
}
.pt-decision-shell .pt-section,
.pt-decision-shell .pt-header {
  background:
    radial-gradient(circle at 12% 0%, rgba(91, 182, 255, 0.05), transparent 22rem),
    linear-gradient(180deg, rgba(13, 25, 40, 0.98), rgba(7, 16, 27, 0.98));
  border-color: rgba(80, 111, 148, 0.52);
}
.pt-decision-shell .pt-header {
  grid-template-columns: minmax(250px, 1.12fr) minmax(420px, 1.86fr) minmax(390px, 1.5fr);
  padding: 1rem 1.1rem;
}
.pt-decision-shell .pt-ticker {
  font-size: 2.15rem;
}
.pt-decision-shell .pt-company-title strong {
  font-size: 1rem;
}
.pt-decision-shell .pt-company-title small {
  color: #b8c8d8;
}
.pt-decision-shell .pt-tag {
  border-color: rgba(91, 182, 255, 0.22);
  background: rgba(91, 182, 255, 0.09);
}
.pt-decision-shell .pt-status-pill {
  color: var(--yellow);
}
.pt-source-link {
  color: #8fb7da;
  font-size: 0.66rem;
  font-weight: 800;
  border: 1px solid rgba(122, 152, 184, 0.18);
  background: rgba(122, 152, 184, 0.045);
  border-radius: 999px;
  padding: 0.14rem 0.38rem;
}
.pt-data-sources {
  position: relative;
}
.pt-data-sources summary {
  color: #8fb7da;
  font-size: 0.66rem;
  font-weight: 800;
  border: 1px solid rgba(122, 152, 184, 0.18);
  background: rgba(122, 152, 184, 0.045);
  border-radius: 999px;
  padding: 0.14rem 0.38rem;
  cursor: pointer;
  list-style: none;
}
.pt-data-sources summary::-webkit-details-marker {
  display: none;
}
.pt-floating-panel {
  position: absolute;
  left: 0;
  top: calc(100% + 0.45rem);
  z-index: 35;
  width: min(24rem, 80vw);
  border: 1px solid rgba(91, 182, 255, 0.28);
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(13, 25, 40, 0.99), rgba(7, 16, 27, 0.99));
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.42);
  padding: 0.8rem;
}
.pt-floating-panel strong {
  display: block;
  color: var(--text);
  font-size: 0.82rem;
  margin-bottom: 0.4rem;
  text-transform: uppercase;
}
.pt-detail-row {
  display: flex;
  justify-content: space-between;
  gap: 0.8rem;
  border-bottom: 1px solid rgba(122, 152, 184, 0.14);
  padding: 0.38rem 0;
  color: var(--muted);
  font-size: 0.72rem;
}
.pt-detail-row:last-child {
  border-bottom: 0;
}
.pt-detail-row span small {
  display: block;
  color: var(--muted);
  margin-top: 0.12rem;
  font-size: 0.66rem;
}
.pt-detail-row b {
  color: var(--text);
  text-align: right;
  overflow-wrap: anywhere;
}
.pt-detail-row span {
  min-width: 0;
}
.pt-detail-row.total {
  border-top: 1px solid rgba(122, 152, 184, 0.24);
  margin-top: 0.25rem;
}
.pt-decision-shell .pt-header-signal {
  grid-template-columns: minmax(108px, 0.78fr) minmax(112px, 0.8fr) minmax(230px, 1.45fr);
  gap: 0.5rem;
  border: 1px solid rgba(122, 152, 184, 0.28);
  border-radius: 7px;
  background:
    radial-gradient(circle at 96% 8%, rgba(91, 182, 255, 0.08), transparent 5rem),
    rgba(20, 34, 53, 0.44);
  padding: 0.64rem;
  overflow: hidden;
}
.pt-signal-kpi strong {
  font-size: 1.46rem;
}
.pt-signal-kpi {
  display: block;
  gap: 0.22rem;
}
.pt-signal-kpi > div {
  min-width: 0;
}
.pt-signal-kpi b {
  display: block;
  max-width: 100%;
  overflow-wrap: anywhere;
}
.pt-decision-shell .pt-header-signal .pt-kpi span {
  font-size: 0.72rem;
}
.pt-decision-shell .pt-header-signal .pt-kpi strong {
  font-size: 1.28rem;
  font-weight: 950;
}
.pt-decision-shell .pt-header-signal .pt-kpi b {
  font-size: 0.78rem;
  line-height: 1.35;
}
.pt-decision-shell .pt-score-big strong {
  font-size: 2rem;
  line-height: 1;
}
.pt-decision-shell .pt-score-big > b {
  font-size: 0.86rem;
}
.pt-decision-shell .pt-score-big small {
  font-size: 0.76rem;
  line-height: 1.25;
}
.pt-decision-shell .pt-signal-kpi strong {
  font-size: 1.58rem;
}
.pt-decision-shell .pt-gauge {
  --gauge-color: var(--green);
  --gauge-track: #26354a;
  width: 3.35rem;
  height: 2.15rem;
  display: block;
  position: static;
  border-radius: 0;
  background: none;
  box-shadow: none;
  overflow: visible;
  margin: 0;
  justify-self: start;
}
.pt-signal-kpi .pt-gauge {
  margin-top: 0.24rem;
}
.pt-decision-shell .pt-gauge.strong-buy {
  --gauge-color: #20d86b;
}
.pt-decision-shell .pt-gauge.buy,
.pt-decision-shell .pt-gauge.speculative-buy {
  --gauge-color: var(--green);
}
.pt-decision-shell .pt-gauge.hold,
.pt-decision-shell .pt-gauge.warn,
.pt-decision-shell .pt-gauge.neutral {
  --gauge-color: var(--yellow);
}
.pt-decision-shell .pt-gauge.avoid {
  --gauge-color: #ff9d43;
}
.pt-decision-shell .pt-gauge.sell,
.pt-decision-shell .pt-gauge.bad {
  --gauge-color: var(--red);
}
.pt-gauge-track,
.pt-gauge-fill {
  fill: none;
  stroke-linecap: round;
  stroke-width: 10;
}
.pt-gauge-track {
  stroke: var(--gauge-track);
}
.pt-gauge-fill {
  stroke: var(--gauge-color);
}
.pt-gauge-needle {
  stroke: var(--gauge-color);
  stroke-linecap: round;
  stroke-width: 3.2;
}
.pt-gauge-hub {
  fill: var(--gauge-color);
  stroke: #07101b;
  stroke-width: 3;
}
.pt-decision-card {
  padding: 1.08rem 1.18rem;
}
.pt-section-title.flat {
  margin: 0 0 0.45rem;
  min-height: 0;
}
.pt-decision-card .pt-section-title.flat span {
  font-size: 0.86rem;
}
.pt-decision-main {
  display: grid;
  grid-template-columns: 4.4rem minmax(0, 1.45fr) minmax(460px, 1.35fr);
  gap: 1rem;
  align-items: center;
}
.pt-decision-icon {
  --signal-color: var(--green);
  width: 4rem;
  height: 4rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(49, 209, 124, 0.34);
  border-radius: 999px;
  background: rgba(49, 209, 124, 0.09);
  box-shadow: inset 0 0 0 1px rgba(49, 209, 124, 0.08);
  color: var(--signal-color);
}
.pt-decision-icon.warn {
  --signal-color: var(--yellow);
  border-color: rgba(240, 194, 74, 0.36);
  background: rgba(240, 194, 74, 0.09);
}
.pt-decision-icon.bad {
  --signal-color: var(--red);
  border-color: rgba(255, 92, 112, 0.36);
  background: rgba(255, 92, 112, 0.09);
}
.pt-decision-icon.avoid {
  --signal-color: #ff9d43;
  border-color: rgba(255, 157, 67, 0.36);
  background: rgba(255, 157, 67, 0.09);
}
.pt-decision-icon .pt-signal-arrow {
  --icon-angle: -42deg;
  width: 2rem;
  height: 2rem;
  display: block;
  position: relative;
  transform: rotate(var(--icon-angle));
}
.pt-decision-icon.strong-buy .pt-signal-arrow {
  --icon-angle: -54deg;
}
.pt-decision-icon.buy .pt-signal-arrow {
  --icon-angle: -46deg;
}
.pt-decision-icon.speculative-buy .pt-signal-arrow {
  --icon-angle: -28deg;
}
.pt-decision-icon.hold .pt-signal-arrow {
  --icon-angle: 0deg;
}
.pt-decision-icon.avoid .pt-signal-arrow {
  --icon-angle: 28deg;
}
.pt-decision-icon.sell .pt-signal-arrow {
  --icon-angle: 86deg;
}
.pt-signal-arrow:before,
.pt-signal-arrow i {
  content: "";
  position: absolute;
  left: 0.22rem;
  top: calc(50% - 1.5px);
  width: 1.42rem;
  height: 3px;
  border-radius: 999px;
  background: currentColor;
}
.pt-signal-arrow:after {
  content: "";
  position: absolute;
  right: 0.28rem;
  top: 0.58rem;
  width: 0.54rem;
  height: 0.54rem;
  border-top: 3px solid currentColor;
  border-right: 3px solid currentColor;
  transform: rotate(45deg);
  border-radius: 1px;
}
.pt-decision-icon.hold .pt-signal-arrow:after {
  display: none;
}
.pt-decision-icon.strong-buy .pt-signal-arrow i {
  display: block;
  transform: translateY(-0.45rem);
}
.pt-decision-icon:not(.strong-buy) .pt-signal-arrow i {
  display: none;
}
.pt-svg-icon {
  width: 1.15rem;
  height: 1.15rem;
  display: block;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
  overflow: visible;
}
.pt-decision-icon .pt-svg-icon {
  width: 2.15rem;
  height: 2.15rem;
  stroke-width: 2.5;
}
.pt-decision-copy strong {
  display: block;
  font-size: 2.12rem;
  line-height: 1.05;
}
.pt-decision-copy p {
  margin: 0.6rem 0 0;
  color: var(--text);
  max-width: 54rem;
  font-size: 1rem;
  line-height: 1.5;
}
.pt-bottom-line-callout {
  border: 1px solid rgba(240, 194, 74, 0.22);
  border-radius: 7px;
  background: rgba(240, 194, 74, 0.065);
  color: #d9e2ec;
  margin-top: 0.72rem;
  padding: 0.66rem 0.72rem;
  font-size: 0.84rem;
  line-height: 1.45;
}
.pt-decision-quick {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border-left: 1px solid rgba(122, 152, 184, 0.2);
}
.pt-decision-quick .pt-kv-row {
  display: block;
  min-width: 0;
  padding: 0 0.85rem;
  border-bottom: 0;
  border-right: 1px solid rgba(122, 152, 184, 0.16);
}
.pt-decision-quick .pt-kv-row:last-child {
  border-right: 0;
}
.pt-decision-quick .pt-kv-row span {
  display: block;
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 850;
}
.pt-decision-quick .pt-kv-row b {
  display: block;
  margin-top: 0.3rem;
  font-size: 1.12rem;
}
.pt-decision-breakdown {
  display: grid;
  grid-template-columns: minmax(130px, 0.45fr) minmax(0, 1fr) auto;
  gap: 0.9rem;
  align-items: center;
  border-top: 1px solid rgba(122, 152, 184, 0.18);
  margin-top: 1rem;
  padding-top: 0.85rem;
}
.pt-score-label {
  display: grid;
  gap: 0.18rem;
}
.pt-score-label small {
  color: var(--muted);
  font-size: 0.67rem;
  line-height: 1.28;
  max-width: 12rem;
}
.pt-decision-score-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.75rem;
}
.pt-decision-score {
  min-width: 0;
}
.pt-decision-score span {
  color: var(--muted);
  display: block;
  font-size: 0.72rem;
  font-weight: 850;
}
.pt-decision-score strong {
  display: block;
  margin-top: 0.18rem;
  font-size: 1.12rem;
  line-height: 1;
}
.pt-decision-score.total strong {
  font-size: 1.55rem;
}
.pt-decision-score small {
  color: var(--muted);
  margin-left: 0.08rem;
}
.pt-decision-score i {
  display: block;
  height: 0.26rem;
  width: 100%;
  margin-top: 0.42rem;
  border-radius: 999px;
  background: linear-gradient(90deg, currentColor var(--score), #18283b var(--score));
}
.pt-methodology {
  position: relative;
  justify-self: end;
}
.pt-methodology summary {
  border: 1px solid rgba(122, 152, 184, 0.42);
  border-radius: 7px;
  padding: 0.56rem 1.1rem;
  color: var(--text);
  font-size: 0.75rem;
  font-weight: 850;
  white-space: nowrap;
  cursor: pointer;
  list-style: none;
}
.pt-methodology summary::-webkit-details-marker {
  display: none;
}
.pt-methodology summary:after {
  content: "";
  display: inline-block;
  width: 0.42rem;
  height: 0.42rem;
  border-right: 2px solid var(--muted);
  border-bottom: 2px solid var(--muted);
  margin-left: 0.65rem;
  transform: rotate(45deg) translateY(-0.1rem);
}
.pt-methodology[open] summary:after {
  transform: rotate(225deg) translate(-0.05rem, -0.1rem);
}
.pt-methodology-panel {
  position: absolute;
  right: 0;
  top: calc(100% + 0.55rem);
  z-index: 20;
  width: min(36rem, 82vw);
  border: 1px solid rgba(91, 182, 255, 0.28);
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(13, 25, 40, 0.99), rgba(7, 16, 27, 0.99));
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.42);
  padding: 0.85rem;
}
.pt-methodology-panel strong {
  color: var(--text);
  display: block;
  font-size: 0.85rem;
  text-transform: uppercase;
}
.pt-methodology-panel p {
  color: #c6d2df;
  font-size: 0.74rem;
  line-height: 1.45;
  margin: 0.5rem 0 0.65rem;
}
.pt-methodology-pillars {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-bottom: 0.65rem;
}
.pt-methodology-pillars span {
  color: var(--blue);
  border: 1px solid rgba(91, 182, 255, 0.22);
  border-radius: 999px;
  background: rgba(91, 182, 255, 0.06);
  padding: 0.18rem 0.42rem;
  font-size: 0.66rem;
  font-weight: 850;
}
.pt-methodology-panel ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 0.32rem;
}
.pt-methodology-panel li {
  display: grid;
  grid-template-columns: 7.8rem minmax(0, 1fr);
  gap: 0.55rem;
  align-items: baseline;
  color: var(--muted);
  font-size: 0.7rem;
}
.pt-methodology-panel li b {
  color: var(--text);
}
.pt-methodology-panel em {
  color: var(--blue);
  display: block;
  font-size: 0.68rem;
  font-style: normal;
  font-weight: 900;
  margin: 0.62rem 0 0.3rem;
  text-transform: uppercase;
}
.pt-inline-details {
  margin-top: 0.62rem;
}
.pt-inline-details summary {
  color: var(--blue);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.42rem;
  font-size: 0.74rem;
  font-weight: 900;
  list-style: none;
}
.pt-inline-details summary::-webkit-details-marker {
  display: none;
}
.pt-inline-details summary:after {
  content: "";
  width: 0.38rem;
  height: 0.38rem;
  border-right: 2px solid currentColor;
  border-bottom: 2px solid currentColor;
  transform: rotate(45deg) translateY(-0.08rem);
}
.pt-inline-details[open] summary:after {
  transform: rotate(225deg);
}
.pt-inline-details.right {
  text-align: right;
}
.pt-inline-details.centered {
  text-align: center;
}
.pt-detail-panel {
  border: 1px solid rgba(91, 182, 255, 0.2);
  border-radius: 8px;
  background: rgba(8, 18, 30, 0.72);
  margin-top: 0.65rem;
  padding: 0.78rem;
  text-align: left;
}
.pt-detail-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.7rem;
  margin-bottom: 0.62rem;
}
.pt-detail-heading strong,
.pt-detail-card > strong {
  color: var(--text);
  display: block;
  font-size: 0.82rem;
  text-transform: uppercase;
}
.pt-detail-heading span {
  color: var(--muted);
  font-size: 0.68rem;
}
.pt-detail-table {
  margin-top: 0.35rem;
}
.pt-detail-table td,
.pt-detail-table th {
  vertical-align: top;
}
.pt-detail-table small {
  color: var(--muted);
  display: block;
  margin-top: 0.12rem;
}
.pt-detail-grid {
  display: grid;
  gap: 0.65rem;
  margin-top: 0.72rem;
}
.pt-detail-grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.pt-detail-card {
  border: 1px solid rgba(122, 152, 184, 0.16);
  border-radius: 7px;
  background: rgba(20, 34, 53, 0.42);
  padding: 0.7rem;
}
.pt-detail-card.warn {
  border-color: rgba(240, 194, 74, 0.35);
  background: rgba(240, 194, 74, 0.06);
}
.pt-detail-card.wide {
  margin-top: 0.72rem;
}
.pt-detail-list {
  margin: 0.45rem 0 0;
  padding-left: 1rem;
  color: var(--muted);
  font-size: 0.72rem;
  line-height: 1.45;
}
.pt-model-warning {
  display: grid;
  grid-template-columns: 1rem minmax(0, 1fr);
  gap: 0.42rem 0.55rem;
  align-items: start;
  border: 1px solid rgba(240, 194, 74, 0.28);
  border-radius: 7px;
  background: rgba(240, 194, 74, 0.07);
  color: var(--yellow);
  margin-bottom: 0.62rem;
  padding: 0.56rem 0.66rem;
  font-size: 0.75rem;
}
.pt-model-warning .pt-svg-icon {
  width: 0.92rem;
  height: 0.92rem;
  margin-top: 0.08rem;
}
.pt-model-warning span {
  color: var(--text);
  font-weight: 800;
}
.pt-model-warning small {
  grid-column: 2;
  color: var(--muted);
  line-height: 1.35;
}
.pt-detail-note {
  border-radius: 6px;
  margin: 0.55rem 0 0;
  padding: 0.48rem 0.55rem;
  font-size: 0.72rem;
  line-height: 1.35;
  background: rgba(122, 152, 184, 0.1);
}
.pt-detail-note.warn {
  background: rgba(240, 194, 74, 0.1);
  color: var(--yellow);
}
.pt-detail-note.good {
  background: rgba(49, 209, 124, 0.1);
  color: var(--green);
}
.pt-detail-note.bad {
  background: rgba(255, 92, 112, 0.1);
  color: var(--red);
}
.pt-decision-row {
  display: grid;
  grid-template-columns: minmax(0, 0.82fr) minmax(0, 1.18fr);
  gap: 0.72rem;
}
.pt-risk-decision-row {
  grid-template-columns: minmax(0, 0.45fr) minmax(0, 1fr);
}
.pt-quality-pillars {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
}
.pt-quality-pillar {
  display: grid;
  grid-template-columns: 2.65rem minmax(0, 1fr);
  gap: 0.72rem;
  padding: 0.85rem 0.75rem;
  border-bottom: 1px solid rgba(122, 152, 184, 0.14);
}
.pt-quality-pillar:nth-child(odd) {
  border-right: 1px solid rgba(122, 152, 184, 0.14);
}
.pt-quality-pillar:nth-child(n+3) {
  border-bottom: 0;
}
.pt-line-icon {
  width: 2.3rem;
  height: 2.3rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(49, 209, 124, 0.26);
  border-radius: 999px;
  color: var(--green);
  background: rgba(49, 209, 124, 0.1);
  font-size: 0.68rem;
  font-weight: 950;
}
.pt-quality-icon {
  position: relative;
  font-size: 0;
}
.pt-quality-icon:before,
.pt-quality-icon:after,
.pt-quality-icon i:before,
.pt-quality-icon i:after {
  content: "";
  position: absolute;
  display: block;
}
.pt-quality-icon.growth:before {
  left: 0.58rem;
  bottom: 0.62rem;
  width: 1.05rem;
  height: 0.76rem;
  border-left: 2px solid currentColor;
  border-bottom: 2px solid currentColor;
}
.pt-quality-icon.growth:after {
  left: 0.72rem;
  top: 0.76rem;
  width: 1rem;
  height: 0.55rem;
  border-top: 2px solid currentColor;
  border-right: 2px solid currentColor;
  transform: rotate(-35deg);
}
.pt-quality-icon.growth i:after {
  right: 0.5rem;
  top: 0.55rem;
  width: 0.42rem;
  height: 0.42rem;
  border-top: 2px solid currentColor;
  border-right: 2px solid currentColor;
  transform: rotate(12deg);
}
.pt-quality-icon.profitability:before {
  content: "%";
  color: currentColor;
  font-size: 1.05rem;
  font-weight: 950;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -52%);
}
.pt-quality-icon.balance:before {
  left: 0.62rem;
  top: 0.46rem;
  width: 1.06rem;
  height: 1.28rem;
  border: 2px solid currentColor;
  border-radius: 0.5rem 0.5rem 0.58rem 0.58rem;
  clip-path: polygon(50% 0, 100% 22%, 92% 78%, 50% 100%, 8% 78%, 0 22%);
}
.pt-quality-icon.execution:before {
  left: 0.57rem;
  top: 0.57rem;
  width: 1.14rem;
  height: 1.14rem;
  border: 2px solid currentColor;
  border-radius: 999px;
}
.pt-quality-icon.execution:after {
  left: 0.9rem;
  top: 0.9rem;
  width: 0.48rem;
  height: 0.48rem;
  border: 2px solid currentColor;
  border-radius: 999px;
}
.pt-quality-icon.execution i:after {
  right: 0.42rem;
  top: 0.42rem;
  width: 0.58rem;
  height: 2px;
  background: currentColor;
  transform: rotate(-35deg);
  transform-origin: right center;
}
.pt-quality-icon:has(svg):before,
.pt-quality-icon:has(svg):after,
.pt-quality-icon:has(svg) i:before,
.pt-quality-icon:has(svg) i:after {
  display: none;
  content: none;
}
.pt-quality-icon .pt-svg-icon {
  width: 1.22rem;
  height: 1.22rem;
  stroke-width: 2.1;
}
.pt-quality-pillar strong,
.pt-quality-pillar b,
.pt-quality-pillar em {
  display: block;
}
.pt-quality-pillar strong {
  font-size: 0.95rem;
  color: var(--text);
}
.pt-quality-pillar b {
  margin-top: 0.16rem;
  font-size: 1.2rem;
}
.pt-quality-pillar b small {
  color: var(--muted);
  font-size: 0.7rem;
}
.pt-quality-pillar em {
  margin-top: 0.26rem;
  color: var(--text);
  font-size: 0.73rem;
  font-style: normal;
}
.pt-quality-pillar p {
  margin: 0.22rem 0 0;
  color: var(--muted);
  font-size: 0.72rem;
  line-height: 1.42;
}
.pt-subtle-link {
  border-top: 1px solid rgba(122, 152, 184, 0.15);
  color: var(--blue);
  margin-top: 0.65rem;
  padding-top: 0.62rem;
  font-size: 0.72rem;
  font-weight: 850;
  text-align: center;
}
.pt-subtle-link.right {
  text-align: right;
}
.pt-subtle-link.centered {
  text-align: center;
}
.pt-decision-scenarios {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.6rem;
}
.pt-decision-scenario {
  border: 1px solid var(--border-soft);
  border-radius: 7px;
  background: linear-gradient(180deg, rgba(20, 34, 53, 0.62), rgba(7, 16, 27, 0.78));
  padding: 0.78rem;
  min-width: 0;
  position: relative;
  overflow: hidden;
}
.pt-decision-scenario:before {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 2px;
  background: rgba(122, 152, 184, 0.35);
}
.pt-decision-scenario.bad {
  border-color: rgba(255, 92, 112, 0.35);
}
.pt-decision-scenario.bad:before {
  background: var(--red);
}
.pt-decision-scenario.info {
  border-color: rgba(91, 182, 255, 0.35);
}
.pt-decision-scenario.info:before {
  background: var(--blue);
}
.pt-decision-scenario.good {
  border-color: rgba(49, 209, 124, 0.35);
}
.pt-decision-scenario.good:before {
  background: var(--green);
}
.pt-decision-scenario h4 {
  display: flex;
  align-items: center;
  gap: 0.42rem;
  margin: 0 0 0.62rem;
  font-size: 0.84rem;
}
.pt-scenario-icon {
  width: 1.18rem;
  height: 1.18rem;
  border: 1px solid currentColor;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  position: relative;
  flex: 0 0 auto;
}
.pt-scenario-icon:before,
.pt-scenario-icon:after,
.pt-scenario-icon i:before,
.pt-scenario-icon i:after {
  content: "";
  position: absolute;
  display: block;
}
.pt-scenario-icon.bear:before,
.pt-scenario-icon.bull:before {
  left: 0.34rem;
  top: 0.3rem;
  width: 0.45rem;
  height: 0.45rem;
  border-right: 2px solid currentColor;
  border-top: 2px solid currentColor;
}
.pt-scenario-icon.bear:before {
  transform: rotate(135deg);
}
.pt-scenario-icon.bull:before {
  transform: rotate(-45deg);
}
.pt-scenario-icon.bear:after,
.pt-scenario-icon.bull:after {
  left: 0.54rem;
  top: 0.32rem;
  width: 2px;
  height: 0.58rem;
  background: currentColor;
}
.pt-scenario-icon.bear:after {
  transform: rotate(-45deg);
}
.pt-scenario-icon.bull:after {
  transform: rotate(45deg);
}
.pt-scenario-icon.base:before {
  left: 0.32rem;
  top: 0.32rem;
  width: 0.5rem;
  height: 0.5rem;
  border: 2px solid currentColor;
  border-radius: 999px;
}
.pt-scenario-icon.base:after {
  left: 0.52rem;
  top: 0.18rem;
  width: 2px;
  height: 0.82rem;
  background: currentColor;
}
.pt-scenario-icon:has(svg):before,
.pt-scenario-icon:has(svg):after,
.pt-scenario-icon:has(svg) i:before,
.pt-scenario-icon:has(svg) i:after {
  display: none;
  content: none;
}
.pt-scenario-icon .pt-svg-icon {
  width: 0.78rem;
  height: 0.78rem;
  stroke-width: 2.4;
}
.pt-decision-scenario strong {
  display: block;
  color: var(--text);
  font-size: 1.6rem;
}
.pt-decision-scenario > b {
  display: block;
  margin-top: 0.2rem;
  font-size: 1.2rem;
}
.pt-decision-scenario > span {
  display: block;
  color: var(--muted);
  margin: 0.35rem 0 0.58rem;
  font-size: 0.7rem;
}
.pt-decision-scenario .pt-data-list {
  margin-top: 0.4rem;
}
.pt-decision-scenario p {
  min-height: 2.15rem;
  color: var(--text);
  margin: 0.6rem 0 0;
  font-size: 0.72rem;
  line-height: 1.45;
}
.pt-expected-strip {
  display: grid;
  grid-template-columns: 1.15fr 0.78fr 0.78fr minmax(220px, 1.55fr);
  gap: 0;
  border: 1px solid rgba(49, 209, 124, 0.18);
  border-radius: 7px;
  background: rgba(49, 209, 124, 0.055);
  margin-top: 0.62rem;
  overflow: hidden;
}
.pt-expected-strip .pt-kv-row {
  display: block;
  padding: 0.68rem 0.8rem;
  border-bottom: 0;
  border-right: 1px solid rgba(122, 152, 184, 0.16);
}
.pt-expected-strip .pt-kv-row:last-child {
  border-right: 0;
}
.pt-expected-strip span {
  display: block;
  color: var(--muted);
  font-size: 0.68rem;
}
.pt-expected-strip b {
  display: block;
  margin-top: 0.24rem;
  font-size: 1.14rem;
}
.pt-expected-strip .pt-kv-row:first-child b {
  font-size: 1.45rem;
}
.pt-expected-strip .pt-kv-row:last-child b {
  color: var(--muted);
  font-size: 0.74rem;
  line-height: 1.35;
  text-align: left;
}
.pt-scenario-footer {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: 0.6rem;
  color: var(--muted);
  font-size: 0.72rem;
}
.pt-scenario-footer b {
  color: var(--blue);
  white-space: nowrap;
}
.pt-drivers-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1.2fr) minmax(220px, 0.64fr);
  gap: 1rem;
}
.pt-drivers-grid > div {
  border-right: 1px solid rgba(122, 152, 184, 0.14);
  padding-right: 1rem;
}
.pt-drivers-grid > div:last-child {
  border-right: 0;
  padding-right: 0;
}
.pt-drivers-grid h4 {
  margin: 0 0 0.58rem;
  font-size: 0.78rem;
}
.pt-drivers-grid ul,
.pt-simple-checklist {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.52rem;
}
.pt-drivers-grid li,
.pt-simple-checklist li {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 0.52rem;
  align-items: start;
  color: var(--text);
  font-size: 0.75rem;
  line-height: 1.35;
}
.pt-driver-dot,
.pt-lever-icon {
  width: 1.05rem;
  height: 1.05rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  border: 1px solid currentColor;
  font-size: 0.65rem;
  font-weight: 950;
  position: relative;
  flex: 0 0 auto;
}
.pt-driver-dot .pt-svg-icon,
.pt-lever-icon .pt-svg-icon {
  width: 0.68rem;
  height: 0.68rem;
  stroke-width: 2.6;
}
.pt-driver-dot.good {
  color: var(--green);
  background: rgba(49, 209, 124, 0.1);
}
.pt-driver-dot.bad {
  color: var(--red);
  background: rgba(255, 92, 112, 0.1);
}
.pt-driver-dot.check:before {
  content: "";
  width: 0.5rem;
  height: 0.28rem;
  border-left: 2px solid currentColor;
  border-bottom: 2px solid currentColor;
  transform: rotate(-45deg);
  margin-top: -0.08rem;
}
.pt-driver-dot.alert:before {
  content: "";
  position: absolute;
  width: 0.48rem;
  height: 2px;
  border-radius: 999px;
  background: currentColor;
}
.pt-key-levers li {
  color: var(--muted);
}
.pt-lever-icon {
  color: var(--blue);
  background: rgba(91, 182, 255, 0.08);
}
.pt-driver-dot.info {
  color: var(--blue);
  background: rgba(91, 182, 255, 0.08);
}
.pt-lever-icon:before {
  content: "";
  width: 0.36rem;
  height: 0.36rem;
  border: 2px solid currentColor;
  border-radius: 999px;
  background: rgba(91, 182, 255, 0.08);
}
.pt-lever-icon:after {
  content: "";
  position: absolute;
  left: 0.18rem;
  right: 0.18rem;
  height: 1px;
  background: currentColor;
  opacity: 0.75;
}
.pt-simple-checklist {
  gap: 0.5rem;
}
.pt-status-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem 0.7rem;
  margin: 0 0 0.62rem;
  color: var(--muted);
  font-size: 0.66rem;
}
.pt-status-legend span {
  display: inline-flex;
  align-items: center;
  gap: 0.32rem;
}
.pt-status-legend i {
  width: 0.42rem;
  height: 0.42rem;
  border-radius: 999px;
  display: inline-block;
}
.pt-status-legend i.good {
  background: var(--green);
}
.pt-status-legend i.warn {
  background: var(--yellow);
}
.pt-status-legend i.bad {
  background: var(--red);
}
.pt-simple-checklist li {
  align-items: center;
  font-size: 0.82rem;
  grid-template-columns: minmax(0, 1fr) auto;
}
.pt-simple-checklist li > span {
  min-width: 0;
}
.pt-status-badge {
  border: 1px solid rgba(122, 152, 184, 0.25);
  border-radius: 999px;
  padding: 0.16rem 0.45rem;
  font-size: 0.66rem;
  line-height: 1;
  white-space: nowrap;
}
.pt-status-badge.good {
  border-color: rgba(49, 209, 124, 0.35);
  background: rgba(49, 209, 124, 0.1);
  color: var(--green);
}
.pt-status-badge.warn {
  border-color: rgba(240, 194, 74, 0.38);
  background: rgba(240, 194, 74, 0.1);
  color: var(--yellow);
}
.pt-status-badge.bad {
  border-color: rgba(255, 92, 112, 0.38);
  background: rgba(255, 92, 112, 0.1);
  color: var(--red);
}
.pt-bottom-line {
  color: var(--muted);
  margin: 0.72rem 0 0;
  font-size: 0.73rem;
}
.pt-key-risk-table {
  table-layout: fixed;
}
.pt-key-risk-table th:nth-child(1) {
  width: 18%;
}
.pt-key-risk-table th:nth-child(2) {
  width: 10%;
}
.pt-key-risk-table th:nth-child(3),
.pt-key-risk-table th:nth-child(4) {
  width: 36%;
}
.pt-key-risk-table td {
  line-height: 1.35;
}
.pt-risk-name {
  display: inline-flex;
  align-items: center;
  gap: 0.38rem;
  min-width: 0;
}
.pt-key-risk-table td:first-child b {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.2rem;
  height: 1.2rem;
  border-radius: 999px;
  color: var(--text);
  background: rgba(255, 92, 112, 0.48);
  flex: 0 0 auto;
}
.pt-risk-icon {
  width: 1.25rem;
  height: 1.25rem;
  border: 1px solid rgba(122, 152, 184, 0.3);
  border-radius: 999px;
  color: var(--blue);
  background: rgba(91, 182, 255, 0.06);
  position: relative;
  flex: 0 0 auto;
}
.pt-risk-icon:before,
.pt-risk-icon:after {
  content: "";
  position: absolute;
  display: block;
}
.pt-risk-icon.scaling:before {
  left: 0.34rem;
  top: 0.32rem;
  width: 0.5rem;
  height: 0.5rem;
  border: 2px solid currentColor;
  border-radius: 2px;
  transform: rotate(45deg);
}
.pt-risk-icon.scaling:after {
  left: 0.56rem;
  top: 0.17rem;
  width: 2px;
  height: 0.9rem;
  background: currentColor;
  transform: rotate(45deg);
}
.pt-risk-icon.customer:before,
.pt-risk-icon.customer:after {
  width: 0.36rem;
  height: 0.36rem;
  border: 2px solid currentColor;
  border-radius: 999px;
  top: 0.24rem;
}
.pt-risk-icon.customer:before {
  left: 0.24rem;
}
.pt-risk-icon.customer:after {
  right: 0.24rem;
}
.pt-risk-icon.customer {
  box-shadow: inset 0 -0.42rem 0 -0.25rem currentColor;
}
.pt-risk-icon.dilution:before {
  left: 0.36rem;
  top: 0.3rem;
  width: 0.52rem;
  height: 0.68rem;
  border: 2px solid currentColor;
  border-radius: 0.45rem 0.45rem 0.45rem 0.08rem;
  transform: rotate(45deg);
}
.pt-risk-icon.generic:before {
  left: 0.34rem;
  top: 0.34rem;
  width: 0.52rem;
  height: 0.52rem;
  border: 2px solid currentColor;
  border-radius: 999px;
}
.pt-risk-icon:has(svg):before,
.pt-risk-icon:has(svg):after {
  display: none;
  content: none;
}
.pt-risk-icon .pt-svg-icon {
  width: 0.76rem;
  height: 0.76rem;
  stroke-width: 2.35;
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
}
.pt-changes-table {
  table-layout: fixed;
}
.pt-changes-table th:nth-child(1) {
  width: 7.2rem;
}
.pt-changes-table th:nth-child(3) {
  width: 8.2rem;
}
.pt-changes-table th:nth-child(4),
.pt-changes-table th:nth-child(5),
.pt-changes-table th:nth-child(6) {
  width: 6.6rem;
  text-align: center;
}
.pt-changes-table td:nth-child(4),
.pt-changes-table td:nth-child(5),
.pt-changes-table td:nth-child(6) {
  text-align: center;
}
.pt-changes-table th:nth-child(8) {
  width: 8.5rem;
}
.pt-changes-table td:nth-child(8) {
  color: var(--blue);
  font-weight: 850;
}
.pt-change-dot {
  width: 0.78rem;
  height: 0.78rem;
  display: inline-block;
  border-radius: 999px;
  margin-right: 0.55rem;
  vertical-align: -0.05rem;
  box-shadow: 0 0 0 3px rgba(122, 152, 184, 0.08);
}
.pt-change-dot.good {
  background: var(--green);
  box-shadow: 0 0 0 3px rgba(49, 209, 124, 0.14);
}
.pt-change-dot.bad {
  background: var(--red);
  box-shadow: 0 0 0 3px rgba(255, 92, 112, 0.14);
}
.pt-change-dot.warn {
  background: var(--yellow);
  box-shadow: 0 0 0 3px rgba(240, 194, 74, 0.14);
}
.pt-advanced-details {
  padding: 0.9rem 1rem;
}
.pt-advanced-details summary {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 0.9rem;
  align-items: center;
  cursor: pointer;
  list-style: none;
}
.pt-advanced-details summary::-webkit-details-marker {
  display: none;
}
.pt-lock-icon {
  width: 2rem;
  height: 2rem;
  border: 1px solid rgba(122, 152, 184, 0.28);
  border-radius: 7px;
  background: rgba(122, 152, 184, 0.08);
  position: relative;
}
.pt-lock-icon:before,
.pt-lock-icon:after {
  content: "";
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}
.pt-lock-icon:before {
  width: 0.8rem;
  height: 0.55rem;
  border: 2px solid var(--muted);
  border-bottom: 0;
  border-radius: 0.5rem 0.5rem 0 0;
  top: 0.42rem;
}
.pt-lock-icon:after {
  width: 1rem;
  height: 0.78rem;
  border-radius: 3px;
  background: var(--muted);
  bottom: 0.38rem;
}
.pt-advanced-details strong {
  color: var(--text);
  text-transform: uppercase;
  font-size: 0.82rem;
}
.pt-advanced-details strong small {
  color: var(--muted);
  text-transform: none;
}
.pt-advanced-details p {
  color: var(--muted);
  margin: 0.2rem 0 0;
  font-size: 0.72rem;
}
.pt-accordion-caret {
  width: 0.68rem;
  height: 0.68rem;
  border-right: 2px solid var(--muted);
  border-bottom: 2px solid var(--muted);
  transform: rotate(-45deg);
  opacity: 0.72;
  transition: transform 0.16s ease;
}
.pt-advanced-details[open] .pt-accordion-caret {
  transform: rotate(45deg);
}
.pt-advanced-content {
  border-top: 1px solid rgba(122, 152, 184, 0.16);
  display: grid;
  gap: 0.72rem;
  margin-top: 0.85rem;
  padding-top: 0.85rem;
}
@media (max-width: 1280px) {
  .pt-quality-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
  .pt-header,
  .pt-grid-two,
  .pt-grid-three,
  .pt-decision-row,
  .pt-decision-main,
  .pt-decision-breakdown,
  .pt-decision-quick,
  .pt-decision-score-grid,
  .pt-drivers-grid,
  .pt-expected-strip,
  .pt-row-valuation,
  .pt-row-assumptions,
  .pt-row-impact,
  .pt-row-bottom,
  .pt-fv-grid,
  .pt-final-grid,
  .pt-home-grid,
  .pt-social-readthrough,
  .pt-social-metrics,
  .pt-thesis-grid {
    grid-template-columns: 1fr;
  }
  .pt-header-market,
  .pt-header-signal {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .pt-decision-main {
    align-items: start;
  }
  .pt-decision-quick {
    border-left: 0;
  }
  .pt-decision-quick .pt-kv-row {
    border-right: 0;
    border-bottom: 1px solid rgba(122, 152, 184, 0.14);
    padding: 0.42rem 0;
  }
  .pt-methodology {
    width: max-content;
  }
  .pt-drivers-grid > div {
    border-right: 0;
    border-bottom: 1px solid rgba(122, 152, 184, 0.14);
    padding: 0 0 0.8rem;
  }
  .pt-drivers-grid > div:last-child {
    border-bottom: 0;
    padding-bottom: 0;
  }
}
@media (max-width: 760px) {
  .stApp .block-container {
    padding-left: 0.75rem;
    padding-right: 0.75rem;
  }
  .pt-quality-grid,
  .pt-quality-pillars,
  .pt-quality-summary,
  .pt-summary-grid,
  .pt-signal-grid,
  .pt-scenario-grid,
  .pt-decision-scenarios,
  .pt-score-breakdown,
  .pt-header-market,
  .pt-header-signal,
  .pt-mover-grid,
  .pt-trigger-grid,
  .pt-scanner-summary,
  .pt-scanner-detail-grid,
  .pt-news-summary,
  .pt-news-card-meta,
  .pt-news-detail-grid,
  .pt-sector-brief,
  .pt-sector-brief-stats,
  .pt-sector-meaning,
  .pt-sector-flow-heatmap,
  .pt-sector-rotation-summary,
  .pt-sector-drivers,
  .pt-sector-next,
  .pt-sector-money-columns,
  .pt-sector-hero,
  .pt-sector-hero-stats,
  .pt-sector-mini-grid,
  .pt-sector-theme-grid,
  .pt-sector-beneficiary-grid,
  .pt-sector-beneficiary-metrics,
  .pt-sector-timeline,
  .pt-sector-insights,
  .pt-sector-bottom-line > div,
  .pt-sector-health {
    grid-template-columns: 1fr;
  }
  .pt-sector-research-row {
    grid-template-columns: 20px 30px minmax(0, 1fr) auto;
  }
  .pt-sector-research-row > div:nth-of-type(n + 3) {
    display: none;
  }
  .pt-sector-research-row em {
    grid-column: 3 / -1;
    justify-self: start;
  }
  .pt-sector-persistence-takeaway {
    align-items: flex-start;
    grid-template-columns: 1fr;
  }
  .pt-sector-brief-main {
    border-bottom: 1px solid var(--border-soft);
    border-right: 0;
    padding-bottom: 0.7rem;
    padding-right: 0;
  }
  .pt-sector-hero > div:first-child {
    border-bottom: 1px solid var(--border-soft);
    border-right: 0;
    padding-bottom: 0.7rem;
    padding-right: 0;
  }
  .pt-scanner-meta,
  .pt-scanner-source,
  .pt-news-feed-status,
  .pt-news-card-head {
    align-items: flex-start;
    flex-direction: column;
  }
  .pt-social-section-head {
    align-items: flex-start;
    flex-direction: column;
  }
  .pt-social-source {
    align-items: flex-start;
    justify-items: start;
  }
  .pt-scanner-source span:last-child,
  .pt-news-feed-status span:last-child {
    margin-left: 0;
  }
  .pt-calendar-weekdays {
    display: none;
  }
  .pt-calendar-grid {
    grid-template-columns: 1fr;
  }
  .pt-calendar-day {
    min-height: auto;
  }
  .pt-topbar {
    grid-template-columns: 1fr;
  }
  .pt-decision-shell .pt-header,
  .pt-decision-card {
    padding: 0.8rem;
  }
  .pt-decision-icon {
    width: 3.2rem;
    height: 3.2rem;
  }
  .pt-decision-copy strong {
    font-size: 1.45rem;
  }
  .pt-quality-pillar {
    border-right: 0 !important;
  }
  .pt-quality-pillar:nth-child(n+3) {
    border-bottom: 1px solid rgba(122, 152, 184, 0.14);
  }
  .pt-key-risk-table,
  .pt-changes-table {
    min-width: 720px;
  }
}

/* Terminal density and hierarchy */
* {
  letter-spacing: 0 !important;
}
:root {
  --bg: #020507;
  --bg-2: #05090c;
  --panel: #080d11;
  --panel-2: #0c1318;
  --panel-3: #111a20;
  --border: #29343c;
  --border-soft: rgba(132, 148, 158, 0.24);
  --text: #e8edf0;
  --muted: #a3adb5;
  --faint: #6f7b84;
  --green: #35d07f;
  --green-2: #74dda0;
  --red: #ff626d;
  --yellow: #f2a900;
  --blue: #36a9e1;
  --teal: #42c8bd;
}
.stApp {
  background: #020507 !important;
  font-family: "Segoe UI", Arial, sans-serif;
}
.stApp .block-container {
  padding: 2.65rem 0.68rem 1.35rem;
}
button,
input,
textarea,
select,
.pt-card,
.pt-header,
.pt-section,
.pt-row-card,
.pt-social-table-wrap,
.pt-social-theme-card,
.pt-detail-card,
.pt-news-card,
.pt-eco-event {
  border-radius: 2px !important;
}
[data-testid="stSidebar"] {
  background: #05090c !important;
  border-right: 1px solid #303941;
}
[data-testid="stSidebar"] .block-container {
  padding: 0.72rem 0.58rem 1rem;
}
.pt-brand {
  border-bottom: 1px solid var(--border);
  margin: 0 -0.1rem 0.55rem;
  padding: 0.16rem 0.18rem 0.72rem;
}
.pt-brand-mark {
  background: var(--yellow);
  border-radius: 1px;
  color: #050505;
  font-family: Consolas, "Cascadia Mono", monospace;
}
.pt-brand strong span {
  color: var(--yellow);
}
[data-testid="stSidebar"] [role="radiogroup"] {
  gap: 1px;
}
[data-testid="stSidebar"] [role="radiogroup"] label {
  border-left: 3px solid transparent;
  margin: 0;
  min-height: 2.05rem;
  padding: 0.28rem 0.45rem;
}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
  background: #11171b;
  border-left-color: var(--yellow);
  color: var(--yellow);
}
[data-testid="stSidebar"] [role="radiogroup"] label p {
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: uppercase;
}
.pt-side-title {
  color: var(--yellow);
  font-family: Consolas, "Cascadia Mono", monospace;
  font-size: 0.66rem;
  margin-top: 0.78rem;
}
.pt-watch-price,
.pt-watch-change,
.pt-kpi strong,
.pt-row-card strong,
.pt-decision-score strong,
.pt-table td,
.pt-social-table td,
[data-testid="stDataFrame"] {
  font-family: Consolas, "Cascadia Mono", monospace;
}
.pt-topbar {
  margin: 0;
  min-height: 2rem;
}
.pt-breadcrumb {
  color: #84909a;
  font-family: Consolas, "Cascadia Mono", monospace;
  font-size: 0.68rem;
  text-transform: uppercase;
}
.pt-breadcrumb span {
  background: var(--yellow);
  color: #050505;
  display: inline-block;
  font-weight: 950;
  margin-right: 0.25rem;
  padding: 0.1rem 0.3rem;
}
.pt-breadcrumb b {
  color: var(--yellow);
}
[data-testid="stTextInput"] input {
  background: #05090c;
  border-color: #35424b;
  border-radius: 1px !important;
  font-family: Consolas, "Cascadia Mono", monospace;
  min-height: 2rem;
}
[data-testid="stTextInput"] input:focus {
  border-color: var(--yellow);
  box-shadow: 0 0 0 1px rgba(242, 169, 0, 0.28);
}
[data-testid="stButton"] button,
[data-testid="stDownloadButton"] button {
  background: #0a1014;
  border-color: #34414a;
  min-height: 2rem;
}
[data-testid="stButton"] button:hover,
[data-testid="stDownloadButton"] button:hover {
  border-color: var(--yellow);
  color: var(--yellow);
}
[data-testid="stSegmentedControl"] {
  margin-bottom: 0.3rem;
}
[data-testid="stSegmentedControl"] button {
  background: #080d11 !important;
  border-color: #303b43 !important;
  border-radius: 1px !important;
  color: var(--muted) !important;
  min-height: 1.9rem;
  text-transform: uppercase;
}
[data-testid="stSegmentedControl"] button[aria-pressed="true"] {
  background: var(--yellow) !important;
  color: #090909 !important;
}
.pt-shell {
  gap: 0.42rem;
}
.pt-card,
.pt-header,
.pt-section {
  background: #080d11;
  border-color: var(--border);
  box-shadow: none;
}
.pt-workspace-head {
  align-items: flex-end;
  background: #05090c;
  border: 1px solid var(--border);
  border-top: 2px solid var(--yellow);
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.38rem;
  padding: 0.55rem 0.72rem;
}
.pt-workspace-head span,
.pt-workspace-head > b {
  color: var(--yellow);
  font-family: Consolas, "Cascadia Mono", monospace;
  font-size: 0.62rem;
  text-transform: uppercase;
}
.pt-workspace-head h1 {
  color: var(--text);
  font-size: 1.45rem;
  line-height: 1.1;
  margin: 0.1rem 0 0;
}
.pt-workspace-head p {
  color: var(--muted);
  font-size: 0.72rem;
  margin: 0.15rem 0 0;
}
.pt-section {
  padding: 0.58rem 0.66rem;
}
.pt-section-title {
  border-bottom: 1px solid #313b43;
  margin: -0.1rem -0.1rem 0.42rem;
  min-height: 1.55rem;
  padding: 0 0.1rem 0.34rem;
}
.pt-section-title > span,
.pt-section-title.flat span,
.pt-social-subhead {
  color: var(--yellow) !important;
  font-family: Consolas, "Cascadia Mono", monospace;
  font-size: 0.68rem !important;
  font-weight: 900;
  text-transform: uppercase;
}
.pt-section-title small {
  color: #7e8992;
  font-size: 0.62rem;
}
.pt-header {
  background: #060a0d;
  border-top: 2px solid var(--yellow);
  gap: 0.58rem;
  grid-template-columns: minmax(250px, 1.18fr) minmax(420px, 1.55fr) minmax(240px, 0.9fr);
  padding: 0.62rem;
}
.pt-ticker {
  color: var(--yellow);
  font-family: Consolas, "Cascadia Mono", monospace;
  font-size: 1.62rem;
}
.pt-tag,
.pt-pill,
.pt-status-pill,
.pt-social-badge {
  border-radius: 1px !important;
  font-family: Consolas, "Cascadia Mono", monospace;
}
.pt-header-market {
  background: #090f13;
  border: 1px solid var(--border);
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  padding: 0.42rem;
}
.pt-header-signal,
.pt-decision-shell .pt-header-signal {
  align-items: center;
  background: #0c1114;
  border: 1px solid rgba(242, 169, 0, 0.42);
  border-radius: 1px;
  display: flex;
  grid-template-columns: none;
  justify-content: space-between;
  padding: 0.5rem 0.62rem;
}
.pt-decision-shell .pt-signal-kpi {
  align-items: center;
  display: flex;
  justify-content: space-between;
  width: 100%;
}
.pt-decision-shell .pt-signal-kpi strong {
  font-size: 1.32rem;
}
.pt-decision-shell .pt-signal-kpi span {
  color: var(--yellow);
}
.pt-decision-card {
  border-left: 3px solid var(--yellow);
  padding: 0.72rem 0.82rem;
}
.pt-decision-main {
  gap: 0.72rem;
  grid-template-columns: minmax(0, 1.4fr) minmax(420px, 1.2fr);
}
.pt-decision-icon {
  display: none;
}
.pt-decision-copy strong {
  font-family: Consolas, "Cascadia Mono", monospace;
  font-size: 1.55rem;
}
.pt-bottom-line-callout,
.pt-analyst-brief {
  background: #0c1216;
  border-left: 2px solid var(--yellow);
  border-radius: 0;
}
.pt-analyst-brief {
  margin-top: 0.45rem;
  padding: 0.48rem 0.58rem;
}
.pt-analyst-brief span {
  color: var(--yellow);
  font-family: Consolas, "Cascadia Mono", monospace;
  font-size: 0.62rem;
  font-weight: 900;
  text-transform: uppercase;
}
.pt-analyst-brief p {
  color: var(--muted);
  font-size: 0.72rem;
  line-height: 1.45;
  margin: 0.16rem 0 0;
}
.pt-analyst-brief b {
  color: var(--text);
}
.pt-decision-score i,
.pt-progress i {
  border-radius: 0;
}
.pt-quality-pillar,
.pt-decision-scenario,
.pt-row-card {
  background: #090f13;
}
.pt-line-icon,
.pt-lock-icon {
  border-radius: 2px;
}
.pt-social-market-shell {
  background: #070c0f;
  border-top: 2px solid #36a9e1;
  margin: 0.48rem 0 0.18rem;
  padding: 0.55rem 0.68rem;
}
.pt-social-section-head strong {
  color: #dce6ec;
  font-size: 0.96rem;
  text-transform: uppercase;
}
.pt-social-metric-grid {
  gap: 1px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.pt-social-metric-grid .pt-row-card {
  border-radius: 0 !important;
  border-color: #2c3740;
  padding: 0.42rem 0.5rem;
}
.pt-social-subhead {
  background: #080d11;
  border: 1px solid var(--border);
  border-left: 3px solid #36a9e1;
  margin: 0.32rem 0 0;
  padding: 0.32rem 0.48rem;
}
.pt-social-table-wrap {
  border-top: 0;
}
.pt-social-market-table {
  min-width: 960px;
}
.pt-social-table {
  background: #05090c;
  min-width: 900px;
}
.pt-social-table th,
.pt-social-table td,
.pt-table th,
.pt-table td {
  border-color: #263139;
  padding: 0.3rem 0.38rem;
}
.pt-social-table th,
.pt-table th {
  background: #0d1419;
  color: #98a4ac;
}
.pt-social-table tbody tr:hover,
.pt-table tbody tr:hover {
  background: rgba(54, 169, 225, 0.07);
}
.pt-gauge-hub {
  stroke: #05090c;
}
.pt-active-quote-card {
  display: none;
}
.pt-company-research-shell {
  background: #070c0f;
  border-top: 2px solid #d69a2d;
  margin: 0.48rem 0;
  padding: 0.62rem 0.68rem;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.pt-chart-anchor) {
  background: #070c0f !important;
  border: 1px solid #344049 !important;
  border-radius: 0 !important;
  border-top: 2px solid #d69a2d !important;
  padding: 0.5rem 0.62rem 0.58rem !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.pt-chart-anchor) [data-testid="stPlotlyChart"] {
  background: #070c0f;
  border: 1px solid #263139;
  min-width: 0;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.pt-chart-anchor) [data-testid="stHorizontalBlock"] {
  gap: 0.48rem;
}
.pt-chart-anchor {
  border-bottom: 1px solid #303b43;
  margin-bottom: 0.08rem;
  padding: 0 0 0.42rem;
  position: relative;
}
.pt-chart-anchor > span,
.pt-thesis-workbench-head > span {
  color: #d69a2d;
  display: block;
  font-size: 0.66rem;
  font-weight: 800;
  letter-spacing: 0.06em;
}
.pt-chart-anchor h2 {
  color: #edf2f5;
  font-size: 1.05rem;
  margin: 0.08rem 0 0.12rem;
}
.pt-chart-anchor p {
  color: #8f9ca4;
  font-size: 0.7rem;
  margin: 0;
}
.pt-chart-coverage {
  border-left: 1px solid #354049;
  min-width: 100px;
  padding-left: 0.7rem;
  position: absolute;
  right: 0;
  text-align: right;
  top: 0;
}
.pt-chart-coverage span,
.pt-chart-coverage small {
  color: #7f8d95;
  display: block;
  font-size: 0.59rem;
  text-transform: uppercase;
}
.pt-chart-coverage b {
  color: #edf2f5;
  display: block;
  font-size: 1rem;
}
.pt-decision-figures {
  border: 1px solid #29343c;
  display: grid;
  gap: 1px;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  margin-top: 0.1rem;
}
.pt-decision-figure {
  background: #0c1318;
  min-width: 0;
  padding: 0.42rem 0.46rem;
}
.pt-decision-figure span,
.pt-decision-figure strong,
.pt-decision-figure small {
  display: block;
}
.pt-decision-figure span {
  color: #8d9aa2;
  font-size: 0.59rem;
  font-weight: 800;
  min-height: 1.8em;
  text-transform: uppercase;
}
.pt-decision-figure strong {
  color: #edf2f5;
  font-size: 0.9rem;
  margin: 0.16rem 0 0.08rem;
}
.pt-decision-figure small {
  color: #74828a;
  font-size: 0.58rem;
  line-height: 1.25;
}
.pt-thesis-workbench {
  background: #090f13;
  border: 1px solid #344049;
  border-left: 3px solid #d69a2d;
  display: grid;
  grid-template-columns: 175px 1fr;
  margin-top: 0.5rem;
}
.pt-thesis-workbench-head {
  border-right: 1px solid #344049;
  padding: 0.52rem;
}
.pt-thesis-workbench-head strong,
.pt-thesis-workbench-head small {
  display: block;
}
.pt-thesis-workbench-head strong {
  color: #edf2f5;
  font-size: 0.78rem;
  line-height: 1.3;
  margin-top: 0.2rem;
}
.pt-thesis-workbench-head small {
  color: #6f7c84;
  font-size: 0.56rem;
  margin-top: 0.35rem;
}
.pt-thesis-workbench-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.pt-thesis-workbench-grid > div {
  border-bottom: 1px solid #273139;
  border-right: 1px solid #273139;
  padding: 0.42rem 0.48rem;
}
.pt-thesis-workbench-grid span {
  color: #d69a2d;
  display: block;
  font-size: 0.58rem;
  font-weight: 800;
  text-transform: uppercase;
}
.pt-thesis-workbench-grid p {
  color: #b7c0c5;
  font-size: 0.64rem;
  line-height: 1.35;
  margin: 0.16rem 0 0;
}
.pt-peer-figures {
  grid-template-columns: repeat(5, minmax(0, 1fr));
  margin-bottom: 0.45rem;
}
.pt-chart-empty {
  border-left: 3px solid #d69a2d;
  color: #8f9ca4;
  font-size: 0.72rem;
  margin: 0.45rem 0;
  padding: 0.5rem;
}
.pt-chart-empty strong {
  color: #d69a2d;
}
.pt-chart-empty p {
  margin: 0.18rem 0 0;
}
.pt-research-head {
  align-items: flex-end;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
  margin-bottom: 0.55rem;
}
.pt-research-head > div:first-child > span,
.pt-recommendation-read > span,
.pt-peer-read > span {
  color: #d69a2d;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.06em;
}
.pt-research-head h2 {
  color: #edf2f5;
  font-size: 1.08rem;
  margin: 0.08rem 0 0.12rem;
}
.pt-research-head p,
.pt-recommendation-read p,
.pt-peer-read p {
  color: #9ba8b0;
  font-size: 0.76rem;
  margin: 0;
}
.pt-research-verdict {
  border-left: 1px solid #354049;
  min-width: 150px;
  padding-left: 0.8rem;
  text-align: right;
}
.pt-research-verdict span,
.pt-research-verdict small {
  color: #87949d;
  display: block;
  font-size: 0.65rem;
  text-transform: uppercase;
}
.pt-research-verdict b {
  color: #edf2f5;
  display: block;
  font-size: 1.08rem;
  margin: 0.08rem 0;
}
.pt-lt-grid {
  display: grid;
  gap: 1px;
  grid-template-columns: repeat(6, minmax(0, 1fr));
}
.pt-lt-metric {
  background: #0c1318;
  border: 1px solid #29343c;
  min-width: 0;
  padding: 0.52rem;
}
.pt-lt-metric-head {
  align-items: flex-start;
  display: flex;
  gap: 0.35rem;
  justify-content: space-between;
}
.pt-lt-metric-head span {
  color: #aeb8be;
  font-size: 0.67rem;
  font-weight: 800;
  text-transform: uppercase;
}
.pt-lt-metric-head b,
.pt-peer-badge {
  border: 1px solid currentColor;
  font-size: 0.6rem;
  padding: 0.06rem 0.2rem;
  white-space: nowrap;
}
.pt-lt-metric > strong {
  color: #edf2f5;
  display: block;
  font-size: 1rem;
  margin-top: 0.34rem;
}
.pt-lt-metric > small {
  color: #8e9ba4;
  display: block;
  font-size: 0.64rem;
  min-height: 1.1rem;
}
.pt-trend-spark {
  height: 42px;
  margin: 0.2rem 0 0.08rem;
  width: 100%;
}
.pt-trend-spark polyline {
  fill: none;
  stroke: #a8b2b8;
  stroke-width: 2;
  vector-effect: non-scaling-stroke;
}
.pt-trend-spark.good polyline { stroke: #48c97a; }
.pt-trend-spark.warn polyline { stroke: #e0ad42; }
.pt-trend-spark.bad polyline { stroke: #ee6670; }
.pt-trend-empty {
  color: #66747d;
  font-size: 0.62rem;
  height: 42px;
  padding-top: 0.8rem;
}
.pt-lt-metric p {
  color: #99a6ae;
  font-size: 0.67rem;
  line-height: 1.35;
  margin: 0.18rem 0 0;
}
.pt-recommendation-read,
.pt-peer-read {
  align-items: center;
  background: #0a1115;
  border-left: 3px solid #d69a2d;
  display: grid;
  gap: 0.45rem;
  grid-template-columns: 140px 100px 1fr;
  margin-top: 0.48rem;
  padding: 0.42rem 0.5rem;
}
.pt-recommendation-read strong {
  font-size: 0.9rem;
}
.pt-source-foot {
  color: #66747d;
  font-size: 0.6rem;
  margin-top: 0.34rem;
  text-align: right;
}
.pt-peer-table-wrap {
  border: 1px solid #29343c;
  overflow-x: auto;
}
.pt-peer-table {
  border-collapse: collapse;
  font-size: 0.69rem;
  min-width: 880px;
  width: 100%;
}
.pt-peer-table th,
.pt-peer-table td {
  border-bottom: 1px solid #263139;
  padding: 0.38rem 0.42rem;
  text-align: right;
}
.pt-peer-table th:first-child,
.pt-peer-table td:first-child {
  text-align: left;
}
.pt-peer-table th {
  background: #0d1419;
  color: #929ea6;
  font-size: 0.62rem;
  text-transform: uppercase;
}
.pt-peer-table td {
  color: #c8d0d5;
}
.pt-peer-table td strong,
.pt-peer-table td small {
  display: block;
}
.pt-peer-table td small {
  color: #75838c;
  font-size: 0.6rem;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pt-peer-table tr.selected {
  background: rgba(214, 154, 45, 0.1);
  box-shadow: inset 3px 0 #d69a2d;
}
.pt-peer-read {
  grid-template-columns: 140px 1fr;
}
.pt-live-ticker-shell,
.pt-watch-tape {
  contain: paint;
  max-width: 100%;
  min-width: 0;
  overflow: hidden;
}
@media (max-width: 1180px) {
  .pt-header,
  .pt-decision-main {
    grid-template-columns: 1fr;
  }
  .pt-header-market {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .pt-decision-quick {
    border-left: 0;
  }
  .pt-lt-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .pt-decision-figures {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
  .pt-peer-figures {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 760px) {
  [data-testid="stMain"] {
    overflow-x: hidden !important;
  }
  [data-testid="stMain"] [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
    gap: 0.35rem !important;
    max-width: 100% !important;
    width: 100% !important;
  }
  [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    flex: 1 1 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    width: 100% !important;
  }
  .pt-breadcrumb {
    overflow-wrap: anywhere;
    white-space: normal;
  }
  .pt-workspace-head {
    align-items: flex-start;
    flex-direction: column;
    gap: 0.4rem;
  }
  .pt-header-market,
  .pt-social-metric-grid {
    grid-template-columns: 1fr 1fr;
  }
  .pt-research-head {
    align-items: flex-start;
    flex-direction: column;
  }
  .pt-research-verdict {
    border-left: 0;
    border-top: 1px solid #354049;
    padding-left: 0;
    padding-top: 0.4rem;
    text-align: left;
    width: 100%;
  }
  .pt-lt-grid {
    grid-template-columns: 1fr 1fr;
  }
  .pt-recommendation-read,
  .pt-peer-read {
    align-items: flex-start;
    grid-template-columns: 1fr;
  }
  .pt-chart-coverage {
    border-left: 0;
    border-top: 1px solid #354049;
    margin-top: 0.35rem;
    padding-left: 0;
    padding-top: 0.3rem;
    position: static;
    text-align: left;
  }
  .pt-decision-figures,
  .pt-peer-figures {
    grid-template-columns: 1fr 1fr;
  }
  .pt-thesis-workbench {
    grid-template-columns: 1fr;
  }
  .pt-thesis-workbench-head {
    border-bottom: 1px solid #344049;
    border-right: 0;
  }
  .pt-thesis-workbench-grid {
    grid-template-columns: 1fr;
  }
}
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
