"""PyTorch baselines for bend-ml's bench/ products, printing the same value as the Bend programs.

  products_torch.py mm_array THREADS          128,001 dot products of 784 elements (0.5 x 0.25), as
                                               ten 100x784 by 784x128 products and one dot
  products_torch.py mv THREADS KN MN REPS      REPS + 1 products of a KN vector with an MN x KN matrix,
                                               summing each product's maximum

The timed region (EVAL_COMPUTE_SECONDS on stderr) is the products, after the operands exist.
"""
import sys
import time

import torch


def main():
    kind, threads = sys.argv[1], int(sys.argv[2])
    torch.set_num_threads(threads)
    if kind == "mm_array":
        a, b = torch.full((100, 784), 0.5), torch.full((784, 128), 0.25)
        x, y = torch.full((784,), 0.5), torch.full((784,), 0.25)
        t0 = time.perf_counter()
        total = torch.zeros(())
        for _ in range(10):
            total += (a @ b).sum()
        total += torch.dot(x, y)
    else:
        kn, mn, reps = map(int, sys.argv[3:6])
        x = (torch.arange(kn) % 13).float().flip(0) / 10
        w = ((torch.arange(kn * mn) % 13).float().flip(0) / 10).reshape(mn, kn)
        t0 = time.perf_counter()
        total = torch.zeros(())
        for _ in range(reps + 1):
            total += (w @ x).max()
    seconds = time.perf_counter() - t0
    print(f"EVAL_COMPUTE_SECONDS={seconds:.6f}", file=sys.stderr)
    print(float(total))


if __name__ == "__main__":
    main()
