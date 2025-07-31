use std::io::{self,Write};

use task_ws::{Game,Cell};



fn main(){

    let mut game = Game::new();

    loop{

        println!("\n{}\n",game.board());

        if game.best_move().is_none(){

            println!("Game over!  Score {}",game.score());

            break;

        }

        // engine plays as X

        if game.board().turn()==Cell::X { game.play_best(); continue; }



        print!("Your move (0‑8): "); io::stdout().flush().unwrap();

        let mut inp=String::new(); io::stdin().read_line(&mut inp).unwrap();

        if let Ok(idx)=inp.trim().parse::<usize>() {

            if idx<9 && game.board().best_move()!=Some(idx){

                game.board_mut().play(idx);

            }

        }

    }

}
