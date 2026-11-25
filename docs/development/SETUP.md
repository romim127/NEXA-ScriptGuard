# Development setup

## Windows PowerShell

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install ".[test]"
python -m nexa_scriptguard.gui
```

The GUI binds only to loopback. Keep the process running while using the
private URL it prints; `Ctrl+C` stops it. The optional helper is built with:

```powershell
cargo build --manifest-path rust\nexa-scriptguard-helper\Cargo.toml
```

## Linux and macOS

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install ".[test]"
python -m nexa_scriptguard.gui
```

CI declares Windows, Ubuntu, and macOS with Python 3.10 and 3.12. This
documentation does not claim that every OS was tested locally.
