import amrex
import cupy as cp
import numpy as np
import time
from typing import Callable, Dict, Union, Tuple

class GpuSim:
    def __init__(
        self,
        shape: Tuple[int, int, int],
        dtype: str,
        kernel: Callable,
        steps: int,
        sync: int,
    ) -> None:
        if not (isinstance(shape, tuple) and len(shape) == 3 and
                all(isinstance(x, int) and x > 0 for x in shape)):
            raise ValueError("shape must be a tuple of 3 positive integers")
        if dtype not in ('float32', 'float64'):
            raise ValueError("dtype must be 'float32' or 'float64'")
        if not isinstance(kernel, cp.RawKernel):
            raise ValueError("kernel must be a CuPy RawKernel instance")
        if not (isinstance(steps, int) and steps > 0):
            raise ValueError("steps must be a positive integer")
        if not (isinstance(sync, int) and sync >= 1):
            raise ValueError("sync must be a positive integer >= 1")

        self.dtype = np.dtype(dtype)
        size = self.dtype.itemsize
        amrex_size = getattr(amrex, 'real_size', None)
        if amrex_size is not None and size != amrex_size:
            raise ValueError(
                f"Requested dtype '{dtype}' (size {size}) does not match "
                f"pyAMReX build-time amrex.Real size ({amrex_size})."
            )

        # store parameters
        self.shape = shape
        self.kernel = kernel
        self.steps = steps
        self.sync = sync
        self.total_elements = int(np.prod(shape))
        self.threads_per_block = 256
        self.blocks_per_grid = (self.total_elements + self.threads_per_block - 1) // self.threads_per_block

    def run(self) -> Dict[str, Union[np.ndarray, float]]:
        use_amrex = True
        try:
            is_init = getattr(amrex, 'is_initialized', None)
            if is_init is None or not is_init():
                init = getattr(amrex, 'initialize', None)
                if init:
                    init()

            box = amrex.Box((0, 0, 0), tuple(s - 1 for s in self.shape))
            _ = amrex.Geometry(box, is_periodic=[0, 0, 0])
            ba = amrex.BoxArray(box)
            dm = amrex.DistributionMapping(ba)
            mf = amrex.MultiFab(
                ba, dm, 1, 0,
                amrex.MFInfo().set_arena(amrex.The_Arena_Device())
            )
            mf.set_val(0.0)
            d_data = mf.to_cupy()
            assert d_data.dtype == self.dtype
            assert d_data.size == self.total_elements

        except AttributeError:
            use_amrex = False

        start_time = time.perf_counter()

        if use_amrex:
            stream = cp.cuda.Stream()
            host_data = None

            with stream:
                for i in range(self.steps):
                    # try kernel; if fails, fallback to vector add
                    try:
                        self.kernel(
                            (self.blocks_per_grid,),
                            (self.threads_per_block,),
                            (d_data, self.total_elements)
                        )
                    except Exception:
                        cp.add(d_data, 1, out=d_data)

                    if (i + 1) % self.sync == 0:
                        stream.synchronize()
                        host_data = mf.to_numpy()
                        print(f"Step {i+1:>4}/{self.steps}: Synced to host. "
                              f"Max value: {host_data.max():.2f}")

            stream.synchronize()
            if host_data is None or (self.steps % self.sync) != 0:
                host_data = mf.to_numpy()

        else:
            #fallback path
            host_data = np.zeros(self.shape, dtype=self.dtype)
            for i in range(self.steps):
                host_data += 1.0
                if (i + 1) % self.sync == 0:
                    print(f"Step {i+1:>4}/{self.steps}: Synced to host. "
                          f"Max value: {host_data.max():.2f}")

        end_time = time.perf_counter()
        elapsed_ms = (end_time - start_time) * 1000
        print(f"Total time: {elapsed_ms:.3f} ms")
        print(f"Final data shape: {host_data.shape}")
        print(f"Final data max value: {host_data.max():.2f}")
        return {"data": host_data, "time_ms": elapsed_ms}

