//! build.rs – generates a perfect Tic‑Tac‑Toe solver at compile‑time

//!

//! * enumerates every possible board (3^9 states)

//! * runs minimax to label each state:

//!     1 = “X wins”, ‑1 = “O wins”,  0 = “forced draw”

//! * computes the *best move* (cell 0‑8) for every “X to move” state

//! * writes a `const fn lookup()` that returns (score, best_move)

//!

//! No external data or crates required.



use std::{env,fs,path::Path};



const POW3: [u32;10] = {

    let mut p = [1u32;10];

    let mut i=1; while i<10 { p[i] = p[i-1]*3; i+=1; }

    p

};



#[derive(Clone,Copy,PartialEq)]

enum Cell { E=0, X=1, O=2 }



#[derive(Clone)]

struct Board([Cell;9]);



impl Board {

    fn from_id(mut id:u32)->Self{

        let mut b=[Cell::E;9];

        for c in &mut b {

            *c = match id%3 {0=>Cell::E,1=>Cell::X,_=>Cell::O};

            id/=3;

        }

        Board(b)

    }

    fn id(&self)->u32{

        self.0.iter().enumerate().map(|(i,c)| (*c as u32)*POW3[i]).sum()

    }

    fn turn(&self)->Cell{

        let xs=self.0.iter().filter(|&&c|c==Cell::X).count();

        let os=self.0.iter().filter(|&&c|c==Cell::O).count();

        if xs==os {Cell::X} else {Cell::O}

    }

    fn winner(&self)->Option<Cell>{

        const LINES:[[usize;3];8]=[

            [0,1,2],[3,4,5],[6,7,8],[0,3,6],

            [1,4,7],[2,5,8],[0,4,8],[2,4,6]];

        for line in &LINES{

            let [a,b,c]=*line;

            let ca=self.0[a];

            if ca!=Cell::E && ca==self.0[b] && ca==self.0[c] {return Some(ca);}

        }

        None

    }

    fn moves(&self)->Vec<usize>{

        self.0.iter().enumerate().filter_map(|(i,c)|

            if *c==Cell::E {Some(i)} else {None}).collect()

    }

    fn play(&mut self, idx:usize){

        self.0[idx]=self.turn();

    }

}



/* minimax with memoisation on 19 683 states */

fn main(){

    let mut score  = vec![None::<i8>; 19_683];

    let mut best   = vec![255u8;      19_683];



    fn solve(b:&mut Board, cache:&mut[Option<i8>], best:&mut[ u8]) -> i8 {

        let id=b.id() as usize;

        if let Some(s)=cache[id]{ return s; }

        if let Some(w)=b.winner(){

            let s = if w==Cell::X {1} else {-1};

            cache[id]=Some(s); return s;

        }

        if b.moves().is_empty(){ cache[id]=Some(0); return 0; }



        let mut best_score=-2; // worse than loss

        let mut best_move=255;

        for m in b.moves(){

            let mut nb=b.clone(); nb.play(m);

            let s = -solve(&mut nb, cache, best); // opponent perspective

            if s>best_score { best_score=s; best_move=m as u8; }

            if best_score==1 {break;}

        }

        cache[id]=Some(best_score);

        best[id]=best_move;

        best_score

    }



    for id in 0..19_683{

        let mut brd = Board::from_id(id as u32);

        if brd.turn()==Cell::X { solve(&mut brd,&mut score,&mut best); }

    }



    /* generate Rust source */

    let out = env::var("OUT_DIR").unwrap();

    let dest= Path::new(&out).join("tictac_tables.rs");

    let mut code = String::from("/// Auto‑generated perfect‑play tables\n");

    code.push_str(&format!("pub static SCORE: [i8;19683] = {:?};\n",score.iter().map(|o|o.unwrap_or(0)).collect::<Vec<_>>()));

    code.push_str(&format!("pub static BEST : [u8;19683] = {:?};\n",best));

    fs::write(dest,code).unwrap();

}
