use clap::Parser;
use serde::Deserialize;
use std::{
    collections::HashMap,
    fs,
    io::{self, ErrorKind, Read},
    path::{Path, PathBuf},
    process::{Command, ExitStatus},
    time::{Duration, Instant},
};
use wait_timeout::ChildExt;

/// ANSI color codes
mod colors {
    pub const RESET: &str = "\x1B[0m";
    pub const RED: &str   = "\x1B[91m";
    pub const GREEN: &str = "\x1B[92m";
    pub const BLUE: &str  = "\x1B[94m";
    pub const BOLD: &str  = "\x1B[1m";
}
use colors::*;

#[derive(Parser)]
#[command(about = "Validate & run a Rust‑task notebook")]
struct Args {
    #[arg(value_hint = clap::ValueHint::FilePath)]
    task_file: PathBuf,

    #[arg(short, long, default_value_t = 1)]
    runs: usize,

    #[arg(short, long, default_value_t = 120)]
    timeout: u64,
}

#[derive(Deserialize)]
#[serde(tag = "cell_type", rename_all = "lowercase")]
enum Cell {
    Markdown { source: Vec<String> },
    Code     { source: Vec<String> },
}

#[derive(Deserialize)]
struct Notebook { cells: Vec<Cell> }

fn load_notebook(path: &Path) -> io::Result<Notebook> {
    if !path.exists() {
        return Err(io::Error::new(ErrorKind::NotFound, "Notebook file not found"));
    }
    if path.extension().and_then(|s| s.to_str()) != Some("ipynb") {
        return Err(io::Error::new(ErrorKind::InvalidInput, "Expected a .ipynb file"));
    }
    let raw = fs::read_to_string(path)?;
    serde_json::from_str(&raw)
        .map_err(|e| io::Error::new(ErrorKind::Other, format!("JSON error: {}", e)))
}

fn extract_rust_block(lines: &[String]) -> String {
    let mut in_block = false;
    let mut out = Vec::new();
    for line in lines {
        let t = line.trim_start();
        if t.starts_with("```rust") {
            in_block = true;
            continue;
        }
        if in_block && t.starts_with("```") {
            break;
        }
        if in_block {
            out.push(line.clone());
        }
    }
    out.join("\n")
}

fn prepare_workspace(nb: &Notebook, workspace: &Path) -> Result<Vec<String>, String> {
    if workspace.exists() {
        fs::remove_dir_all(workspace).map_err(|e| e.to_string())?;
    }
    fs::create_dir_all(workspace).map_err(|e| e.to_string())?;

    fs::write(
        workspace.join("Cargo.toml"),
        r#"[package]
name = "task_ws"
version = "0.1.0"
edition = "2021"
[dependencies]
"#,
    ).map_err(|e| e.to_string())?;

    let mut seen = HashMap::new();
    let mut files = vec!["Cargo.toml".into()];

    for cell in &nb.cells {
        let src = match cell {
            Cell::Markdown { source } | Cell::Code { source } => source,
        };
        let joined = src.join("");

        if joined.contains("# lib") && joined.contains("```rust") {
            let dir = workspace.join("src");
            fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
            fs::write(dir.join("lib.rs"), extract_rust_block(src))
                .map_err(|e| e.to_string())?;
            seen.insert("lib", true);
            files.push("src/lib.rs".into());
        }
        if joined.contains("# main") && joined.contains("```rust") {
            let dir = workspace.join("src");
            fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
            fs::write(dir.join("main.rs"), extract_rust_block(src))
                .map_err(|e| e.to_string())?;
            seen.insert("main", true);
            files.push("src/main.rs".into());
        }
        if joined.contains("# test") && joined.contains("```rust") {
            let dir = workspace.join("tests");
            fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
            fs::write(dir.join("integration.rs"), extract_rust_block(src))
                .map_err(|e| e.to_string())?;
            seen.insert("test", true);
            files.push("tests/integration.rs".into());
        }
        if joined.contains("# build") && joined.contains("```rust") {
            fs::write(workspace.join("build.rs"), extract_rust_block(src))
                .map_err(|e| e.to_string())?;
            seen.insert("build", true);
            files.push("build.rs".into());
        }
    }

    for &req in &["lib", "main", "test"] {
        if !seen.contains_key(req) {
            return Err(format!("Missing required code section: `# {}`", req));
        }
    }
    Ok(files)
}

fn run_cargo_test(workspace: &Path, timeout: u64) -> Result<ExitStatus, String> {
    let mut child = Command::new("cargo")
        .arg("test")
        .current_dir(workspace)
        .spawn()
        .map_err(|e| e.to_string())?;
    match child.wait_timeout(Duration::from_secs(timeout))
               .map_err(|e| e.to_string())? {
        Some(status) => Ok(status),
        None => {
            let _ = child.kill();
            Err("Timeout reached".into())
        }
    }
}

/// Run `cargo test` once, capture each test’s pass/fail outcome.
fn run_cargo_test_once(
    workspace: &Path,
    timeout: u64
) -> Result<HashMap<String,bool>, String> {
    let mut child = Command::new("cargo")
        .arg("test")
        .arg("--color=never")
        .current_dir(workspace)
        .stdout(std::process::Stdio::piped())
        .spawn()
        .map_err(|e| e.to_string())?;

    // wait with timeout
    let status = match child
        .wait_timeout(Duration::from_secs(timeout))
        .map_err(|e| e.to_string())? {
        Some(s) => s,
        None => { let _ = child.kill(); return Err("Timeout reached".into()); }
    };

    // read stdout
    let mut buf = String::new();
    if let Some(mut out) = child.stdout.take() {
        out.read_to_string(&mut buf).unwrap();
    }

    // parse lines: test <name> ... ok/FAILED
    let mut map = HashMap::new();
    for line in buf.lines() {
        if let Some(rest) = line.strip_prefix("test ") {
            let mut parts = rest.split(" ... ");
            if let (Some(name), Some(res)) = (parts.next(), parts.next()) {
                map.insert(name.to_string(), res.trim() == "ok");
            }
        }
    }

    if !status.success() && map.is_empty() {
        return Err(format!("`cargo test` failed (exit {:?})", status.code()));
    }

    Ok(map)
}

fn main() {
    let args = Args::parse();

    let stem = args
        .task_file
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("task_ws");
    let workspace = Path::new("tasks").join(stem);

    let nb = load_notebook(&args.task_file).unwrap_or_else(|e| {
        eprintln!("{}Error loading {}: {}{}", RED, args.task_file.display(), e, RESET);
        std::process::exit(1);
    });

    let files = match prepare_workspace(&nb, &workspace) {
        Ok(f) => f,
        Err(err) => {
            eprintln!("{}Validation error:{} {}", RED, BOLD, RESET);
            eprintln!("  {}", err);
            std::process::exit(1);
        }
    };

    // Build per-test pass/fail matrix over N runs
    let mut matrix: HashMap<String, Vec<bool>> = HashMap::new();

    for run in 1..=args.runs {
        println!("{}Run {}/{}{}", BLUE, run, args.runs, RESET);
        let t0 = Instant::now();
        match run_cargo_test_once(&workspace, args.timeout) {
            Ok(results) => {
                println!("  {}completed in {:.2}s{}", GREEN, t0.elapsed().as_secs_f32(), RESET);
                for (name, passed) in results {
                    matrix.entry(name).or_default().push(passed);
                }
            }
            Err(e) => {
                eprintln!("{}cargo test error:{} {}", RED, RESET, e);
                std::process::exit(1);
            }
        }
    }

    // Print consistency table
    println!("\n{:<45} | {:<16} | {:>6} | {:>6}",
             "Test", "Consistency", "Pass%", "Fail%");
    println!("{:-<45}-+-{:-<16}-+-{:-<6}-+-{:-<6}", "", "", "", "");

    let mut consistent_pass = 0;
    let mut consistent_fail = 0;
    let mut flaky = 0;

    for (test, runs) in &matrix {
        let pass_count = runs.iter().filter(|&&b| b).count() as f32;
        let total = runs.len() as f32;
        let pass_pct = 100.0 * pass_count / total;
        let fail_pct = 100.0 - pass_pct;

        let (label, col) = if pass_pct == 100.0 {
            consistent_pass += 1;
            ("Consistent pass", GREEN)
        } else if fail_pct == 100.0 {
            consistent_fail += 1;
            ("Consistent fail", RED)
        } else {
            flaky += 1;
            ("Flaky", BLUE)
        };

        println!("{:<45} | {}{:<16}{} | {:>5.0}% | {:>5.0}%",
                 test, col, label, RESET, pass_pct, fail_pct);
    }

    // Totals & exit
    println!("\nTotals:");
    println!("Consistent pass : {}", consistent_pass);
    println!("Consistent fail : {}", consistent_fail);
    println!("Flaky           : {}", flaky);

    if consistent_fail == 0 && flaky == 0 {
        println!("{}All tests consistently passed 🎉{}", GREEN, RESET);
        std::process::exit(0);
    } else {
        std::process::exit(1);
    }
}
