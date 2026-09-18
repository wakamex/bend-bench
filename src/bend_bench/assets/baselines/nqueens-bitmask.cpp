#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>

// Enumerate every solution, without symmetry reduction, like the Bend port.
static uint64_t serial(uint32_t full, uint32_t cols, uint32_t left, uint32_t right) {
  if (cols == full) return 1;
  uint64_t count = 0;
  uint32_t available = full & ~(cols | left | right);
  while (available) {
    uint32_t bit = available & -available;
    available ^= bit;
    count += serial(full, cols | bit, (left | bit) << 1, (right | bit) >> 1);
  }
  return count;
}

static uint64_t tasks(uint32_t full, uint32_t cols, uint32_t left,
                      uint32_t right, unsigned levels) {
  if (!levels || cols == full) return serial(full, cols, left, right);
  uint64_t children[16] = {};
  unsigned n = 0;
  uint32_t available = full & ~(cols | left | right);
  while (available) {
    uint32_t bit = available & -available;
    available ^= bit;
    unsigned index = n++;
#pragma omp task shared(children) firstprivate(index, bit, full, cols, left, right, levels)
    children[index] = tasks(full, cols | bit, (left | bit) << 1,
                            (right | bit) >> 1, levels - 1);
  }
#pragma omp taskwait
  uint64_t count = 0;
  for (unsigned i = 0; i < n; ++i) count += children[i];
  return count;
}

int main(int argc, char **argv) {
  if (argc != 3) return 2;
  int size = std::atoi(argv[1]), levels = std::atoi(argv[2]);
  if (size < 1 || size > 16 || levels < 0 || levels > 5) return 2;
  uint32_t full = (1u << size) - 1;
  uint64_t count = 0;
  auto start = std::chrono::steady_clock::now();
  if (!levels) count = serial(full, 0, 0, 0);
  else {
#pragma omp parallel
    {
#pragma omp single
      count = tasks(full, 0, 0, 0, levels);
    }
  }
  double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
  std::fprintf(stderr, "EVAL_COMPUTE_SECONDS=%.9f\n", seconds);
  std::printf("%llu\n", (unsigned long long)count);
}
