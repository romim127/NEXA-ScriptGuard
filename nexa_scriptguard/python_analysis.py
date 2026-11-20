"""Conservative AST-based Python analysis; input is parsed, never imported."""

import ast
import datetime as dt
import io
import json
import re
import time
import tokenize
from pathlib import Path

from .classification import classify_findings
from .model import AnalysisReport, Finding, Location
from .rules import _bounded_evidence


PYTHON_RULES_PATH = Path(__file__).with_name("python_rules.json")
SECRET_NAME = re.compile(r"(?:^|_)(?:password|passwd|secret|token|api_?key)(?:$|_)", re.I)
NETWORK = {"requests.get", "requests.post", "urllib.request.urlopen", "httpx.get", "httpx.post"}
SHELL_CALLS = {"os.system", "os.popen", "subprocess.getoutput", "subprocess.getstatusoutput"}
SUBPROCESS = {"subprocess.run", "subprocess.call", "subprocess.Popen", "subprocess.check_call", "subprocess.check_output"}
HTTP_CALLS = {"requests.get", "requests.post", "requests.put", "requests.delete", "requests.request",
              "httpx.get", "httpx.post", "httpx.put", "httpx.delete", "httpx.request"}


def python_rules():
    rules = json.loads(PYTHON_RULES_PATH.read_text(encoding="utf-8"))
    if len({rule["id"] for rule in rules}) != len(rules):
        raise ValueError("Duplicate Python rule identifiers")
    return rules


def _column(lines, line, byte_column):
    return len(lines[line - 1].encode("utf-8")[:byte_column].decode("utf-8")) + 1


def _location(node, lines):
    return Location(node.lineno, _column(lines, node.lineno, node.col_offset),
                    node.end_lineno, _column(lines, node.end_lineno, node.end_col_offset))


def _bounded_segment(node, lines, limit):
    parts = []
    length = 0
    for line_number in range(node.lineno, node.end_lineno + 1):
        line = lines[line_number - 1]
        start = _column(lines, line_number, node.col_offset) - 1 if line_number == node.lineno else 0
        end = _column(lines, line_number, node.end_col_offset) - 1 if line_number == node.end_lineno else len(line)
        remaining = limit + 1 - length
        part = line[start:min(end, start + remaining)]
        parts.append(part)
        length += len(part)
        if length > limit:
            break
    return _bounded_evidence("".join(parts), limit)


class Inspector:
    def __init__(self, lines, limits, deadline):
        self.lines = lines
        self.limits = limits
        self.deadline = deadline
        self.rules = {rule["id"]: rule for rule in python_rules()}
        self.findings = []
        self.reasons = []
        self.remaining_evidence = limits.max_total_evidence_chars

    def add(self, rule_id, node, correlations=None):
        if len(self.findings) >= self.limits.max_findings:
            if "Finding limit reached." not in self.reasons:
                self.reasons.append("Finding limit reached.")
            return
        rule = self.rules[rule_id]
        instruction, truncated = _bounded_segment(
            node, self.lines, min(self.limits.max_evidence_chars, self.remaining_evidence)
        )
        self.remaining_evidence -= len(instruction)
        self.findings.append(Finding(
            rule_id=rule_id, title=rule["title"], severity=rule["severity"],
            location=_location(node, self.lines), instruction=instruction,
            explanation=rule["why"], recommendation=rule["recommendation"],
            verification_commands=rule["checks"], confidence="medium",
            confidence_reason="Coincidencia AST estática; la ejecución y el contexto requieren revisión.",
            correlation=correlations or [],
            evidence_truncated=truncated,
        ))

    def inspect(self, tree):
        # A conflicting binding anywhere makes resolution ambiguous rather than guessing.
        def collect(scope):
            bindings = {}
            conflicts = set()
            wildcard = False
            stack = list(ast.iter_child_nodes(scope))
            if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                args = scope.args
                for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs]:
                    conflicts.add(arg.arg)
                for arg in (args.vararg, args.kwarg):
                    if arg:
                        conflicts.add(arg.arg)
            while stack:
                if time.monotonic() >= self.deadline:
                    self.reasons.append("Analysis deadline reached.")
                    return bindings, wildcard
                node = stack.pop()
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    conflicts.add(node.name)
                    continue
                if isinstance(node, ast.Lambda):
                    continue
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname or alias.name.split(".")[0]
                        value = alias.name if alias.asname else name
                        if name in bindings and bindings[name] != value:
                            conflicts.add(name)
                        bindings[name] = value
                elif isinstance(node, ast.ImportFrom):
                    if node.level or node.module is None:
                        for alias in node.names:
                            conflicts.add(alias.asname or alias.name)
                    else:
                        for alias in node.names:
                            if alias.name == "*":
                                wildcard = True
                            else:
                                name = alias.asname or alias.name
                                value = node.module + "." + alias.name
                                if name in bindings and bindings[name] != value:
                                    conflicts.add(name)
                                bindings[name] = value
                elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                    conflicts.add(node.id)
                stack.extend(ast.iter_child_nodes(node))
            for name in conflicts:
                bindings[name] = None
            return bindings, wildcard

        def resolve(node, environments):
            if isinstance(node, ast.Name):
                for bindings, wildcard in reversed(environments):
                    if node.id in bindings:
                        return bindings[node.id]
                    if wildcard:
                        return None
                return node.id if node.id in {"eval", "exec"} else None
            if isinstance(node, ast.Attribute):
                base = resolve(node.value, environments)
                return base + "." + node.attr if base else None
            return None

        def network(node, environments):
            if isinstance(node, ast.Call):
                if resolve(node.func, environments) in NETWORK:
                    return node
                if isinstance(node.func, ast.Attribute) and node.func.attr in {"read", "text", "content", "json"}:
                    return network(node.func.value, environments)
            if isinstance(node, ast.Attribute) and node.attr in {"text", "content"}:
                return network(node.value, environments)
            return None

        def visit_scope(scope, outer):
            if time.monotonic() >= self.deadline:
                self.reasons.append("Analysis deadline reached.")
                return
            env = outer + [collect(scope)]
            if self.reasons:
                return
            network_vars = {}

            def walk(node):
                if time.monotonic() >= self.deadline:
                    if "Analysis deadline reached." not in self.reasons:
                        self.reasons.append("Analysis deadline reached.")
                    return
                if node is not scope and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                    visit_scope(node, env)
                    return
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    value = node.value
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for target in targets:
                        if isinstance(target, ast.Name):
                            network_vars.pop(target.id, None)
                            source = network(value, env) if value else None
                            if source:
                                network_vars[target.id] = source
                            if (value and isinstance(value, ast.Constant)
                                    and isinstance(value.value, str) and value.value
                                    and SECRET_NAME.search(target.id)):
                                self.add("PY-005", node)
                if isinstance(node, ast.Call):
                    name = resolve(node.func, env)
                    if name in {"eval", "exec", "builtins.eval", "builtins.exec"}:
                        self.add("PY-001", node)
                        if node.args:
                            origin = network(node.args[0], env)
                            if isinstance(node.args[0], ast.Name):
                                origin = network_vars.get(node.args[0].id)
                            if origin:
                                self.add("PY-004", node, [{
                                    "relationship": "possible",
                                    "source": {"kind": "network call", "location": _location(origin, self.lines).to_dict()},
                                    "sink": {"kind": "dynamic evaluation", "location": _location(node, self.lines).to_dict()},
                                    "reason": "Syntactic relation only; control flow and runtime values are not proven.",
                                }])
                    if name in SUBPROCESS and any(k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True for k in node.keywords):
                        self.add("PY-002", node)
                    if name in {"pickle.load", "pickle.loads", "_pickle.load", "_pickle.loads"}:
                        self.add("PY-003", node)
                    if name in SHELL_CALLS:
                        self.add("PY-006", node)
                    if (isinstance(node.func, ast.Attribute) and node.func.attr in {"execute", "executemany"}
                            and node.args and isinstance(node.args[0], (ast.JoinedStr, ast.BinOp, ast.Call))):
                        query = node.args[0]
                        if (isinstance(query, ast.JoinedStr)
                                or isinstance(query, ast.BinOp) and isinstance(query.op, (ast.Add, ast.Mod))
                                or isinstance(query, ast.Call) and isinstance(query.func, ast.Attribute) and query.func.attr == "format"):
                            self.add("PY-007", node)
                    if name in HTTP_CALLS and any(k.arg == "verify" and isinstance(k.value, ast.Constant) and k.value.value is False for k in node.keywords):
                        self.add("PY-008", node)
                for child in ast.iter_child_nodes(node):
                    walk(child)

            walk(scope)

        visit_scope(tree, [])


def analyze_python(source, digest, limits, deadline):
    reasons = []
    limitations = [
        "Python AST parsing uses the running Python version; newer syntax may not be supported.",
        "Name resolution and network correlation are conservative approximations, not control-flow or execution proof.",
        "Parsing is not preemptible and memory use is estimated, not a hard quota.",
    ]
    text = ""
    findings = []
    try:
        encoding, _ = tokenize.detect_encoding(io.BytesIO(source.data).readline)
        text = source.data.decode(encoding)
        tree = ast.parse(text, filename="<input>")
        count = 0
        for _ in ast.walk(tree):
            count += 1
            if time.monotonic() >= deadline:
                reasons.append("Analysis deadline reached during AST traversal.")
                break
            if count > limits.max_ast_nodes or len(source.data) + count * 256 > limits.max_memory_bytes:
                reasons.append("Python AST node or estimated memory budget reached.")
                break
        if not reasons:
            inspector = Inspector(text.splitlines(keepends=True), limits, deadline)
            inspector.inspect(tree)
            findings = inspector.findings
            reasons.extend(inspector.reasons)
    except (SyntaxError, UnicodeError, LookupError, ValueError, RecursionError, MemoryError) as exc:
        reasons.append(f"Python parsing could not complete ({type(exc).__name__}).")
    findings, classification_reasons = classify_findings(findings, str(source.path), digest, limits)
    reasons.extend(classification_reasons)
    reasons = list(dict.fromkeys(reasons))
    report = AnalysisReport(
        file_path=str(source.path), sha256=digest, line_count=len(text.splitlines()),
        findings=findings, limitations=limitations, complete=not reasons,
        incomplete_reasons=reasons, parser="python-ast",
        analyzed_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
    )
    if time.monotonic() >= deadline:
        report.complete = False
        if "Analysis deadline reached." not in report.incomplete_reasons:
            report.incomplete_reasons.append("Analysis deadline reached.")
    return report
