// Bend benchmark adaptation, Copyright 2026 HigherOrderCO, Apache-2.0.
// Compile the exact reference arithmetic for both host and device.
#include <cuda_runtime.h>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <vector>
#define main upstream_main
#include "main.c"
#undef main
#include "vendor-nbody-device.cuh"
#define CUDA(call) do { auto e=(call); if(e!=cudaSuccess) { fprintf(stderr,"%s: %s\n",#call,cudaGetErrorString(e)); return 2; } } while(0)
__global__ void systems(uint32_t n,uint32_t steps,uint32_t *stats,uint2 *values) {
  __shared__ uint32_t local[9];
  if(threadIdx.x<9) local[threadIdx.x]=0;
  __syncthreads();
  uint32_t total=0;
  for(uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;i<n;i+=gridDim.x*blockDim.x) {
    gpu::V2 v=gpu::sim(i,steps);
    if(values) values[i]=make_uint2(v.cs,v.eb);
    atomicAdd(local+v.eb,1u); total+=v.cs*(i*2654435761u+1u);
  }
  for(int offset=16;offset;offset/=2) total+=__shfl_down_sync(0xffffffff,total,offset);
  if(!(threadIdx.x&31)) atomicAdd(local+8,total);
  __syncthreads();
  if(threadIdx.x<9) atomicAdd(stats+threadIdx.x,local[threadIdx.x]);
}
int main(int argc,char **argv) {
  bool verify=argc>1 && !strcmp(argv[1],"verify");
  if(argc>4 || (argc>1 && !verify)) return 2;
  uint32_t depth=17,steps=300;
  for(int i=2;i<argc;i++) { char *end=nullptr; unsigned long v=strtoul(argv[i],&end,10);
    if(!*argv[i] || *end || v>(i==2?17u:300u)) return 2; if(i==2) depth=v; else steps=v;
  }
  uint32_t n=8u<<depth,*stats; uint2 *values=nullptr;
  CUDA(cudaMalloc(&stats,9*4)); if(verify) { CUDA(cudaMalloc(&values,size_t(n)*sizeof(uint2))); }
  cudaEvent_t begin,end; CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end)); CUDA(cudaEventRecord(begin));
  CUDA(cudaMemset(stats,0,9*4)); systems<<<(n+127)/128,128>>>(n,steps,stats,values); CUDA(cudaGetLastError());
  CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end));
  float ms; CUDA(cudaEventElapsedTime(&ms,begin,end)); fprintf(stderr,"EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n",ms/1000.0);
  uint32_t actual[9]; CUDA(cudaMemcpy(actual,stats,sizeof actual,cudaMemcpyDeviceToHost));
  if(verify) {
    std::vector<uint2> outputs(n); CUDA(cudaMemcpy(outputs.data(),values,size_t(n)*sizeof(uint2),cudaMemcpyDeviceToHost));
    uint32_t expected[9]={};
    for(uint32_t i=0;i<n;i++) {
      V2 v=sim(i,steps);
      if(outputs[i].x!=v.cs || outputs[i].y!=v.eb) { fprintf(stderr,"System mismatch %u: %u/%u != %u/%u\n",i,outputs[i].x,outputs[i].y,v.cs,v.eb); return 3; }
      expected[v.eb]++; expected[8]+=v.cs*(i*2654435761u+1u);
    }
    if(memcmp(expected,actual,sizeof expected)) return 4;
    fprintf(stderr,"FULL_OUTPUT_VERIFIED=%u\n",n); CUDA(cudaFree(values));
  }
  uint32_t result=0; for(uint32_t v:actual) result=result*2654435761u+v;
  printf("%u\n",result); CUDA(cudaFree(stats)); CUDA(cudaEventDestroy(begin)); CUDA(cudaEventDestroy(end));
}
