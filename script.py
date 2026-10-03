"""Launch NEON//HUB, a local cybersecurity command station.

    python script.py
    python script.py --offline
"""
import argparse
import json
from pathlib import Path
import sys

from hub_ui import CyberHub


def main():
    parser = argparse.ArgumentParser(description="NEON//HUB cybersecurity command station")
    parser.add_argument("--offline", action="store_true", help="Start with public news requests disabled.")
    parser.add_argument("--data-dir", type=Path, help="Use a separate local workspace directory.")
    parser.add_argument("--smoke-test", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    app = CyberHub(data_dir=args.data_dir, start_network=not args.offline and not args.smoke_test)
    if args.offline:
        app.store.state["settings"]["online_news"] = False
        app.online_news.set(False)
        app.refresh_dashboard()
    if args.smoke_test:
        app.withdraw()
        errors = []
        app.report_callback_exception = lambda kind, value, trace: errors.append(str(value))
        try:
            app.update()
            app.expression.set("0xFF & 0b1010")
            app.calculate()
            assert app.result.get() == "10"
            app.float_preset("-0.0")
            assert app.float_data["sign"] == "1"
            app.graph_preset("x ** 2")
            assert len(app.graph_series) == 1
            app.open_tool("Nmap")
            assert app.generated_command.startswith("nmap")
            app.update()
            assert not errors, errors
            report = {"ok": True, "screens": len(app.pages), "frozen": bool(getattr(sys, "frozen", False)),
                      "checks": ["calculator", "IEEE-754", "graph", "command library", "Tk callbacks"]}
        except Exception as exc:
            report = {"ok": False, "error": str(exc), "callback_errors": errors}
        finally:
            app.close()
        args.smoke_test.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 0 if report["ok"] else 1
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

