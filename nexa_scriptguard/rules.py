import json
import re
import shlex
import time
from dataclasses import dataclass
from pathlib import Path

from .limits import ScanLimits
from .model import Finding
from .parser import BashDocument, SyntaxNode


SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
RULES_PATH = Path(__file__).with_name("bash.json")


@dataclass(frozen=True)
class Rule:
    id: str
    severity: str
    title: str
    explanation: str
    recommendation: str
    checks: tuple[str, ...]
    matcher: str


def load_rules():
    raw = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    rules = [Rule(
        id=item["id"],
        severity=item["severity"],
        title=item["title"],
        explanation=item["why"],
        recommendation=item["recommendation"],
        checks=tuple(item["checks"]),
        matcher=item["matcher"],
    ) for item in raw]
    ids = [rule.id for rule in rules]
    if len(ids) != len(set(ids)):
        raise ValueError("Rule identifiers must be unique")
    return {rule.id: rule for rule in rules}


def _words(node: SyntaxNode):
    try:
        return shlex.split(node.text, comments=False, posix=True)
    except ValueError:
        return []


def _commands(node: SyntaxNode):
    found = []
    stack = list(reversed(node.children))
    while stack:
        current = stack.pop()
        if current.kind == "command":
            found.append(current)
            continue
        if current.kind in {"pipeline", "command_substitution", "process_substitution"}:
            continue
        stack.extend(reversed(current.children))
    return found


def _command_name(command: SyntaxNode):
    name = next(
        (node for node in command.children if node.kind == "command_name"), None
    )
    if name is None:
        return ""
    words = _words(name)
    return words[0] if words else name.text.strip("\"'")


def _normalized_name(name, words):
    if name in {"env", "sudo", "command", "exec", "builtin"}:
        skip_value = False
        for token in words[1:]:
            if skip_value:
                skip_value = False
                continue
            if token in {"-u", "--user", "-g", "--group", "-h", "--host"}:
                skip_value = True
                continue
            if token == "--":
                continue
            if token.startswith("-") or (
                name == "env" and re.match(r"[A-Za-z_][A-Za-z_0-9]*=", token)
            ):
                continue
            return token
    return name


def _is_sensitive(value: str):
    return bool(re.search(
        r"(?i)(?:/etc/(?:shadow|sudoers|passwd|ssh/)|"
        r"(?:^|[/~])\.ssh/id_(?:rsa|ed25519|ecdsa)\b|"
        r"(?:^|[/~])\.aws/credentials\b|(?:^|[/~])\.env\b)",
        value,
    ))


def _bounded_evidence(value, limit):
    if len(value) <= limit:
        return value, False
    marker = "[TRUNCATED]"
    if len(marker) > limit:
        marker = marker[:limit]
    return value[: max(0, limit - len(marker))] + marker, True


def _make_finding(rule, node, source_lines, detail, correlation=None, limits=None):
    limits = limits or ScanLimits()
    line = node.location.start_line
    instruction, truncated = _bounded_evidence(node.text, limits.max_evidence_chars)
    before_pairs = [
        _bounded_evidence(item, limits.max_evidence_chars)
        for item in source_lines[max(0, line - 3) : line - 1]
    ]
    after_pairs = [
        _bounded_evidence(item, limits.max_evidence_chars)
        for item in source_lines[line : min(len(source_lines), line + 2)]
    ]
    truncated = truncated or any(item[1] for item in before_pairs + after_pairs)
    before = [item[0] for item in before_pairs]
    after = [item[0] for item in after_pairs]
    name_node = next((child for child in node.children if child.kind == "command_name"), None)
    impact_target = None
    if name_node and rule.id in {"SG-004", "SG-005", "SG-006", "SG-FLOW-001", "SG-FLOW-002"}:
        words = _words(node)
        name = _command_name(node)
        if name and name == _normalized_name(name, words):
            impact_target = name_node.location
    return Finding(
        rule_id=rule.id,
        title=rule.title,
        severity=rule.severity,
        location=node.location,
        instruction=instruction,
        explanation=rule.explanation,
        recommendation=rule.recommendation,
        verification_commands=list(rule.checks),
        confidence="medium",
        confidence_reason=detail,
        context_before=before,
        context_after=after,
        correlation=correlation or [],
        evidence_truncated=truncated,
        impact_target=impact_target,
    )


def _match_command(rule, command, words, name):
    normalized = _normalized_name(name, words)
    raw = command.text
    try:
        command_index = words.index(name)
    except ValueError:
        command_index = 0
    if name in {"env", "sudo", "command", "exec", "builtin"}:
        effective = normalized
        try:
            command_index = words.index(effective)
        except ValueError:
            command_index = min(command_index + 1, len(words))
    args = words[command_index + 1 :]
    if rule.matcher == "remote_pipeline":
        return False
    if rule.matcher == "sensitive_upload":
        upload = any(
            arg in {"--data-binary", "--upload-file", "--data"}
            or arg.startswith(("--data-binary=", "--upload-file=", "--data="))
            for arg in args
        )
        return normalized in {"curl", "wget"} and upload and _is_sensitive(raw)
    if rule.matcher == "chmod_world_writable":
        return normalized == "chmod" and any(
            arg == "777" or arg == "0777" or re.fullmatch(r"[ugo]*\+rwx", arg)
            for arg in args
        )
    if rule.matcher == "recursive_force_delete":
        return normalized == "rm" and any(
            arg in {"-rf", "-fr", "--recursive", "--force"}
            or (arg.startswith("-") and "r" in arg[1:] and "f" in arg[1:])
            for arg in args
        )
    if rule.matcher == "dynamic_eval":
        return normalized == "eval"
    if rule.matcher == "dynamic_shell":
        return normalized in {"bash", "sh", "zsh"} and "-c" in args and (
            "$" in raw or "`" in raw
        )
    if rule.matcher == "control_disable":
        joined = " ".join(words)
        return (
            (normalized == "setenforce" and "0" in args)
            or (normalized in {"ufw", "firewall-cmd"} and "disable" in args)
            or (normalized == "iptables" and "-F" in args)
            or (
                normalized == "systemctl"
                and "stop" in args
                and any(x in joined.lower() for x in ("apparmor", "firewalld", "ufw"))
            )
        )
    if rule.matcher == "persistence":
        return (
            normalized == "crontab"
            and ("-e" in args or "@reboot" in raw)
        ) or (normalized == "systemctl" and "enable" in args)
    if rule.matcher == "sensitive_config":
        return normalized in {"sed", "tee", "cp", "mv", "printf"} and bool(
            re.search(r"/etc/(?:ssh/sshd_config|sudoers|passwd|pam\.d/)", raw)
        )
    if rule.matcher == "setuid":
        return normalized == "chmod" and any(
            arg in {"4755", "u+s"} or "+s" in arg for arg in args
        )
    if rule.matcher == "credential_literal":
        return bool(
            re.search(
                r"(?i)\b(?:password|passwd|api[_-]?key|secret|token)\s*=\s*['\"]?[^$'\"\s]{8,}",
                raw,
            )
        )
    if rule.matcher == "unsafe_redirect":
        return normalized in {"dd", "tee", "cp", "mv"} and bool(
            re.search(r"(?:^|\s)(?:/dev/sd[a-z]|/etc/(?:passwd|shadow|sudoers))\b", raw)
        )
    return False


def analyze_rules(document: BashDocument, rules, source_lines, deadline, limits: ScanLimits):
    findings = []
    limitations = []
    pipeline_rule = rules.get("SG-001")
    for node in document.walk():
        if time.monotonic() >= deadline:
            limitations.append("Analysis time limit reached during rule matching.")
            break
        if node.kind == "pipeline" and pipeline_rule:
            commands = _commands(node)
            names = [
                _normalized_name(_command_name(command), _words(command))
                for command in commands
            ]
            if any(name in {"curl", "wget"} for name in names) and any(
                name in {"bash", "sh", "zsh"} for name in names
            ):
                network = next(
                    command for command, name in zip(commands, names)
                    if name in {"curl", "wget"}
                )
                shell = next(
                    command for command, name in zip(commands, names)
                    if name in {"bash", "sh", "zsh"}
                )
                findings.append(_make_finding(
                    pipeline_rule,
                    node,
                    source_lines,
                    "Parser identified a download command and shell interpreter in one pipeline; execution is not proven.",
                    [{
                        "relationship": "possible",
                        "structural_relation": "demonstrable",
                        "source": {
                            "kind": "network command",
                            "location": network.location.to_dict(),
                        },
                        "sink": {
                            "kind": "shell interpreter",
                            "location": shell.location.to_dict(),
                        },
                        "reason": "Both syntax nodes occur in the same parsed pipeline; data delivery and execution are not proven.",
                    }],
                    limits,
                ))
        if node.kind != "command":
            continue
        words = _words(node)
        name = _command_name(node)
        for rule in rules.values():
            if rule.matcher == "remote_pipeline":
                continue
            if _match_command(rule, node, words, name):
                findings.append(_make_finding(
                    rule,
                    node,
                    source_lines,
                    "AST command-name match and argument pattern; inspect operands and runtime context.",
                    limits=limits,
                ))
        if len(findings) >= limits.max_findings:
            limitations.append(f"Finding limit reached ({limits.max_findings}).")
            break
    return findings, limitations
