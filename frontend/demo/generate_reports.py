"""Regenerate the public demo fixtures from fixed synthetic source data."""
import json
from pathlib import Path

from nexa_scriptguard.analysis import analyze
from nexa_scriptguard.ingestion import Source
from nexa_scriptguard.limits import ScanLimits
from nexa_scriptguard.redaction import prepare_report
from nexa_scriptguard.reports import render_html, render_json, render_sarif, rules_for_report
from nexa_scriptguard.rules import RULES_PATH


def main():
    output = Path(__file__).resolve().parent / "public" / "reports"
    output.mkdir(parents=True, exist_ok=True)
    source = Source(Path("synthetic.py"), b'api_token = "synthetic_example"\nvalue = eval("1+1")\n', -1, -1)
    report = prepare_report(analyze(source.path, ScanLimits(), source=source).to_dict())
    report["analyzed_at_utc"] = "2026-11-26T00:00:00+00:00"
    report["demo"] = "DEMO MODE — SYNTHETIC DATA"
    (output / "synthetic.json").write_bytes(render_json(report))
    html = render_html(report).replace("</header>", "<p>DEMO MODE — SYNTHETIC DATA</p></header>", 1)
    (output / "synthetic.html").write_text(html, encoding="utf-8", newline="\n")
    rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    sarif = render_sarif(report, rules_for_report(report, rules))
    sarif["runs"][0]["properties"]["demo"] = report["demo"]
    (output / "synthetic.sarif").write_text(json.dumps(sarif, ensure_ascii=False, indent=2) + "\n",
                                              encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
