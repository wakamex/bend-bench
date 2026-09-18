// Wrapper around unchanged GAP DOBFS. Parent validation and distance conversion
// are included in process wall time, excluded from the algorithm timer.
#define main gap_original_main
#include "bfs.cc"
#undef main
#include <chrono>
int main(int argc, char **argv) {
  CLApp cli(argc, argv, "Bend comparison: GAP BFS");
  if (!cli.ParseArgs())
    return 2;
  Builder b(cli);
  Graph g = b.MakeGraph();
  auto start = std::chrono::steady_clock::now();
  auto parents = DOBFS(g, 0, false);
  fprintf(
      stderr, "EVAL_COMPUTE_SECONDS=%.9f\n",
      std::chrono::duration<double>(std::chrono::steady_clock::now() - start)
          .count());
  if (!BFSVerifier(g, 0, parents))
    return 3;
  // GAP emits setup statistics to stdout; a prefixed full vector is parsed by
  // the harness, with every vertex checked against an independent queue BFS.
  printf("BEGIN_DISTANCES\n");
  for (NodeID v : g.vertices()) {
    uint32_t d = 0;
    NodeID p = v;
    if (parents[p] < 0)
      d = UINT32_MAX;
    else
      while (p != 0) {
        p = parents[p];
        if (p < 0 || ++d > g.num_nodes())
          return 4;
      }
    printf("%u\n", d);
  }
}
