// Bend benchmark adaptation, Copyright 2026 HigherOrderCO, Apache-2.0.
// Fixed-point escape counts plus per-bucket weighted sums avoid a second render.
#include <cuda_runtime.h>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#define main upstream_main
#include "main.c"
#undef main
#define CUDA(call) do { auto e=(call); if(e!=cudaSuccess) { fprintf(stderr,"%s: %s\n",#call,cudaGetErrorString(e)); return 2; } } while(0)

__device__ uint32_t escape_count(uint32_t id, uint32_t steps) {
  uint32_t cr=(id&4095)*768/4096-512, ci=(id>>12)*768/4096-384;
  uint32_t zr=0,zi=0;
  #pragma unroll 4
  for(uint32_t i=0;i<steps;i++) {
    uint32_t r2=uint32_t(int32_t(zr*zr)>>8),i2=uint32_t(int32_t(zi*zi)>>8);
    if(r2+i2>1024) return i;
    uint32_t next=r2-i2+cr;
    zi=uint32_t(int32_t(2u*zr*zi)>>8)+ci;
    zr=next;
  }
  return steps;
}
// One thread per pixel. Each block sums its pixels in shared memory and adds its 17 sums to the
// global ones (integer sums, so the order doesn't change them).
__global__ void render(uint32_t n,uint32_t steps,uint32_t *sums,uint32_t *pixels) {
  __shared__ uint32_t block[17];
  if(threadIdx.x<17) block[threadIdx.x]=0;
  __syncthreads();
  uint32_t total=0;
  for(uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;i<n;i+=gridDim.x*blockDim.x) {
    uint32_t it=escape_count(i,steps),bucket=min(it*8/steps,7u);
    atomicAdd(block+bucket,1u);
    atomicAdd(block+8+bucket,i*2654435761u+1u);
    total+=it;
    if(pixels) pixels[i]=it;
  }
  atomicAdd(block+16,total);
  __syncthreads();
  if(threadIdx.x<17) atomicAdd(sums+threadIdx.x,block[threadIdx.x]);
}
__global__ void finish(const uint32_t *sums,uint32_t n,uint32_t *out) {
  uint32_t cumulative=0,mix=0,result=sums[16];
  for(int k=0;k<8;k++) {
    cumulative+=sums[k];
    uint32_t color=cumulative*255u/n;
    mix=mix*2654435761u+color;
    result+=color*sums[8+k];
  }
  for(int k=0;k<17;k++) out[k]=sums[k];
  out[17]=mix*2654435761u+result;
}
int main(int argc,char **argv) {
  bool verify=argc>1 && !strcmp(argv[1],"verify");
  if(argc>4 || (argc>1 && !verify)) return 2;
  uint32_t depth=18,steps=51;
  for(int i=2;i<argc;i++) {
    char *end=nullptr; unsigned long v=strtoul(argv[i],&end,10);
    if(!*argv[i] || *end || (i==2 ? v>18 : v<1 || v>51)) return 2;
    if(i==2) depth=v; else steps=v;
  }
  uint32_t n=64u<<depth,groups=(n+255)/256;
  uint32_t *sums,*out,*pixels=nullptr;
  CUDA(cudaMalloc(&sums,17*4)); CUDA(cudaMalloc(&out,18*4));
  if(verify) { CUDA(cudaMalloc(&pixels,size_t(n)*4)); }
  cudaEvent_t begin,end; CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end));
  CUDA(cudaEventRecord(begin));
  CUDA(cudaMemsetAsync(sums,0,17*4));
  render<<<groups,256>>>(n,steps,sums,pixels); CUDA(cudaGetLastError());
  finish<<<1,1>>>(sums,n,out); CUDA(cudaGetLastError());
  CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end));
  float ms; CUDA(cudaEventElapsedTime(&ms,begin,end));
  fprintf(stderr,"EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n",ms/1000.0);
  uint32_t actual[18]; CUDA(cudaMemcpy(actual,out,sizeof actual,cudaMemcpyDeviceToHost));
  if(verify) {
    std::vector<uint32_t> values(n); uint32_t expected[17]={};
    CUDA(cudaMemcpy(values.data(),pixels,size_t(n)*4,cudaMemcpyDeviceToHost));
    for(uint32_t i=0;i<n;i++) {
      uint32_t it=pix(i,steps);
      if(values[i]!=it) { fprintf(stderr,"Pixel mismatch at %u\n",i); return 3; }
      uint32_t b=bkt(it,steps);
      expected[b]++; expected[8+b]+=i*2654435761u+1u; expected[16]+=it;
    }
    if(memcmp(expected,actual,sizeof expected) || actual[17]!=rend(depth,steps)) return 4;
    fprintf(stderr,"FULL_OUTPUT_VERIFIED=%u\n",n);
    CUDA(cudaFree(pixels));
  }
  printf("%u\n",actual[17]);
  CUDA(cudaFree(sums)); CUDA(cudaFree(out)); CUDA(cudaEventDestroy(begin)); CUDA(cudaEventDestroy(end));
}
