// Published sequence generator and independent rolling-row CPU oracle.
#define main vendor_main
#include "main.c"
#undef main
constexpr unsigned sequence_length=N;
#undef N
#include <nvtext/edit_distance.hpp>
#include <cudf/column/column_view.hpp>
#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <vector>

constexpr unsigned N=sequence_length;

#define CUDA(call) do { auto e=(call); if(e!=cudaSuccess) { fprintf(stderr,"%s: %s\n",#call,cudaGetErrorString(e)); return 2; } } while(0)
int run(int argc,char **argv) {
  bool verify=argc>1 && !strcmp(argv[1],"verify");
  if(argc>3 || (argc>1 && !verify)) return 2;
  unsigned depth=15;
  if(argc==3) {
    char *end=nullptr; unsigned long value=strtoul(argv[2],&end,10);
    if(!*argv[2] || *end || value>15) return 2;
    depth=unsigned(value);
  }
  unsigned count=1u<<depth;
  std::vector<uint8_t> a(count*N),b(count*N);
  std::vector<int32_t> offsets(count+1);
  for(unsigned i=0;i<count;i++) {
    uint32_t seed=(i+1u)*2654435761u;
    seq_gen(seed,a.data()+i*N); seq_gen(seed*340573321u,b.data()+i*N);
    for(unsigned j=0;j<N;j++) { a[i*N+j]+='A'; b[i*N+j]+='A'; }
    offsets[i]=int32_t(i*N);
  }
  offsets[count]=int32_t(count*N);
  char *da,*db; int32_t *d_offsets;
  CUDA(cudaMalloc(&da,a.size())); CUDA(cudaMalloc(&db,b.size()));
  CUDA(cudaMalloc(&d_offsets,offsets.size()*sizeof(int32_t)));
  cudaEvent_t begin,end; CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end));
  CUDA(cudaEventRecord(begin));
  CUDA(cudaMemcpy(da,a.data(),a.size(),cudaMemcpyHostToDevice));
  CUDA(cudaMemcpy(db,b.data(),b.size(),cudaMemcpyHostToDevice));
  CUDA(cudaMemcpy(d_offsets,offsets.data(),offsets.size()*sizeof(int32_t),cudaMemcpyHostToDevice));
  cudf::column_view offset_view(cudf::data_type{cudf::type_id::INT32},count+1,d_offsets,nullptr,0);
  cudf::column_view a_view(cudf::data_type{cudf::type_id::STRING},count,da,nullptr,0,0,{offset_view});
  cudf::column_view b_view(cudf::data_type{cudf::type_id::STRING},count,db,nullptr,0,0,{offset_view});
  rmm::cuda_stream_view stream{cudaStream_t{0}};
  auto distances=nvtext::edit_distance(cudf::strings_column_view(a_view),cudf::strings_column_view(b_view),stream);
  if(distances->type()!=cudf::data_type{cudf::type_id::INT32} || distances->size()!=int(count)) return 3;
  std::vector<int32_t> actual(count);
  CUDA(cudaMemcpy(actual.data(),distances->view().data<int32_t>(),count*sizeof(int32_t),cudaMemcpyDeviceToHost));
  CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end));
  float ms; CUDA(cudaEventElapsedTime(&ms,begin,end));
  fprintf(stderr,"EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n",ms/1000.0);
  uint32_t result=0;
  for(unsigned i=0;i<count;i++) {
    if(actual[i]<0 || actual[i]>int(N)) return 3;
    if(verify && uint32_t(actual[i])!=edit_dist(a.data()+i*N,b.data()+i*N)) return 4;
    result+=(uint32_t(actual[i])*2654435761u)^(i+1u);
  }
  if(verify) fprintf(stderr,"FULL_OUTPUT_VERIFIED=%u\n",count);
  printf("%u\n",result);
  distances.reset();
  CUDA(cudaFree(da)); CUDA(cudaFree(db)); CUDA(cudaFree(d_offsets));
  CUDA(cudaEventDestroy(begin)); CUDA(cudaEventDestroy(end));
  return 0;
}
int main(int argc,char **argv) {
  try { return run(argc,argv); }
  catch(const std::exception &e) { fprintf(stderr,"cuDF: %s\n",e.what()); return 2; }
}
