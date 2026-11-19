"""NEXA ScriptGuard — experimental read-only shell-script analyzer."""
import argparse
import copy
import datetime as dt
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from .contextual import correlated_findings

SEVERITY = {"CRITICAL":4,"HIGH":3,"MEDIUM":2,"LOW":1,"INFO":0}
MAX_BYTES = 5 * 1024 * 1024
REDACT = re.compile(r"(?i)(\b(?:password|passwd|api[_-]?key|secret|token)\s*[=:]\s*[\"']?)([^\s\"']+)")

def inspect(target, rules):
    with target.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Input exceeds the 5 MiB limit")
    lines = data.decode("utf-8", errors="replace").splitlines()
    findings = []
    for number, line in enumerate(lines, 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        for rule in rules:
            for match in re.finditer(rule["pattern"], line, re.IGNORECASE):
                findings.append(dict(rule_id=rule["id"],severity=rule["severity"],title=rule["title"],
                    line=number,column=match.start()+1,instruction=line,matched_fragment=match.group(0),
                    explanation=rule["why"],recommendation=rule["recommendation"],
                    verification_commands=rule["checks"],confidence="heuristic",status="requires_review",
                    context_before=lines[max(0,number-3):number-1],
                    context_after=lines[number:min(len(lines),number+2)]))
    findings.extend(correlated_findings(lines))
    findings.sort(key=lambda f:(-SEVERITY[f["severity"]],f["line"],f["column"]))
    return dict(tool="NEXA ScriptGuard",version="0.4.0-alpha",
        analyzed_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        file=str(target),sha256=hashlib.sha256(data).hexdigest(),
        lines=len(lines),findings=findings,
        limitations="Heuristic rules and limited variable correlation; not a complete Bash parser. No findings does not prove safety.")

def redact_report(report):
    result = copy.deepcopy(report)
    for finding in result["findings"]:
        for field in ("instruction","matched_fragment"):
            finding[field] = REDACT.sub(lambda m:m.group(1)+"[REDACTED]",finding.get(field,""))
        for field in ("context_before","context_after"):
            finding[field] = [REDACT.sub(lambda m:m.group(1)+"[REDACTED]",s) for s in finding.get(field,[])]
    return result

def render_sarif(report, rules):
    levels={"CRITICAL":"error","HIGH":"error","MEDIUM":"warning","LOW":"note","INFO":"note"}
    return {"version":"2.1.0","$schema":"https://json.schemastore.org/sarif-2.1.0.json",
      "runs":[{"tool":{"driver":{"name":"NEXA ScriptGuard","version":report["version"],
        "rules":[{"id":r["id"],"shortDescription":{"text":r["title"]}} for r in rules]}},
        "results":[{"ruleId":f["rule_id"],"level":levels[f["severity"]],
          "message":{"text":f["explanation"]},
          "locations":[{"physicalLocation":{"artifactLocation":{"uri":Path(report["file"]).as_uri()},
            "region":{"startLine":f["line"],"startColumn":f["column"]}}}],
          "properties":{"originalInstruction":f["instruction"],"confidence":f["confidence"]}}
          for f in report["findings"]]}]}

def render_html(report):
    esc=lambda x:html.escape(str(x),quote=True)
    cards=[]
    colors={"CRITICAL":"#ff3e51","HIGH":"#ff765c","MEDIUM":"#ffc36e","LOW":"#40d5ed","INFO":"#98a6c8"}
    for f in report["findings"]:
        checks="".join("<li><code>"+esc(c)+"</code></li>" for c in f["verification_commands"])
        cards.append(f"""<article class="finding" style="--sev:{colors.get(f['severity'],'#00d9ff')}">
          <h2>⚠ {esc(f['severity'])} · {esc(f['rule_id'])} · {esc(f['title'])}</h2>
          <p>LÍNEA {f['line']} · COLUMNA {f['column']} · CONFIANZA {esc(f['confidence'])}</p>
          <h3>INSTRUCCIÓN ORIGINAL</h3><pre>{esc(f['instruction'])}</pre>
          <h3>FRAGMENTO</h3><pre>{esc(f['matched_fragment'])}</pre>
          <h3>ANÁLISIS TÉCNICO</h3><p>{esc(f['explanation'])}</p>
          <h3>RECOMENDACIÓN</h3><p>{esc(f['recommendation'])}</p>
          <h3>VERIFICACIÓN — NO EJECUTADA</h3><ul>{checks}</ul></article>""")
    body="\n".join(cards) if cards else "<p>Sin coincidencias. Esto NO garantiza seguridad.</p>"
    return f"""<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>NEXA ScriptGuard</title><style>
    body{{background:radial-gradient(ellipse at top,#211039,#050912 65%);color:#f5f7ff;
    font:15px/1.6 system-ui,sans-serif;margin:0}}main{{max-width:1080px;margin:auto;padding:35px}}
    header{{border-bottom:1px solid #00d9ff;padding:24px 0}}h1{{font-size:42px;color:#00d9ff}}
    .finding{{border:1px solid var(--sev);box-shadow:0 0 14px var(--sev);border-radius:18px;
    padding:22px;margin:25px 0;background:#080e1b}}h2{{color:var(--sev)}}
    h3{{color:#00d9ff;font-size:13px;letter-spacing:.1em}}
    pre{{background:#020711;border:1px solid #00b9ef;padding:15px;white-space:pre-wrap;
    overflow-wrap:anywhere;border-radius:9px}}code{{color:#d9faff}}
    </style><main><header><h1>♾ NEXA ScriptGuard</h1>
    <p>NextGenAI Infinity · AI assists. Human verifies. Human decides.</p></header>
    <p>Archivo: {esc(report['file'])} · SHA-256: {esc(report['sha256'])}</p>
    <h2>{len(report['findings'])} hallazgo(s) heurístico(s)</h2>{body}
    <p>El script NO se ejecutó. Los hallazgos requieren revisión humana. Los reportes pueden contener secretos.</p>
    <footer>THERE IS NO FINAL VERSION. THERE IS ONLY EVOLUTION.</footer></main></html>"""

def render_terminal(report, console):
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    banner=Text("∞ NEXA SCRIPTGUARD",style="bold bright_cyan",justify="center")
    banner.append("\nNEXTGENAI INFINITY",style="bright_magenta")
    banner.append("\nAI assists. Human verifies. Human decides.",style="italic white")
    console.print(Panel(banner,border_style="bright_cyan",box=box.DOUBLE))
    console.print(f"[cyan]ARCHIVO[/] {report['file']}\n[cyan]SHA-256[/] {report['sha256']}\n[cyan]HALLAZGOS[/] {len(report['findings'])}")
    colors={"CRITICAL":"bright_red","HIGH":"red","MEDIUM":"yellow","LOW":"cyan","INFO":"white"}
    for f in report["findings"]:
        t=Text()
        t.append(f"{f['severity']} · {f['rule_id']} · {f['title']}\n",style="bold")
        t.append(f"LÍNEA {f['line']} · COLUMNA {f['column']}\n\n",style="bright_cyan")
        for label,value in [("INSTRUCCIÓN ORIGINAL",f["instruction"]),("FRAGMENTO",f["matched_fragment"]),
                            ("ANÁLISIS TÉCNICO",f["explanation"]),("RECOMENDACIÓN",f["recommendation"])]:
            t.append(label+"\n",style="bold bright_cyan")
            t.append(str(value)+"\n\n")
        t.append("VERIFICACIONES — NO EJECUTADAS\n",style="bright_cyan")
        for cmd in f["verification_commands"]:
            t.append("• "+cmd+"\n")
        console.print(Panel(t,border_style=colors.get(f["severity"],"cyan"),box=box.DOUBLE))
    if not report["findings"]:
        console.print("[yellow]Sin coincidencias; NO garantiza seguridad.[/]")

def main():
    p=argparse.ArgumentParser(description="Read-only static shell-script risk analyzer")
    p.add_argument("script",type=Path)
    for fmt in ("json","html","sarif"):
        p.add_argument("--"+fmt,dest=fmt+"_path",type=Path)
    p.add_argument("--view",choices=("neon","plain"),default="neon")
    p.add_argument("--redact",action="store_true")
    p.add_argument("--fail-on",choices=("critical","high","medium","low"))
    args=p.parse_args()
    target=args.script.expanduser().resolve()
    if not target.is_file():
        p.error("Input file does not exist")
    outputs=[x.expanduser().resolve() for x in (args.json_path,args.html_path,args.sarif_path) if x]
    if target in outputs or len(outputs)!=len(set(outputs)):
        p.error("Output paths must be distinct from each other and from input")
    try:
        rules=json.loads((Path(__file__).parent/"bash.json").read_text(encoding="utf-8"))
        report=inspect(target,rules)
    except (OSError,ValueError,re.error) as exc:
        p.error(str(exc))
    if args.redact:
        report=redact_report(report)
    if args.view=="neon":
        try:
            from rich.console import Console
            render_terminal(report,Console(highlight=False))
        except ImportError:
            args.view="plain"
    if args.view=="plain":
        print(f"NEXA ScriptGuard | {target.name} | {len(report['findings'])} finding(s)")
        for f in report["findings"]:
            print(f"[{f['severity']}] {f['rule_id']} L{f['line']}:C{f['column']} {f['instruction']}")
            print("  "+f["explanation"])
            print("  "+f["recommendation"])
    if args.json_path:
        args.json_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    if args.html_path:
        args.html_path.write_text(render_html(report),encoding="utf-8")
    if args.sarif_path:
        args.sarif_path.write_text(json.dumps(render_sarif(report,rules),ensure_ascii=False,indent=2),encoding="utf-8")
    if args.fail_on and any(SEVERITY[f["severity"]]>=SEVERITY[args.fail_on.upper()] for f in report["findings"]):
        return 2
    return 0

if __name__=="__main__":
    sys.exit(main())
