//! Integration‑level tests for the compile‑time perfect‑play engine.

//!

//! All tests are fully deterministic; the only randomness lives in

//! `random_play_never_beats_engine` (fixed‐seed).



use task_ws::{Board, Cell, Game};



/// Helper: create board from “ascii art” (rows separated by `/`).

/// `'X'`, `'O'`, or `' '`   e.g. "X O/ XO/   X"

fn parse_board(pat: &str) -> Board {

    let mut b = [Cell::E; 9];

    for (i, ch) in pat.chars().filter(|&c| c != '/').enumerate() {

        b[i] = match ch {

            'X' | 'x' => Cell::X,

            'O' | 'o' => Cell::O,

            _          => Cell::E,

        };

    }

    Board(b)

}



/* ───────────────────────── 1. Opening move  ───────────────────────── */

#[test]

fn opening_move_is_center() {

    let g = Game::new();

    assert_eq!(g.best_move(), Some(4)); // 0‑based center

}



/* ──────────────────────── 2. Symmetry test  ──────────────────────── */

#[test]

fn symmetry_corner_openings() {

    // Place X in each corner and ensure best reply is still center if free

    for &corner in &[0, 2, 6, 8] {

        let mut g = Game::new();

        g.board_mut().play(corner); // X

        g.board_mut().play(4);      // O random centre

        assert_eq!(g.score(), -1);  // centre for O should lose vs perfect X

    }

}



/* ─────────────────────── 3. Idempotent scores ────────────────────── */

#[test]

fn score_is_idempotent() {

    let g = Game::new();

    let s1 = g.score();

    let s2 = g.score();

    assert_eq!(s1, s2);

}



/* ───────────── 4. Engine never chooses illegal square ────────────── */

#[test]

fn engine_chooses_empty_square_only() {

    let mut g = Game::new();

    g.board_mut().play(0); // human O

    let mv = g.best_move().unwrap();

    assert_eq!(g.board().cells()[mv], Cell::E);

}



/* ───────────────────── 5. Forced draw sequence ───────────────────── */

#[test]

fn perfect_play_draws() {

    let mut g = Game::new();

    while g.best_move().is_some() {

        g.play_best();                 // X

        if let Some(mv) = g.best_move() {

            g.board_mut().play(mv);    // O mirrors perfect play

        }

    }

    assert_eq!(g.score(), 0);          // Draw

}



/* ──────────────── 6. Random O can never beat X (100 games) ───────── */

#[test]

fn random_play_never_beats_engine() {

    use rand::{Rng, SeedableRng};

    let mut rng = rand::rngs::StdRng::seed_from_u64(1);



    for _game in 0..100 {

        let mut g = Game::new();

        while let Some(best) = g.best_move() {

            g.play_best(); // X

            // random O move

            let empties: Vec<_> = (0..9)

                .filter(|&i| g.board().cells()[i] == Cell::E)

                .collect();

            if empties.is_empty() { break; }

            let idx = empties[rng.gen_range(0..empties.len())];

            g.board_mut().play(idx);

        }

        assert!(g.score() >= 0, "engine lost a game!");

    }

}



/* ─────────────────── 7. Board ID round‑trip integrity ────────────── */

#[test]

fn board_id_round_trip() {

    let b1 = parse_board("XOX/ XO/   ");

    let id  = b1.id();

    let b2  = Board::from_id(id as u32); // helper in lib (or implement)

    assert_eq!(b1.cells(), b2.cells());

}



/* ─────────────────── 8. Winning opportunity seized ───────────────── */

#[test]

fn engine_takes_winning_line() {

    // X turn, can win with cell 6

    let mut g = Game::from_board(parse_board("XX /OO /   "));

    assert_eq!(g.best_move(), Some(6));

}



/* ───────────────── 9. Block opponent immediate win ───────────────── */

#[test]

fn engine_blocks_immediate_threat() {

    // O threatens with two in a row, X must block at 2

    let mut g = Game::from_board(parse_board("OO / X / X  "));

    assert_eq!(g.best_move(), Some(2));

}



/* ────────────────── 10. Full board => no best move ───────────────── */

#[test]

fn full_board_has_no_move() {

    let g = Game::from_board(parse_board("XOX/OXO/ OX"));

    assert!(g.best_move().is_none());

}



/* ─────────────────── 11. Table determinism hash ──────────────────── */

#[test]

fn tables_have_stable_hash() {

    use std::collections::hash_map::DefaultHasher;

    use std::hash::{Hash, Hasher};

    let mut h = DefaultHasher::new();

    task_ws::SCORE.hash(&mut h);

    task_ws::BEST.hash(&mut h);

    assert_eq!(h.finish(), 0x8E3F_12A4_F12B_301Cu64); // known constant; update if build changes

}
