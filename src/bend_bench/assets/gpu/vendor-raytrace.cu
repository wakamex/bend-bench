// Bend benchmark adaptation, Copyright 2026 HigherOrderCO, Apache-2.0.
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
#include "vendor-raytrace-device.cuh"
#define CUDA(call) do { auto e=(call); if(e!=cudaSuccess) { fprintf(stderr,"%s: %s\n",#call,cudaGetErrorString(e)); return 2; } } while(0)
__global__ void render(uint32_t w,uint32_t h,uint32_t *sum,uint32_t *values) {
  uint32_t total=0;
  for(uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;i<w*h;i+=gridDim.x*blockDim.x) {
    uint32_t v=gpu::pixel_render(i%w,i/w,float(w/2),float(h/2)); total+=v;
    if(values) values[i]=v;
  }
  for(int offset=16;offset;offset/=2) total+=__shfl_down_sync(0xffffffff,total,offset);
  if(!(threadIdx.x&31)) atomicAdd(sum,total);
}
int main(int argc,char **argv) {
  bool verify=argc>1 && !strcmp(argv[1],"verify");
  if(argc>4 || (argc>1 && !verify)) return 2;
  uint32_t depth=12,width=6000;
  for(int i=2;i<argc;i++) { char *end=nullptr; unsigned long v=strtoul(argv[i],&end,10);
    if(!*argv[i] || *end || (i==2?v>12:v<2 || v>6000)) return 2; if(i==2) depth=v; else width=v;
  }
  uint32_t height=1u<<depth,n=width*height,*sum,*values=nullptr;
  CUDA(cudaMalloc(&sum,4)); if(verify) { CUDA(cudaMalloc(&values,size_t(n)*4)); }
  cudaEvent_t begin,end; CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end)); CUDA(cudaEventRecord(begin));
  CUDA(cudaMemset(sum,0,4)); render<<<(n+127)/128,128>>>(width,height,sum,values); CUDA(cudaGetLastError());
  CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end));
  float ms; CUDA(cudaEventElapsedTime(&ms,begin,end)); fprintf(stderr,"EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n",ms/1000.0);
  uint32_t result; CUDA(cudaMemcpy(&result,sum,4,cudaMemcpyDeviceToHost));
  if(verify) {
    std::vector<uint32_t> actual(n); CUDA(cudaMemcpy(actual.data(),values,size_t(n)*4,cudaMemcpyDeviceToHost));
    uint32_t expected=0;
    for(uint32_t i=0;i<n;i++) {
      uint32_t v=pixel_render(i%width,i/width,float(width/2),float(height/2));
      if(actual[i]!=v) { fprintf(stderr,"Pixel mismatch %u: %u != %u\n",i,actual[i],v); return 3; } expected+=v;
    }
    if(result!=expected) return 4;
    fprintf(stderr,"FULL_OUTPUT_VERIFIED=%u\n",n); CUDA(cudaFree(values));
  }
  printf("%u\n",result); CUDA(cudaFree(sum)); CUDA(cudaEventDestroy(begin)); CUDA(cudaEventDestroy(end));
}
