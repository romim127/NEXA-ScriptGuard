from dataclasses import dataclass


@dataclass(frozen=True)
class ScanLimits:
    max_input_bytes: int = 5 * 1024 * 1024
    max_findings: int = 2_000
    max_evidence_chars: int = 4_096
    max_total_evidence_chars: int = 8 * 1024 * 1024
    max_output_bytes: int = 20 * 1024 * 1024
    max_memory_bytes: int = 128 * 1024 * 1024
    timeout_seconds: float = 10.0
    max_ast_nodes: int = 250_000

    def __post_init__(self):
        for name, value in vars(self).items():
            if value <= 0:
                raise ValueError(f"{name} must be greater than zero")
