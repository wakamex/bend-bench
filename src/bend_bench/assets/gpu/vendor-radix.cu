// Published tree-radix contract: sort, deduplicate, check and summarize.
#include <cub/device/device_radix_sort.cuh>
#include <cub/device/device_select.cuh>
#include <cub/device/device_reduce.cuh>
#include <thrust/iterator/counting_iterator.h>
#include <thrust/iterator/transform_iterator.h>
#include <cuda_runtime.h>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#define CUDA(call) do { auto e=(call); if(e!=cudaSuccess) { fprintf(stderr,"%s: %s\n",#call,cudaGetErrorString(e)); return 2; } } while(0)
__host__ __device__ uint32_t key(uint32_t i) {
  uint32_t x=(i+1u)*2654435761u;
  x^=x<<13; x^=x>>17; x^=x<<5;
  return x & 16777215u;
}
__global__ void generate(uint32_t *a, unsigned n) {
  unsigned i=blockIdx.x*blockDim.x+threadIdx.x;
  if(i<n) a[i]=key(i);
}
struct Stat { uint32_t sum,bad; };
struct Plus {
  __host__ __device__ Stat operator()(Stat a,Stat b) const { return {a.sum+b.sum,a.bad+b.bad}; }
};
struct Summarize {
  const uint32_t *a; const int *count;
  __device__ Stat operator()(unsigned i) const {
    return i<unsigned(*count) ? Stat{a[i],uint32_t(i+1<unsigned(*count) && a[i]>=a[i+1])} : Stat{0,0};
  }
};
int main(int argc,char **argv) {
  bool verify=argc>1 && !strcmp(argv[1],"verify");
  if(argc>3 || (argc>1 && !verify)) return 2;
  unsigned depth=22;
  if(argc==3) {
    char *end=nullptr; unsigned long value=strtoul(argv[2],&end,10);
    if(!*argv[2] || *end || value>22) return 2;
    depth=unsigned(value);
  }
  unsigned n=1u<<depth;
  uint32_t *input,*sorted,*unique; int *count; Stat *stat;
  CUDA(cudaMalloc(&input,n*4)); CUDA(cudaMalloc(&sorted,n*4)); CUDA(cudaMalloc(&unique,n*4));
  CUDA(cudaMalloc(&count,sizeof(int))); CUDA(cudaMalloc(&stat,sizeof(Stat)));
  size_t sort_bytes=0,unique_bytes=0,reduce_bytes=0;
  auto values=thrust::make_transform_iterator(thrust::counting_iterator<unsigned>(0),Summarize{unique,count});
  CUDA(cub::DeviceRadixSort::SortKeys(nullptr,sort_bytes,input,sorted,n,0,24));
  CUDA(cub::DeviceSelect::Unique(nullptr,unique_bytes,sorted,unique,count,n));
  CUDA(cub::DeviceReduce::Reduce(nullptr,reduce_bytes,values,stat,n,Plus{},Stat{0,0}));
  void *temp; CUDA(cudaMalloc(&temp,std::max({sort_bytes,unique_bytes,reduce_bytes})));
  cudaEvent_t begin,end; CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end));
  CUDA(cudaEventRecord(begin));
  generate<<<(n+255)/256,256>>>(input,n); CUDA(cudaGetLastError());
  CUDA(cub::DeviceRadixSort::SortKeys(temp,sort_bytes,input,sorted,n,0,24));
  CUDA(cub::DeviceSelect::Unique(temp,unique_bytes,sorted,unique,count,n));
  CUDA(cub::DeviceReduce::Reduce(temp,reduce_bytes,values,stat,n,Plus{},Stat{0,0}));
  CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end));
  float ms; CUDA(cudaEventElapsedTime(&ms,begin,end));
  fprintf(stderr,"EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n",ms/1000.0);
  int size; Stat h; uint32_t lo,hi;
  CUDA(cudaMemcpy(&size,count,sizeof size,cudaMemcpyDeviceToHost));
  CUDA(cudaMemcpy(&h,stat,sizeof h,cudaMemcpyDeviceToHost));
  if(size<1 || unsigned(size)>n || h.bad) return 3;
  CUDA(cudaMemcpy(&lo,unique,4,cudaMemcpyDeviceToHost));
  CUDA(cudaMemcpy(&hi,unique+size-1,4,cudaMemcpyDeviceToHost));
  if(verify) {
    std::vector<uint32_t> expected(n),actual(size);
    for(unsigned i=0;i<n;i++) expected[i]=key(i);
    std::sort(expected.begin(),expected.end());
    expected.erase(std::unique(expected.begin(),expected.end()),expected.end());
    CUDA(cudaMemcpy(actual.data(),unique,size*4,cudaMemcpyDeviceToHost));
    if(actual!=expected) return 4;
    fprintf(stderr,"FULL_OUTPUT_VERIFIED=%d\n",size);
  }
  printf("%u\n",((h.sum+uint32_t(size)*2654435761u)^(hi+lo*340573321u))+2246822519u);
  CUDA(cudaFree(temp)); CUDA(cudaFree(input)); CUDA(cudaFree(sorted)); CUDA(cudaFree(unique));
  CUDA(cudaFree(count)); CUDA(cudaFree(stat)); CUDA(cudaEventDestroy(begin)); CUDA(cudaEventDestroy(end));
}
