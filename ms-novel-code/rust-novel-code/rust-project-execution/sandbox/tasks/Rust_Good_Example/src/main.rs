// src/main.rs



use std::io::{self, BufRead, Write};

use task_ws::solve_tsp;



fn main() -> io::Result<()> {

    let stdin = io::stdin();

    let stdout = io::stdout();

    solve_tsp(&mut stdin.lock(), &mut stdout.lock())

}
