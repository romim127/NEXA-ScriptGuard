import os
import sys
from pathlib import Path


Path(os.environ["NEXA_BROWSER_CAPTURE"]).write_text(sys.argv[1], encoding="utf-8")
