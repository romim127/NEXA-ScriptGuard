from dataclasses import asdict, dataclass, field
from typing import Any
from .impact import ImpactAnalysis


SCHEMA_VERSION = "1.0"
RULE_VERSION = "1.0.0"


@dataclass(frozen=True)
class Location:
    start_line: int
    start_column: int
    end_line: int
    end_column: int

    def to_dict(self):
        return {
            "start": {"line": self.start_line, "column": self.start_column},
            "end": {"line": self.end_line, "column": self.end_column},
        }


@dataclass
class Finding:
    rule_id: str
    title: str
    severity: str
    location: Location
    instruction: str
    explanation: str
    recommendation: str
    verification_commands: list[str]
    confidence: str = "medium"
    confidence_reason: str = "Heurística estructural; requiere revisión humana."
    status: str = "requires_review"
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)
    correlation: list[dict[str, Any]] = field(default_factory=list)
    engine: str = "python"
    finding_id: str = ""
    evidence_truncated: bool = False
    impact_analysis: ImpactAnalysis | None = None
    impact_target: Location | None = None

    def to_dict(self, file_path: str, sha256: str, limitations: list[str]):
        return {
            "id": self.finding_id,
            "rule": {"id": self.rule_id, "version": RULE_VERSION},
            "rule_id": self.rule_id,
            "title": self.title,
            "file": file_path,
            "sha256": sha256,
            "location": self.location.to_dict(),
            "line": self.location.start_line,
            "column": self.location.start_column,
            "end_line": self.location.end_line,
            "end_column": self.location.end_column,
            "instruction": self.instruction,
            "context": {
                "before": self.context_before,
                "after": self.context_after,
            },
            "context_before": self.context_before,
            "context_after": self.context_after,
            "severity": self.severity,
            "confidence": self.confidence,
            "confidence_reason": self.confidence_reason,
            "status": self.status,
            "evidence": {
                "original": self.instruction,
                "truncated": self.evidence_truncated,
                "correlation": self.correlation,
            },
            "explanation": self.explanation,
            "recommendation": self.recommendation,
            "verification_commands": self.verification_commands,
            "limitations": limitations,
            "engine": self.engine,
            **({"impact_analysis": asdict(self.impact_analysis)} if self.impact_analysis else {}),
        }


@dataclass
class AnalysisReport:
    file_path: str
    sha256: str
    line_count: int
    findings: list[Finding]
    limitations: list[str]
    complete: bool
    incomplete_reasons: list[str]
    parser: str
    analyzed_at_utc: str
    schema_version: str = SCHEMA_VERSION
    redaction_applied: bool = False

    def to_dict(self):
        return {
            "schema_version": self.schema_version,
            "tool": "NEXA ScriptGuard",
            "version": "0.5.0-alpha.1",
            "analyzed_at_utc": self.analyzed_at_utc,
            "file": self.file_path,
            "sha256": self.sha256,
            "lines": self.line_count,
            "complete": self.complete,
            "analysis_status": "complete" if self.complete else "incomplete",
            "incomplete_reasons": list(self.incomplete_reasons),
            "parser": self.parser,
            "redaction_applied": self.redaction_applied,
            "limitations": list(self.limitations),
            "findings": [
                finding.to_dict(
                    self.file_path, self.sha256, self.limitations
                )
                for finding in self.findings
            ],
        }
