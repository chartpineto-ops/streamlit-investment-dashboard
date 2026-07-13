from __future__ import annotations

import argparse
import time

from services.economic_data_service import fetch_macro_dashboard, macro_poll_interval_seconds
from services.macro_alert_service import process_macro_updates


def run_once() -> int:
    frame = fetch_macro_dashboard()
    alerts = process_macro_updates(frame)
    for alert in alerts:
        print(f"[{alert['delivery_status']}] {alert['message']}", flush=True)
    return len(alerts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor official macro releases and deliver PineTerminal alerts.")
    parser.add_argument("--once", action="store_true", help="Check once and exit.")
    args = parser.parse_args()
    while True:
        run_once()
        if args.once:
            return
        time.sleep(macro_poll_interval_seconds())


if __name__ == "__main__":
    main()
