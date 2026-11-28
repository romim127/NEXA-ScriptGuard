import copy
import re
import unicodedata
from pathlib import PurePath


_REDACTIONS = (
    (re.compile(r"(?i)(\bauthorization\s*:\s*bearer\s+)[^\s,;]+"), r"\1[REDACTED]"),
    (re.compile(r"""(?i)(\b(?:[a-z][a-z0-9_]*_)?(?:password|passwd|api[_-]?key|secret|token)(?:_[a-z0-9_]+)?["']?(?:\s*:\s*[a-z_][a-z0-9_.]*)?\s*[=:]\s*)(["'])(?:\\.|(?!\2)[^\\\r\n])*\2"""), r"\1\2[REDACTED]\2"),
    (re.compile(r"(?i)(\b(?:[a-z][a-z0-9_]*_)?(?:password|passwd|api[_-]?key|secret|token)(?:_[a-z0-9_]+)?[\"']?(?:\s*:\s*[a-z_][a-z0-9_.]*)?\s*[=:]\s*[\"']?)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(https?://)[^/\s:@]+:[^/\s@]+@"), r"\1[REDACTED]@"),
    (re.compile(r"(?i)(-----BEGIN [^-]*PRIVATE KEY-----).*?(-----END [^-]*PRIVATE KEY-----)", re.S), r"\1[REDACTED]\2"),
    (re.compile(r"(?i)(?:[A-Z]:\\Users\\)[^\\\s]+"), r"[REDACTED_USER_PATH]"),
    (re.compile(r"(?i)(?:/(?:home|Users)/)[^/\s]+"), r"[REDACTED_USER_PATH]"),
    (re.compile(r"(?i)(?:/root|~)/\.ssh/(?:id_[A-Za-z0-9_-]+|known_hosts)"), r"[REDACTED_SENSITIVE_PATH]"),
    (re.compile(r"(?i)(?:/root|~)/\.aws/credentials"), r"[REDACTED_SENSITIVE_PATH]"),
    (re.compile(r"(?i)(?:/root|~)/\.env\b"), r"[REDACTED_SENSITIVE_PATH]"),
    (re.compile(r"(?i)[/\\]\.ssh[/\\](?:id_[A-Za-z0-9_-]+|known_hosts)"), r"[REDACTED_SENSITIVE_PATH]"),
    (re.compile(r"(?i)[/\\]\.aws[/\\]credentials"), r"[REDACTED_SENSITIVE_PATH]"),
    (re.compile(r"(?i)[/\\]\.env\b"), r"[REDACTED_SENSITIVE_PATH]"),
)


def sanitize_text(value: str, redact_secrets=True):
    sanitized = []
    for character in value:
        category = unicodedata.category(character)
        if character in "\n\t" or category not in {"Cc", "Cf"}:
            sanitized.append(character)
        else:
            sanitized.append(f"\\u{ord(character):04x}")
    value = "".join(sanitized)
    if not redact_secrets:
        return value
    for pattern, replacement in _REDACTIONS:
        value = pattern.sub(replacement, value)
    return value


def prepare_report(report, redact_secrets=True):
    result = copy.deepcopy(report)

    def visit(value):
        if isinstance(value, dict):
            return {key: visit(item) for key, item in value.items()}
        if isinstance(value, list):
            return [visit(item) for item in value]
        if isinstance(value, str):
            return sanitize_text(value, redact_secrets)
        return value

    result = visit(result)
    for original, finding in zip(report.get("findings", []), result.get("findings", [])):
        evidence = finding.get("evidence")
        impact = finding.get("impact_analysis")
        if impact and (finding["instruction"] != original["instruction"]
                       or evidence.get("original") != original["evidence"].get("original")):
            for reference in impact["references"]:
                if reference["range"] is not None:
                    reference["range"] = None
                    reference["limitation"] = "La preparación del reporte cambió la evidencia visible."
        if isinstance(evidence, dict) and isinstance(evidence.get("original"), str):
            evidence["shared"] = evidence["original"]
            evidence["original_available_in_this_report"] = not redact_secrets
            if redact_secrets:
                evidence.pop("original", None)
        if redact_secrets and isinstance(finding.get("file"), str):
            finding["file"] = result.get("file", finding["file"])
    file_path = result.get("file")
    if redact_secrets and isinstance(file_path, str) and (
        file_path.startswith("/")
        or file_path.startswith("[REDACTED_USER_PATH]")
        or re.match(r"(?i)^[A-Z]:\\", file_path)
    ):
        result["file"] = PurePath(file_path.replace("\\", "/")).name
        for finding in result.get("findings", []):
            finding["file"] = result["file"]
    result["redaction_applied"] = redact_secrets
    return result


def redact_report(report):
    return prepare_report(report, redact_secrets=True)
