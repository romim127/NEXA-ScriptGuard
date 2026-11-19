"""Conservative, non-executing variable correlation. NOT a full Bash parser."""
import re

ASSIGN = re.compile(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)=(.*)$')
VAR = re.compile(r'\$(?:\{([A-Za-z_][A-Za-z_0-9]*)\}|([A-Za-z_][A-Za-z_0-9]*))')
NETWORK = re.compile(r'\b(?:curl|wget)\b')
SINK = re.compile(r'\|\s*(?:(?:sudo|env)\s+)*(?:bash|sh|zsh)\b|\b(?:bash|sh|zsh)\s+-c\b')
SENSITIVE = re.compile(r'(?:/etc/shadow|/etc/sudoers|\.ssh/id_(?:rsa|ed25519|ecdsa)|\.aws/credentials|\.env\b)')
UPLOAD = re.compile(r'\b(?:curl|wget)\b[^\n]*(?:--data-binary\s+@|--upload-file\s+|--data\s+@)')

def logical_lines(lines):
    buffer, start = [], None
    for number, line in enumerate(lines, 1):
        if start is None:
            start = number
        continued = bool(re.search(r'(?<!\\)(?:\\\\)*\\\s*$', line))
        buffer.append(re.sub(r'\\\s*$', ' ', line) if continued else line)
        if not continued:
            yield start, number, ' '.join(buffer)
            buffer, start = [], None
    if buffer:
        yield start, len(lines), ' '.join(buffer)

def correlated_findings(lines):
    assigned, results = {}, []
    for start, end, command in logical_lines(lines):
        if command.lstrip().startswith('#'):
            continue
        assignment = ASSIGN.match(command)
        if assignment:
            name, value = assignment.groups()
            assigned[name] = value
            continue
        refs = set((a or b) for a, b in VAR.findall(command))
        expanded = command
        for name in refs:
            if name in assigned:
                expanded = re.sub(r'\$\{' + re.escape(name) + r'\}|\$' + re.escape(name) + r'\b', lambda _: assigned[name], expanded)
        kind = None
        if NETWORK.search(expanded) and SINK.search(expanded) and not (NETWORK.search(command) and SINK.search(command)):
            kind = ('SG-FLOW-001','CRITICAL','Descarga remota ejecutada mediante variable','La descarga de red termina ejecutándose en un intérprete.','Revisar la variable y el origen remoto.')
        elif SENSITIVE.search(expanded) and UPLOAD.search(expanded) and not (SENSITIVE.search(command) and UPLOAD.search(command)):
            kind = ('SG-FLOW-002','CRITICAL','Posible transferencia de archivo sensible','Una variable puede referenciar un archivo sensible en una transferencia.','Verificar archivo, destino y autorización.')
        if kind:
            rule, severity, title, why, advice = kind
            results.append(dict(rule_id=rule,severity=severity,title=title,line=start,end_line=end,column=1,
                instruction='\n'.join(lines[start-1:end]),matched_fragment=command,explanation=why,
                recommendation=advice,verification_commands=['Revisar las asignaciones de variables'],
                confidence='medium',status='requires_review',context_before=lines[max(0,start-3):start-1],
                context_after=lines[end:min(len(lines),end+2)]))
    return results
