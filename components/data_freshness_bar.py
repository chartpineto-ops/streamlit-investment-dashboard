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
            <span class="freshness-item" title="{title}">
                <b>{label}</b>
                <i class="{status_class}"></i>
                <em class="{status_class}">{refreshed}</em>
            </span>
            """
        )

    render_html(
        f"""
        <div class="freshness-bar">
            <strong>DATA</strong>
            {"".join(html_parts)}
        </div>

        <style>
        .freshness-bar {{
            display: flex;
            gap: 0;
            align-items: center;
            justify-content: flex-start;
            flex-wrap: wrap;
            min-height: 26px;
            border-top: 1px solid #26313a;
            border-bottom: 1px solid #26313a;
            background: #05090c;
            color: #aab3bb;
            font-family: Consolas, "Cascadia Mono", monospace;
            font-size: 10px;
            margin: 0 0 6px;
        }}

        .freshness-bar > strong {{
            align-self: stretch;
            display: inline-flex;
            align-items: center;
            padding: 0 10px;
            color: #f2a900;
            border-right: 1px solid #26313a;
            letter-spacing: .08em;
        }}

        .freshness-item {{
            display: inline-flex;
            gap: 6px;
            align-items: center;
            min-height: 25px;
            padding: 0 9px;
            border-right: 1px solid #26313a;
            white-space: nowrap;
        }}

        .freshness-item b {{
            color: #dce3e8;
            font-weight: 800;
            text-transform: uppercase;
        }}

        .freshness-item i {{
            width: 5px;
            height: 5px;
            border-radius: 50%;
            background: currentColor;
        }}

        .freshness-item em {{
            font-style: normal;
            font-weight: 600;
        }}

        .freshness-item .good {{
            color: #58d68d;
        }}

        .freshness-item .warn {{
            color: #f4d03f;
        }}

        .freshness-item .bad {{
            color: #ff6b6b;
        }}
        </style>
        """
    )
