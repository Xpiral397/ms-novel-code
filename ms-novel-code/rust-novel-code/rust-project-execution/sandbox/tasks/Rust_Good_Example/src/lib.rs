// src/lib.rs



use std::io::{self, BufRead, Write};



#[cfg(target_arch = "x86_64")]

use std::arch::x86_64::{

    __m256i, _mm256_add_epi32, _mm256_loadu_si256, _mm256_min_epu32, _mm256_set1_epi32,

    _mm256_storeu_si256,

};



/// Solver for the bitmask‐DP Traveling Salesman Problem.

pub struct DpSolver {

    pub n: usize,

    pub dist: Vec<Vec<u32>>,

    pub dp: Vec<u32>,

}



impl DpSolver {

    /// Initialize a new solver for `n` cities with the given distance matrix.

    pub fn new(n: usize, dist: Vec<Vec<u32>>) -> Self {

        let size = (1 << n) * n;

        let mut dp = vec![u32::MAX; size];

        if n > 0 {

            dp[(1 << 0) * n + 0] = 0;

        }

        DpSolver { n, dist, dp }

    }



    /// Compute the shortest Hamiltonian cycle length.

    ///

    /// Uses AVX2 SIMD if detected at runtime, otherwise falls back to scalar.

    /// Returns 0 immediately for n ≤ 1.

    pub fn compute(&mut self) -> u32 {

        if self.n <= 1 {

            return 0;

        }

        let full_mask = (1 << self.n) - 1;

        #[cfg(target_arch = "x86_64")]

        {

            if is_x86_feature_detected!("avx2") {

                // SAFETY: AVX2 support was checked

                return unsafe { self.compute_simd(full_mask) };

            }

        }

        self.compute_scalar(full_mask)

    }



    /// Scalar fallback implementation.

    fn compute_scalar(&mut self, full: usize) -> u32 {

        let n = self.n;

        for mask in 1..=full {

            for i in 0..n {

                if mask & (1 << i) == 0 { continue; }

                let prev = mask ^ (1 << i);

                if prev == 0 {         // keep the seed dp[1*n + 0] = 0

                    continue;

                }

                let base_prev = prev * n;

                let idx = mask * n + i;

                let mut best = u32::MAX;

                for j in 0..n {

                    if prev & (1 << j) != 0 {

                        let cost = self.dp[base_prev + j].saturating_add(self.dist[j][i]);

                        if cost < best { best = cost; }

                    }

                }

                self.dp[idx] = best;

            }

        }

        // close cycle

        let mut result = u32::MAX;

        for i in 0..n {

            let cost = self

                .dp[full * n + i]

                .saturating_add(self.dist[i][0]);

            if cost < result {

                result = cost;

            }

        }

        result

    }



    /// Unsafe SIMD‐accelerated implementation (AVX2).

    #[target_feature(enable = "avx2")]

    pub unsafe fn compute_simd(&mut self, full_mask: usize) -> u32 {

        let n = self.n;

        let lane = 8;

        let chunks = n / lane;

        for mask in 1..=full_mask {

            for i in 0..n {

                if mask & (1 << i) == 0 { continue; }

                let prev = mask ^ (1 << i);

                if prev == 0 {                 continue;           }

                let base = mask * n + i;

                let base_prev = prev * n;



                let mut best_vec: __m256i = _mm256_set1_epi32(-1);

                for c in 0..chunks {

                    let j0 = c * lane;

                    let dp_ptr = self.dp.as_ptr().add(base_prev + j0) as *const __m256i;

                    let dp_vec = _mm256_loadu_si256(dp_ptr);



                    let mut ds = [0u32; 8];

                    for k in 0..lane {

                        ds[k] = self.dist[j0 + k][i];

                    }

                    let dist_vec = _mm256_loadu_si256(ds.as_ptr() as *const __m256i);



                    let sum = _mm256_add_epi32(dp_vec, dist_vec);

                    best_vec = _mm256_min_epu32(best_vec, sum);

                }



                let mut tmp = [0u32; 8];

                _mm256_storeu_si256(tmp.as_mut_ptr() as *mut __m256i, best_vec);

                let mut best = tmp.iter().cloned().min().unwrap_or(u32::MAX);



                for j in (chunks * lane)..n {

                    if prev & (1 << j) != 0 {

                        let cost = self.dp[base_prev + j].saturating_add(self.dist[j][i]);

                        if cost < best { best = cost; }

                    }

                }



                self.dp[base] = best;

            }

        }

        // close cycle

        let mut result = u32::MAX;

        for i in 0..n {

            let cost = self

                .dp[full_mask * n + i]

                .saturating_add(self.dist[i][0]);

            if cost < result {

                result = cost;

            }

        }

        result

    }

}



/// Parse input, validate, run the solver, and write output.

pub fn solve_tsp<R: BufRead, W: Write>(

    input: &mut R,

    output: &mut W,

) -> io::Result<()> {

    let mut buf = String::new();

    input.read_line(&mut buf)?;

    let n: usize = buf.trim().parse().map_err(|_| {

        io::Error::new(io::ErrorKind::InvalidData, "Invalid N")

    })?;



    if n == 0 {

        writeln!(output, "0")?;

        return Ok(());

    }



    let mut dist = Vec::with_capacity(n);

    for line_idx in 0..n {

        buf.clear();

        input.read_line(&mut buf)?;

        let row: Vec<u32> = buf

            .split_whitespace()

            .map(|s| s.parse().unwrap_or(u32::MAX))

            .collect();

        if row.len() != n {

            return Err(io::Error::new(

                io::ErrorKind::InvalidData,

                format!("Line {}: expected {} values, got {}", line_idx + 1, n, row.len()),

            ));

        }

        dist.push(row);

    }



    let mut solver = DpSolver::new(n, dist);

    let ans = solver.compute();

    writeln!(output, "{}", ans)?;

    Ok(())

}


