"""Describe possible effects using existing findings, without inspecting runtime state."""

import time
from dataclasses import dataclass, field
from typing import Literal, TypedDict


Status = Literal["potential", "conditional", "indeterminate", "not_established", "not_evaluated"]
DIMENSIONS = ("confidentiality", "integrity", "availability")
RESOURCES = dict(zip((f"SYS-{i:02d}" for i in range(1, 16)), (
    "Sistema de archivos", "Procesos y subprocesos", "Registro de Windows",
    "Servicios del sistema", "Variables de entorno", "Credenciales y secretos",
    "Comunicaciones de red", "Usuarios, permisos y privilegios", "Configuración del SO",
    "Persistencia", "Controles de seguridad", "Bases de datos",
    "Memoria y ejecución dinámica", "Registros de auditoría", "Cadena de suministro",
)))
BOUNDARIES = dict(zip((f"TB-{i:02d}" for i in range(1, 11)), (
    ("Entrada externa", "Aplicación"), ("Datos", "Intérprete de código"),
    ("Aplicación", "Sistema operativo"), ("Usuario", "Contexto privilegiado"),
    ("Entorno local", "Red externa"), ("Aplicación", "Almacenamiento sensible"),
    ("Proceso", "Otro proceso"), ("Aplicación", "Servicio externo"),
    ("Dependencia externa", "Entorno local"), ("Aplicación", "Controles de seguridad"),
)))


class Point(TypedDict):
    line: int
    column: int


class LocationData(TypedDict):
    start: Point
    end: Point


@dataclass
class Reference:
    id: str
    role: Literal["instruction", "source", "sink", "propagation", "validation"]
    location: LocationData
    range: dict[str, int] | None = None
    limitation: str = "La ubicación no tiene un rango verificable en la evidencia visible."


@dataclass
class Conclusion:
    status: Status
    justification: str
    conditions: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)


@dataclass
class Resource(Conclusion):
    id: str = ""
    label: str = ""
    operation: str = ""
    scope: Literal["direct", "correlated"] = "direct"


@dataclass
class Boundary(Conclusion):
    id: str = ""
    origin: str = ""
    destination: str = ""


@dataclass
class Flow:
    source: str
    sink: str
    relationship: Literal["possible", "indeterminate"]
    assignment_steps: int


@dataclass
class ImpactAnalysis:
    coverage: Literal["syntax", "correlated", "partial", "not_evaluated"]
    confidence: Literal["low", "medium"]
    cia: dict[str, Conclusion]
    limitations: list[str]
    provenance: str
    version: str = "1.0"
    resources: list[Resource] = field(default_factory=list)
    boundaries: list[Boundary] = field(default_factory=list)
    flows: list[Flow] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)


@dataclass(frozen=True)
class Signal:
    resource: str
    operation: str
    justification: str
    condition: str
    dimensions: tuple[str, ...] = ()
    boundary: str = ""
    status: Status = "conditional"


# Map only what the matcher establishes. A path somewhere in a command does
# not establish how the command uses it. An execute() attribute is not a DB type.
SIGNALS = {
    "SG-001": Signal("SYS-13", "ejecución", "Una tubería conecta una descarga con un intérprete.",
                     "La tubería debe ejecutarse y entregar datos interpretables.", boundary="TB-02"),
    "SG-002": Signal("SYS-07", "transferencia", "Hay una opción de carga y una referencia sensible.",
                     "La opción debe consumir datos y alcanzar el destino.", ("confidentiality",)),
    "SG-003": Signal("SYS-08", "modificación", "El comando chmod solicita permisos amplios.",
                     "El comando debe alcanzar un objetivo y tener permiso de modificación.", ("integrity",)),
    "SG-004": Signal("SYS-01", "eliminación", "El comando rm incluye una opción recursiva o forzada.",
                     "Debe ejecutarse sobre una ruta existente con permisos suficientes.", ("integrity", "availability")),
    "SG-005": Signal("SYS-13", "ejecución", "La instrucción usa eval.",
                     "El intérprete debe alcanzar la llamada y recibir código.", boundary="TB-02"),
    "SG-006": Signal("SYS-13", "ejecución", "Un shell recibe una expresión expandida.",
                     "La expansión debe aportar texto interpretable.", boundary="TB-02"),
    "SG-007": Signal("SYS-11", "desactivación", "El comando solicita detener o degradar un control.",
                     "El control debe existir y el comando contar con permisos.", ("integrity",), "TB-10"),
    "SG-008": Signal("SYS-10", "modificación", "La instrucción usa crontab o habilita un servicio.",
                     "La configuración debe modificarse y activarse.", ("integrity",)),
    "SG-009": Signal("SYS-09", "acceso", "Una herramienta menciona una ruta de configuración sensible.",
                     "El papel de la ruta debe verificarse.", status="indeterminate"),
    "SG-010": Signal("SYS-08", "modificación", "El comando chmod solicita un modo con indicador set-ID.",
                     "El objetivo, el modo resultante y los permisos deben verificarse.", ("integrity",)),
    "SG-011": Signal("SYS-06", "presencia", "La instrucción contiene un candidato a credencial literal.",
                     "El valor tendría que ser un secreto válido.", ("confidentiality",), status="potential"),
    "SG-012": Signal("SYS-01", "acceso", "Una herramienta menciona una ruta de alto impacto.",
                     "La posición y las opciones deben confirmar el papel de la ruta.", status="indeterminate"),
    "SG-FLOW-001": Signal("SYS-13", "ejecución", "Se correlaciona una asignación con un comando intérprete.",
                          "La relación debe mantenerse durante la expansión y ejecución.", boundary="TB-02"),
    "SG-FLOW-002": Signal("SYS-07", "transferencia", "Se correlaciona una ruta sensible con una opción de carga.",
                          "La opción debe consumir el archivo y alcanzar el destino.", ("confidentiality",)),
    "PY-001": Signal("SYS-13", "ejecución", "La llamada evalúa datos como código.",
                     "La llamada debe ejecutarse con un argumento interpretable.", boundary="TB-02"),
    "PY-002": Signal("SYS-02", "ejecución", "La API de subprocesos solicita un shell.",
                     "La llamada debe ejecutarse y el sistema debe aceptar el comando.", boundary="TB-03"),
    "PY-003": Signal("SYS-13", "ejecución", "La API pickle puede reconstruir objetos con ejecución asociada.",
                     "La llamada debe deserializar datos con instrucciones de reconstrucción pertinentes."),
    "PY-004": Signal("SYS-13", "ejecución", "Se correlaciona una llamada de red con evaluación dinámica.",
                     "Los datos correlacionados deben llegar a la llamada como código válido.", boundary="TB-02"),
    "PY-005": Signal("SYS-06", "presencia", "Una variable de nombre sensible recibe un literal.",
                     "El literal tendría que ser un secreto válido.", ("confidentiality",), status="potential"),
    "PY-006": Signal("SYS-02", "ejecución", "La API identificada puede invocar un comando del sistema.",
                     "La llamada debe ejecutarse y el sistema debe aceptar el comando.", boundary="TB-03"),
    "PY-007": Signal("SYS-12", "acceso", "Un argumento dinámico llega a un método con nombre de consulta.",
                     "Debe confirmarse que el receptor sea una API de base de datos.", status="indeterminate"),
    "PY-008": Signal("SYS-11", "desactivación", "La llamada HTTP solicita desactivar la verificación TLS.",
                     "La llamada debe realizar una conexión TLS donde se aplique la opción.",
                     ("confidentiality", "integrity"), "TB-10"),
}
FLOW_RULES = {"SG-FLOW-001", "SG-FLOW-002", "PY-004"}
MAX_RELATIONS = 4


def _visible_range(finding, location):
    if finding.evidence_truncated or not location:
        return None
    start, end = location["start"], location["end"]
    if start["line"] != end["line"] or start["line"] != finding.location.start_line:
        return None
    left = start["column"] - finding.location.start_column
    right = end["column"] - finding.location.start_column
    if 0 <= left < right <= len(finding.instruction.partition("\n")[0]):
        return {"start": left, "end": right}
    return None


def enrich(finding, parser, deadline):
    provenance = f"{parser}/{finding.engine}/{finding.rule_id}"
    signal = SIGNALS.get(finding.rule_id)
    reason = None
    if time.monotonic() >= deadline:
        reason = "Se agotó el tiempo de análisis SITA."
    elif finding.engine != "python" or parser not in {"python-ast", "tree-sitter-bash"} or not signal:
        reason = "La procedencia o regla carece de cobertura SITA."
    elif finding.rule_id in FLOW_RULES and not finding.correlation:
        reason = "La regla requiere evidencia de correlación."
    if reason:
        return ImpactAnalysis("not_evaluated", "low", {
            dimension: Conclusion("not_evaluated", reason) for dimension in DIMENSIONS
        }, [reason], provenance)

    limitations = ["La señal estática no demuestra ejecución, acceso ni efecto observado."]
    result = ImpactAnalysis("syntax", "medium", {}, limitations, provenance)
    result.references.append(Reference("instruction", "instruction", finding.location.to_dict()))
    if finding.impact_target:
        location = finding.impact_target.to_dict()
        role = "sink"
        span = _visible_range(finding, location)
        result.references.append(Reference("target", role, location, span, "" if span else
                                           "El destino no tiene un rango verificable en la evidencia visible."))

    for index, relation in enumerate(finding.correlation[:MAX_RELATIONS]):
        source, sink = relation.get("source"), relation.get("sink", relation.get("destination"))
        if not source or not sink or not source.get("location") or not sink.get("location"):
            continue
        source_id, sink_id = f"source-{index}", f"sink-{index}"
        source_span = _visible_range(finding, source["location"]) if parser == "python-ast" else None
        result.references.extend([
            Reference(source_id, "source", source["location"], source_span, "" if source_span else
                      "El origen no está posicionado en la evidencia visible."),
            Reference(sink_id, "sink", sink["location"]),
        ])
        relationship = "indeterminate" if relation.get("relationship") != "possible" else "possible"
        result.flows.append(Flow(source_id, sink_id, relationship, len(relation.get("assignment_chain", []))))
    if result.flows:
        result.coverage = "correlated"
        result.confidence = "low"
        limitations.append("El orden y los valores en tiempo de ejecución requieren revisión.")
    if len(result.flows) != len(finding.correlation):
        result.coverage = "partial"
        limitations.append("Parte de la correlación superó el presupuesto o carece de ubicaciones.")

    refs = [reference.id for reference in result.references]
    status = signal.status
    if any(flow.relationship == "indeterminate" for flow in result.flows) or (
        finding.rule_id in FLOW_RULES and not result.flows
    ):
        status = "indeterminate"
    conditions = [signal.condition]
    result.resources.append(Resource(status, signal.justification, conditions, refs,
                                     signal.resource, RESOURCES[signal.resource], signal.operation,
                                     "correlated" if finding.rule_id in FLOW_RULES else "direct"))
    if result.flows and finding.rule_id == "PY-004":
        result.resources.append(Resource(
            status, "El AST identifica una llamada de red como origen posible.", conditions,
            [flow.source for flow in result.flows], "SYS-07", RESOURCES["SYS-07"], "acceso", "correlated",
        ))
    if signal.boundary:
        origin, destination = BOUNDARIES[signal.boundary]
        result.boundaries.append(Boundary(status, signal.justification, conditions, refs,
                                          signal.boundary, origin, destination))
    result.cia = {
        dimension: Conclusion(status, signal.justification, conditions, refs)
        if dimension in signal.dimensions else Conclusion(
            "indeterminate" if status == "indeterminate" else "not_established",
            "La señal disponible no establece un efecto en esta dimensión.",
            conditions if status == "indeterminate" else [],
            refs if status == "indeterminate" else [],
        )
        for dimension in DIMENSIONS
    }
    return result
