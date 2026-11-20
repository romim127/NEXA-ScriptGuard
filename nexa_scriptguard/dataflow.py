import re
import time

from .limits import ScanLimits
from .parser import BashDocument
from .rules import (
    _command_name,
    _commands,
    _is_sensitive,
    _make_finding,
    _normalized_name,
    _words,
)


_ASSIGNMENT = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)=(.*)$", re.S)
_REFERENCE = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z_0-9]*)\}|([A-Za-z_][A-Za-z_0-9]*))")
_UNCERTAIN_SCOPES = {
    "if_statement",
    "while_statement",
    "for_statement",
    "case_statement",
    "function_definition",
    "subshell",
}


def _ancestors(node):
    current = node.parent
    while current is not None:
        yield current
        current = current.parent


def _expand(value, assignments, position, max_chars, chain=(), depth=0):
    if depth >= 5:
        return value[:max_chars], list(chain), True, len(value) > max_chars
    uncertain = False
    truncated = False
    expanded_parts = []
    expanded_length = 0
    next_chain = tuple(chain)
    cursor = 0

    def append(value_part):
        nonlocal expanded_length, truncated
        available = max_chars - expanded_length
        if len(value_part) > available:
            truncated = True
        if available > 0:
            part = value_part[:available]
            expanded_parts.append(part)
            expanded_length += len(part)

    for match in _REFERENCE.finditer(value):
        append(value[cursor : match.start()])
        name = match.group(1) or match.group(2)
        candidates = [
            item for item in assignments.get(name, ())
            if (
                item["node"].location.start_line,
                item["node"].location.start_column,
            ) <= position
        ]
        if not candidates:
            append(match.group(0))
        elif name in chain:
            append(match.group(0))
            uncertain = True
        else:
            selected = max(
                candidates,
                key=lambda item: (
                    item["node"].location.start_line,
                    item["node"].location.start_column,
                ),
            )
            expanded, nested_chain, nested_uncertain, nested_truncated = _expand(
                selected["value"],
                assignments,
                position,
                max_chars,
                chain + (name,),
                depth + 1,
            )
            append(expanded)
            next_chain = tuple(dict.fromkeys(
                (*next_chain, *nested_chain, name)
            ))
            uncertain = uncertain or selected["uncertain"] or nested_uncertain
            truncated = truncated or nested_truncated
        cursor = match.end()
    append(value[cursor:])
    return "".join(expanded_parts), list(next_chain), uncertain, truncated


def _flow_record(variable, source, destination, chain, relation):
    return {
        "relationship": relation,
        "variable": variable,
        "source": {
            "kind": "variable_assignment",
            "location": source.location.to_dict(),
        },
        "destination": {
            "kind": "command",
            "location": destination.location.to_dict(),
        },
        "assignment_chain": list(chain),
    }


def analyze_dataflow(document: BashDocument, rules, source_lines, deadline, limits: ScanLimits):
    assignments = {}
    findings = []
    limitations = []
    nodes = list(document.walk())
    nodes.sort(key=lambda node: (
        node.location.start_line, node.location.start_column
    ))
    for node in nodes:
        if time.monotonic() > deadline:
            limitations.append("Analysis time limit reached during data-flow analysis.")
            return findings, limitations
        if node.kind != "variable_assignment":
            continue
        match = _ASSIGNMENT.match(node.text)
        if not match:
            continue
        name, value = match.groups()
        assignments.setdefault(name, []).append({
            "node": node,
            "value": value,
            "uncertain": any(parent.kind in _UNCERTAIN_SCOPES for parent in _ancestors(node)),
        })

    for node in nodes:
        if time.monotonic() > deadline:
            limitations.append("Analysis time limit reached during data-flow analysis.")
            break
        if node.kind == "pipeline":
            commands = _commands(node)
            command_names = [
                _normalized_name(_command_name(command), _words(command))
                for command in commands
            ]
            sinks = [
                command for command, name in zip(commands, command_names)
                if name in {"bash", "sh", "zsh"}
            ]
            references = {
                match.group(1) or match.group(2)
                for match in _REFERENCE.finditer(node.text)
            }
            if sinks:
                for variable in sorted(references):
                    candidates = [
                        item for item in assignments.get(variable, ())
                        if (
                            item["node"].location.start_line,
                            item["node"].location.start_column,
                        ) <= (
                            node.location.start_line,
                            node.location.start_column,
                        )
                    ]
                    if not candidates:
                        continue
                    source = max(
                        candidates,
                        key=lambda item: (
                            item["node"].location.start_line,
                            item["node"].location.start_column,
                        ),
                    )
                    expanded, chain, uncertain, truncated = _expand(
                        f"${variable}",
                        assignments,
                        (node.location.start_line, node.location.start_column),
                        limits.max_total_evidence_chars,
                    )
                    if truncated:
                        limitations.append(
                            "Data-flow expansion character limit reached "
                            f"({limits.max_total_evidence_chars})."
                        )
                    if re.search(r"\b(?:curl|wget)\b", expanded):
                        rule = rules.get("SG-FLOW-001")
                        if rule:
                            relation = "indeterminate" if uncertain else "possible"
                            findings.append(_make_finding(
                                rule,
                                node,
                                source_lines,
                                "A prior assignment may contain network command text in a pipeline; shell word-splitting and runtime values are not proven.",
                                [_flow_record(variable, source["node"], sinks[0], chain, relation)],
                                limits,
                            ))
                            break
            if len(findings) >= limits.max_findings:
                limitations.append(f"Finding limit reached ({limits.max_findings}).")
                break
            continue
        if node.kind != "command":
            continue
        words = _words(node)
        name = _normalized_name(_command_name(node), words)
        references = {
            match.group(1) or match.group(2)
            for match in _REFERENCE.finditer(node.text)
        }
        for variable in sorted(references):
            candidates = [
                item for item in assignments.get(variable, ())
                if (
                    item["node"].location.start_line,
                    item["node"].location.start_column,
                ) <= (
                    node.location.start_line,
                    node.location.start_column,
                )
            ]
            if not candidates:
                continue
            source = max(
                candidates,
                key=lambda item: (
                    item["node"].location.start_line,
                    item["node"].location.start_column,
                ),
            )
            expanded, chain, uncertain, truncated = _expand(
                f"${variable}",
                assignments,
                (node.location.start_line, node.location.start_column),
                limits.max_total_evidence_chars,
            )
            if truncated:
                limitations.append(
                    "Data-flow expansion character limit reached "
                    f"({limits.max_total_evidence_chars})."
                )
            relation = "indeterminate" if uncertain else "possible"
            remote_source = bool(re.search(r"\b(?:curl|wget)\b", expanded))
            if (
                remote_source
                and name in {"bash", "sh", "zsh"}
                and (("-c" in words) or "$" in node.text)
            ):
                rule = rules.get("SG-FLOW-001")
                if rule:
                    findings.append(_make_finding(
                        rule,
                        node,
                        source_lines,
                        "A prior assignment may contain network-derived command text; branch, quoting, and expansion semantics are not proven.",
                        [_flow_record(variable, source["node"], node, chain, relation)],
                        limits,
                    ))
                    break
            sensitive_source = _is_sensitive(expanded)
            upload_command = (
                name in {"curl", "wget"}
                and any(
                    arg in {"--data-binary", "--upload-file", "--data"}
                    or arg.startswith(("--data-binary=", "--upload-file=", "--data="))
                    for arg in words[1:]
                )
            )
            if sensitive_source and upload_command:
                rule = rules.get("SG-FLOW-002")
                if rule:
                    findings.append(_make_finding(
                        rule,
                        node,
                        source_lines,
                        "A prior assignment may name a sensitive path used by a network upload option; file resolution and transfer are not proven.",
                        [_flow_record(variable, source["node"], node, chain, relation)],
                        limits,
                    ))
                    break
        if len(findings) >= limits.max_findings:
            limitations.append(f"Finding limit reached ({limits.max_findings}).")
            break
    return findings, limitations
