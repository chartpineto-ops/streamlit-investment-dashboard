from __future__ import annotations

from utils.rendering import render_html, safe_text


def _status_class(status: object) -> str:
    value = str(status or "unknown").casefold()
    if value in {"good", "ok", "live", "fresh"}:
        return "good"
    if value in {"warn", "warning", "pending", "stale", "unknown"}:
        return "warn"
    return "bad"


def render_data_freshness_bar(status_items: list[dict[str, object]]) -> None:
    html_parts = []

    for item in status_items:
        label = safe_text(item.get("label", "Unknown"))
        refreshed = safe_text(item.get("refreshed", "N/A"))
        title = safe_text(item.get("title") or item.get("source") or "")
        status_class = _status_class(item.get("status", "unknown"))

        html_parts.append(
            f"""
            <span class="freshness-pill" title="{title}">
                <b>{label}</b>
                <em class="{status_class}">refreshed {refreshed}</em>
            </span>
            """
        )

    render_html(
        f"""
        <div class="freshness-bar">
            {"".join(html_parts)}
        </div>

        <style>
        .freshness-bar {{
            display: flex;
            gap: 10px;
            align-items: center;
            justify-content: flex-end;
            flex-wrap: wrap;
            font-size: 12px;
            margin-bottom: 8px;
        }}

        .freshness-pill {{
            display: inline-flex;
            gap: 6px;
            align-items: center;
            padding: 4px 8px;
            border-radius: 999px;
            background: rgba(18, 26, 36, 0.95);
            border: 1px solid rgba(90, 110, 130, 0.35);
            color: #d7e1ea;
            white-space: nowrap;
        }}

        .freshness-pill b {{
            color: #f3f6f9;
            font-weight: 700;
        }}

        .freshness-pill em {{
            font-style: normal;
            font-weight: 600;
        }}

        .freshness-pill em.good {{
            color: #58d68d;
        }}

        .freshness-pill em.warn {{
            color: #f4d03f;
        }}

        .freshness-pill em.bad {{
            color: #ff6b6b;
        }}
        </style>
        """
    )
