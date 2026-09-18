#include <cstdio>
#include <gunrock/algorithms/bfs.hxx>
#include <gunrock/io/matrix_market.hxx>
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  using namespace gunrock;
  io::matrix_market_t<int, int, float> reader;
  auto [properties, coo] = reader.load(argv[1]);
  format::csr_t<memory::memory_space_t::device, int, int, float> csr;
  csr.from_coo(coo);
  auto graph = graph::build<memory::memory_space_t::device>(properties, csr);
  auto context = std::make_shared<gcuda::multi_context_t>(0);
  thrust::device_vector<int> distances(graph.get_number_of_vertices());
  thrust::device_vector<int> predecessors(graph.get_number_of_vertices());
  int source = 0;
  float ms = bfs::run(graph, source, distances.data().get(),
                      predecessors.data().get(), context);
  context->get_context(0)->synchronize();
  fprintf(stderr, "EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n", ms / 1000.0);
  thrust::host_vector<int> host = distances;
  printf("BEGIN_DISTANCES\n");
  for (int v : host)
    printf("%u\n", v == 2147483647 ? UINT32_MAX : unsigned(v));
}
