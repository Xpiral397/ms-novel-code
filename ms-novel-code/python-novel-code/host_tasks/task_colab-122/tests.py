# tests

# test_gpu_sim.py
import unittest
import numpy as np
import cupy as cp
from typing import Any
from main import GpuSim


# CUDA kernels for float32 and float64 increments
_code_f32 = r"""
extern "C" __global__
void inc(float* a, const unsigned int N) {
    unsigned int i = blockDim.x * blockIdx.x + threadIdx.x;
    if (i < N) a[i] += 1.0f;
}
"""

_code_f64 = r"""
extern "C" __global__
void inc(double* a, const unsigned int N) {
    unsigned int i = blockDim.x * blockIdx.x + threadIdx.x;
    if (i < N) a[i] += 1.0;
}
"""

KER_F32 = cp.RawKernel(_code_f32, "inc")
KER_F64 = cp.RawKernel(_code_f64, "inc")


class TestGpuSim(unittest.TestCase):
    # ----- constructor validation -------------------------------------------------
    def test_invalid_shape(self) -> None:
        with self.assertRaises(ValueError):
            GpuSim(shape=(0, 1, 1), dtype='float32', kernel=KER_F32, steps=1, sync=1)

    def test_invalid_dtype(self) -> None:
        with self.assertRaises(ValueError):
            GpuSim(shape=(1, 1, 1), dtype='int32', kernel=KER_F32, steps=1, sync=1)

    def test_invalid_kernel_type(self) -> None:
        with self.assertRaises(ValueError):
            GpuSim(shape=(1, 1, 1), dtype='float32', kernel=lambda x: x, steps=1, sync=1)

    def test_invalid_steps(self) -> None:
        with self.assertRaises(ValueError):
            GpuSim(shape=(1, 1, 1), dtype='float32', kernel=KER_F32, steps=0, sync=1)

    def test_invalid_sync(self) -> None:
        with self.assertRaises(ValueError):
            GpuSim(shape=(1, 1, 1), dtype='float32', kernel=KER_F32, steps=1, sync=0)

    # ----- functional edge cases --------------------------------------------------
    def test_single_cell_single_step(self) -> None:
        sim = GpuSim(shape=(1, 1, 1), dtype='float32', kernel=KER_F32, steps=1, sync=1)
        result = sim.run()
        self.assertEqual(result["data"].shape, (1, 1, 1))
        self.assertTrue(np.allclose(result["data"], 1.0))

    def test_sync_larger_than_steps(self) -> None:
        sim = GpuSim(shape=(2, 2, 2), dtype='float32', kernel=KER_F32, steps=5, sync=10)
        result = sim.run()
        self.assertTrue(np.allclose(result["data"], 5.0))

    def test_float64_kernel(self) -> None:
        sim = GpuSim(shape=(4, 4, 4), dtype='float64', kernel=KER_F64, steps=3, sync=1)
        result = sim.run()
        self.assertEqual(result["data"].dtype, np.float64)
        self.assertTrue(np.allclose(result["data"], 3.0))

    def test_large_steps_under_memory_cap(self) -> None:
        sim = GpuSim(shape=(8, 8, 8), dtype='float32', kernel=KER_F32, steps=100, sync=50)
        result = sim.run()
        self.assertTrue(np.allclose(result["data"], 100.0))

    # ----- determinism & repeatability -------------------------------------------
    def test_deterministic_results(self) -> None:
        sim1 = GpuSim(shape=(3, 3, 3), dtype='float32', kernel=KER_F32, steps=7, sync=2)
        sim2 = GpuSim(shape=(3, 3, 3), dtype='float32', kernel=KER_F32, steps=7, sync=2)
        res1 = sim1.run()["data"]
        res2 = sim2.run()["data"]
        self.assertTrue(np.array_equal(res1, res2))

    def test_run_twice_new_instance(self) -> None:
        sim = GpuSim(shape=(2, 2, 2), dtype='float32', kernel=KER_F32, steps=4, sync=2)
        first = sim.run()["data"].copy()
        second = sim.run()["data"]
        self.assertTrue(np.array_equal(first, second))

    # ----- stress on shape dimension variety -------------------------------------
    def test_non_cube_shape(self) -> None:
        sim = GpuSim(shape=(4, 8, 2), dtype='float32', kernel=KER_F32, steps=6, sync=3)
        result = sim.run()
        self.assertEqual(result["data"].shape, (4, 8, 2))
        self.assertTrue(np.allclose(result["data"], 6.0))

    def test_medium_size_grid(self) -> None:
        sim = GpuSim(shape=(16, 16, 16), dtype='float32', kernel=KER_F32, steps=2, sync=1)
        result = sim.run()
        self.assertTrue(np.allclose(result["data"], 2.0))

    def test_host_copy_every_step(self) -> None:
        sim = GpuSim(shape=(4, 4, 4), dtype='float32', kernel=KER_F32, steps=5, sync=1)
        out = sim.run()
        self.assertTrue(np.array_equal(out["data"], np.full((4, 4, 4), 5.0, dtype=np.float32)))


if __name__ == "__main__":
    unittest.main()
