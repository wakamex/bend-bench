// Generate and sum the same U32 sequence as Bend and CUB, without an input array.
#include <cstdint>
#include <cstdio>
#include <cstdlib>

int main(int argc, char **argv) {
  if (argc != 2) return 2;
  char *end;
  uint64_t count = strtoull(argv[1], &end, 10);
  if (*end || count < 1 || count > (1ull << 31)) return 2;
  uint32_t sum = 0;
#ifdef _OPENMP
#pragma omp parallel for simd schedule(static) reduction(+:sum)
#endif
  for (uint64_t i = 0; i < count; ++i) {
    uint32_t x = (uint32_t(i) + 1u) * 2654435761u;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    sum += x;
  }
  printf("%u\n", sum);
}
