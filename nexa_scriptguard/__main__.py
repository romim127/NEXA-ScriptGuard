import sys

from .cli import main
from .legacy import inspect, render_html, render_sarif
from .redaction import redact_report

__all__ = ["main", "inspect", "render_html", "render_sarif", "redact_report"]


if __name__ == "__main__":
    sys.exit(main())
