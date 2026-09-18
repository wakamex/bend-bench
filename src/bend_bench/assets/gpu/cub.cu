// CUB library calls over the same deterministic U32 inputs as the Bend ports.
#include <cub/device/device_radix_sort.cuh>
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

#define CUDA(call) do { cudaError_t e = (call); if(e != cudaSuccess) { fprintf(stderr,"%s: %s\n",#call,cudaGetErrorString(e)); return 2; } } while(0)

__host__ __device__ uint32_t key(uint32_t i) {
  uint32_t x=(i+1u)*2654435761u;
  x^=x<<13; x^=x>>17; x^=x<<5;
  return x;
}
struct Key {
  __host__ __device__ uint32_t operator()(uint32_t i) const { return key(i); }
};
struct Stat { uint32_t mix, bad; };
struct Plus {
  __host__ __device__ Stat operator()(Stat a, Stat b) const { return {a.mix+b.mix,a.bad+b.bad}; }
};
__constant__ uint32_t powers[32];
struct Summarize {
  const uint32_t *sorted; uint32_t n, depth;
  __device__ Stat operator()(uint32_t i) const {
    return {sorted[i]*powers[depth-__popc(i)], uint32_t(i+1<n && sorted[i]>sorted[i+1])};
  }
};
__global__ void generate(uint32_t *a, uint32_t n) {
  uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;
  if(i<n) a[i]=key(i);
}

int main(int argc,char **argv) {
  if(argc<3) return 2;
  bool sorting=strcmp(argv[1],"sort")==0;
  unsigned depth=unsigned(atoi(argv[2]));
  if(depth>26 || (!sorting && strcmp(argv[1],"reduce"))) return 2;
  uint32_t n=1u<<depth;
  uint32_t *input=nullptr,*sorted=nullptr,*sum=nullptr;
  Stat *stat=nullptr;
  void *temp=nullptr; size_t sort_bytes=0,reduce_bytes=0;
  thrust::counting_iterator<uint32_t> indices(0);
  auto keys=thrust::make_transform_iterator(indices,Key{});
  CUDA(cudaMalloc(&sum,sizeof(uint32_t)));
  if(sorting) {
    CUDA(cudaMalloc(&input,n*sizeof(uint32_t)));
    CUDA(cudaMalloc(&sorted,n*sizeof(uint32_t)));
    CUDA(cudaMalloc(&stat,sizeof(Stat)));
    CUDA(cub::DeviceRadixSort::SortKeys(nullptr,sort_bytes,input,sorted,n));
    auto stats=thrust::make_transform_iterator(indices,Summarize{sorted,n,depth});
    CUDA(cub::DeviceReduce::Reduce(nullptr,reduce_bytes,stats,stat,n,Plus{},Stat{0,0}));
    uint32_t p[32]; p[0]=1; for(unsigned i=1;i<32;i++) p[i]=p[i-1]*2654435761u;
    CUDA(cudaMemcpyToSymbol(powers,p,sizeof(p)));
  } else {
    CUDA(cub::DeviceReduce::Sum(nullptr,reduce_bytes,keys,sum,n));
  }
  CUDA(cudaMalloc(&temp,std::max(sort_bytes,reduce_bytes)));
  cudaEvent_t begin,end; CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end));
  CUDA(cudaEventRecord(begin));
  if(sorting) {
    generate<<<(n+255)/256,256>>>(input,n);
    CUDA(cudaGetLastError());
    CUDA(cub::DeviceRadixSort::SortKeys(temp,sort_bytes,input,sorted,n));
    auto stats=thrust::make_transform_iterator(indices,Summarize{sorted,n,depth});
    CUDA(cub::DeviceReduce::Reduce(temp,reduce_bytes,stats,stat,n,Plus{},Stat{0,0}));
  } else {
    CUDA(cub::DeviceReduce::Sum(temp,reduce_bytes,keys,sum,n));
  }
  CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end));
  float ms; CUDA(cudaEventElapsedTime(&ms,begin,end));
  fprintf(stderr,"EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n",ms/1000.0);
  uint32_t result=0;
  if(sorting) {
    Stat h; uint32_t lo,hi;
    CUDA(cudaMemcpy(&h,stat,sizeof h,cudaMemcpyDeviceToHost));
    CUDA(cudaMemcpy(&lo,sorted,sizeof lo,cudaMemcpyDeviceToHost));
    CUDA(cudaMemcpy(&hi,sorted+n-1,sizeof hi,cudaMemcpyDeviceToHost));
    if(h.bad) return 3;
    result=((h.mix*2654435761u)^(hi+lo*340573321u))+2246822519u;
    if(argc>3 && !strcmp(argv[3],"verify")) {
      std::vector<uint32_t> actual(n),expected(n);
      CUDA(cudaMemcpy(actual.data(),sorted,n*sizeof(uint32_t),cudaMemcpyDeviceToHost));
      for(uint32_t i=0;i<n;i++) expected[i]=key(i);
      std::sort(expected.begin(),expected.end());
      if(actual!=expected) return 4;
      fprintf(stderr,"FULL_OUTPUT_VERIFIED=%u\n",n);
    }
  } else CUDA(cudaMemcpy(&result,sum,sizeof result,cudaMemcpyDeviceToHost));
  printf("%u\n",result);
  CUDA(cudaFree(temp)); CUDA(cudaFree(input)); CUDA(cudaFree(sorted)); CUDA(cudaFree(stat)); CUDA(cudaFree(sum));
  CUDA(cudaEventDestroy(begin)); CUDA(cudaEventDestroy(end));
}
