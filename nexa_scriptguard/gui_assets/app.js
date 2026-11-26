"use strict";
const token = location.hash.slice(1) || sessionStorage.getItem("nexa-token") || "";
if (token) sessionStorage.setItem("nexa-token", token);
history.replaceState(null, "", location.pathname);
const input = document.getElementById("script-file");
const analyze = document.getElementById("analyze");
const status = document.getElementById("status");
const findings = document.getElementById("findings");
const exportsPanel = document.getElementById("exports");
const filename = document.getElementById("filename");
const language = document.getElementById("language");
const hash = document.getElementById("hash");
const date = document.getElementById("date");
const maxInputBytes = Number(document.body.dataset.maxInputBytes);
let resultId = "";

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function detail(card, label, value) {
  const section = element("div", "detail");
  section.append(element("span", "", label), element("p", "", value));
  card.append(section);
}

function showFinding(finding) {
  const severities = ["critical", "high", "medium", "low", "info"];
  const severity = String(finding.severity).toLowerCase();
  const card = element("section", `finding sev-${severities.includes(severity) ? severity : "info"}`);
  const heading = element("div", "heading");
  heading.append(element("span", "flag", `⚠ ${finding.severity}`), element("span", "rule", finding.rule_id));
  card.append(heading, element("h2", "", finding.title));
  const location = finding.location.start;
  card.append(element("div", "metadata", `LÍNEA ${location.line} · COLUMNA ${location.column} · CONFIANZA: ${finding.confidence}`));
  card.append(element("h3", "", "INSTRUCCIÓN DETECTADA"));
  card.append(element("pre", "instruction", `${String(location.line).padStart(4, "0")} │ ${finding.instruction}`));
  detail(card, "EVIDENCIA COMPARTIBLE", finding.evidence.shared);
  detail(card, "CONTEXTO", [...finding.context.before, ...finding.context.after].join("\n") || "Sin contexto adicional.");
  if (finding.evidence.correlation.length) detail(card, "CORRELACIÓN", JSON.stringify(finding.evidence.correlation, null, 2));
  detail(card, "ANÁLISIS TÉCNICO", finding.explanation);
  detail(card, "RECOMENDACIÓN", finding.recommendation);
  detail(card, "VERIFICACIONES · NO EJECUTADAS", finding.verification_commands.join("\n"));
  card.append(element("footer", "", `ESTADO: ${finding.status} · ${finding.confidence_reason}`));
  findings.append(card);
}

input.addEventListener("change", () => {
  const file = input.files[0];
  filename.textContent = file ? file.name : "Ninguno";
  language.textContent = file ? (/\.sh$/i.test(file.name) ? "Bash" : /\.py$/i.test(file.name) ? "Python" : "No compatible") : "—";
  const tooLarge = file && maxInputBytes > 0 && file.size > maxInputBytes;
  analyze.disabled = !file || tooLarge;
  exportsPanel.hidden = true;
  resultId = "";
  findings.replaceChildren();
  hash.textContent = "";
  date.textContent = "";
  status.classList.toggle("error", Boolean(tooLarge));
  status.textContent = tooLarge ? "El archivo supera el límite de entrada."
    : "Seleccione Analizar archivo. El contenido no se ejecutará.";
});

analyze.addEventListener("click", async () => {
  const file = input.files[0];
  if (!file) return;
  analyze.disabled = true;
  input.disabled = true;
  exportsPanel.hidden = true;
  resultId = "";
  findings.replaceChildren();
  hash.textContent = "";
  date.textContent = "";
  status.classList.remove("error");
  status.textContent = "ANALIZANDO · El script no se ejecuta.";
  try {
    const response = await fetch("/analyze", {
      method: "POST",
      headers: {"X-Nexa-Token": token, "X-Nexa-Filename": encodeURIComponent(file.name), "Content-Type": "application/octet-stream"},
      body: file
    });
    const report = await response.json();
    if (!response.ok) throw new Error(report.error || `Error HTTP ${response.status}`);
    language.textContent = report.parser === "python-ast" ? "Python" : /\.py$/i.test(file.name) ? "Python" : "Bash";
    resultId = response.headers.get("X-Nexa-Result");
    if (!resultId) throw new Error("Falta el identificador de resultado.");
    const counts = {};
    for (const finding of report.findings) counts[finding.severity] = (counts[finding.severity] || 0) + 1;
    status.textContent = `${report.complete ? "ANÁLISIS COMPLETO" : "ANÁLISIS INCOMPLETO"} · ${report.findings.length} HALLAZGOS · ${Object.entries(counts).map(([k, v]) => `${k} ${v}`).join(" · ")}`;
    if (!report.complete) {
      status.classList.add("error");
      for (const reason of report.incomplete_reasons) findings.append(element("p", "notice", `INCOMPLETO: ${reason}`));
    }
    if (!report.findings.length) findings.append(element("p", "notice", "Sin coincidencias; esto no garantiza seguridad."));
    for (const finding of report.findings) showFinding(finding);
    hash.textContent = `SHA-256: ${report.sha256}`;
    date.textContent = `FECHA UTC: ${report.analyzed_at_utc}`;
    exportsPanel.hidden = false;
  } catch (error) {
    status.classList.add("error");
    status.textContent = `ERROR · ${error.message}`;
  } finally {
    analyze.disabled = false;
    input.disabled = false;
  }
});

exportsPanel.addEventListener("click", async (event) => {
  const format = event.target.dataset.export;
  if (!["json", "html", "sarif"].includes(format)) return;
  try {
    const response = await fetch(`/export/${format}`, {headers: {"X-Nexa-Token": token, "X-Nexa-Result": resultId}});
    if (!response.ok) throw new Error((await response.json()).error);
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = `nexa-scriptguard-report.${format}`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) {
    status.classList.add("error");
    status.textContent = `ERROR DE EXPORTACIÓN · ${error.message}`;
  }
});
