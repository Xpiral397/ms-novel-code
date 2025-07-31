//! tests/integration.rs

//! (save alongside your project’s Cargo.toml)



use std::io::Cursor;

use task_ws::solve_tsp;            // ← replace `task_ws` with your crate name



/// Helper: run the solver and capture its single‑line output.

fn run_ok(input: &str) -> String {

    let mut rdr = Cursor::new(input);

    let mut out = Vec::<u8>::new();

    solve_tsp(&mut rdr, &mut out).unwrap();

    String::from_utf8(out).unwrap().trim().to_string()

}



/// Helper: assert that the solver returns an error.

fn run_err(input: &str) {

    let mut rdr = Cursor::new(input);

    let mut out = Vec::<u8>::new();

    assert!(solve_tsp(&mut rdr, &mut out).is_err());

}



/* ---------- malformed‑input checks ---------- */



#[test] fn invalid_n()                 { run_err("foo\n"); }



#[test] fn bad_row_count()             { run_err(r#"3

0 1 2

3 4 5

"#); }



#[test] fn bad_row_too_short()         { run_err(r#"2

0

0 0

"#); }



#[test] fn bad_row_too_long()          { run_err(r#"2

0 1 2

0 0

"#); }



/* ---------- trivial sizes ---------- */



#[test] fn n_zero()                   { assert_eq!(run_ok("0\n"), "0"); }



#[test] fn n_one()                    { assert_eq!(run_ok("1\n0\n"), "0"); }



/* ---------- prompt examples ---------- */



#[test]

fn example_four_city() {

    let input = "4\n\

                 0 29 20 21\n\

                 29 0 15 17\n\

                 20 15 0 28\n\

                 21 17 28 0\n";

    assert_eq!(run_ok(input), "73");

}



#[test]

fn example_three_city() {

    let input = "3\n\

                 0 10 15\n\

                 10 0 20\n\

                 15 20 0\n";

    assert_eq!(run_ok(input), "45");

}

/* ---------- edge cases & blind spots ---------- */



#[test]

fn overflow_saturates() {

    let half = std::u32::MAX / 2;

    let expect = (half * 2).to_string();              // 4 294 967 294

    let inp = format!("2\n0 {}\n{} 0\n", half, half);

    assert_eq!(run_ok(&inp), expect);

}





#[test]

fn simd_tail_handling() {

    // N = 10, not a multiple of 8‑lane AVX2

    let mut inp = String::from("10\n");

    for _ in 0..10 { inp.push_str(&"0 ".repeat(10)); inp.push('\n'); }

    assert_eq!(run_ok(&inp), "0");

}



#[test]

fn simd_exact_lane() {

    // N = 8: exactly one AVX2 vector, all zeros

    let mut inp = String::from("8\n");

    for _ in 0..8 { inp.push_str(&"0 ".repeat(8)); inp.push('\n'); }

    assert_eq!(run_ok(&inp), "0");

}



#[test]

fn all_zero_n16() {

    let mut inp = String::from("16\n");

    for _ in 0..16 { inp.push_str(&"0 ".repeat(16)); inp.push('\n'); }

    assert_eq!(run_ok(&inp), "0");

}


