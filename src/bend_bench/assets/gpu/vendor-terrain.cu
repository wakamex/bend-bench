// Bend benchmark adaptation, Copyright 2026 HigherOrderCO, Apache-2.0.
// Anti-diagonals preserve row-major Gauss-Seidel dependencies within each tile.
#include <cuda_runtime.h>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#define main upstream_main
#include "main.c"
#undef main
#include "vendor-terrain-device.cuh"
#define CUDA(call) do { auto e=(call); if(e!=cudaSuccess) { fprintf(stderr,"%s: %s\n",#call,cudaGetErrorString(e)); return 2; } } while(0)
__device__ uint32_t power(uint32_t n) { uint32_t r=1,a=2654435761u; while(n) { if(n&1) r*=a; a*=a; n>>=1; } return r; }
__global__ void tiles(uint32_t first,uint32_t passes,uint32_t *out,uint32_t *heights) {
  __shared__ uint32_t h[4096],hist[64],sums[2];
  uint32_t x=threadIdx.x,t=first+blockIdx.x,ox=(t&255)<<6,oz=(t>>8)<<6;
  hist[x]=0;
  for(uint32_t y=0;y<64;y++) h[y*64+x]=gpu::terrain_ground((ox+x)<<6,(oz+y)<<6);
  __syncthreads();
  for(uint32_t p=passes;p;p--) {
    for(int diagonal=0;diagonal<127;diagonal++) {
      int y=diagonal-int(x);
      if(y>=0 && y<64) gpu::erode_cell(uint32_t(y)*64+x,p,h);
      __syncthreads();
    }
  }
  // The additive height fold can be expanded into an exact wrapping-U32 sum.
  uint32_t weighted=0,weight=power(x),stride=power(64);
  for(int i=4095-int(x);i>=0;i-=64) {
    uint32_t v=h[i]; atomicAdd(hist+((v>>2)&63),1u);
    weighted+=v*uint32_t(i+1)*weight; weight*=stride;
    if(heights) heights[size_t(blockIdx.x)*4096+i]=v;
  }
  for(int offset=16;offset;offset/=2) weighted+=__shfl_down_sync(0xffffffff,weighted,offset);
  if(!(x&31)) sums[x/32]=weighted;
  __syncthreads();
  if(x==0) {
    uint32_t result=(t+1)*power(4096)+sums[0]+sums[1];
    for(uint32_t k=0;k<64;k++) result=(result*2654435761u)^(hist[k]*(k+3));
    out[blockIdx.x]=result;
  }
}
int main(int argc,char **argv) {
  bool verify=argc>1 && !strcmp(argv[1],"verify");
  if(argc>4 || (argc>1 && !verify)) return 2;
  uint32_t depth=16,passes=5;
  for(int i=2;i<argc;i++) { char *end=nullptr; unsigned long v=strtoul(argv[i],&end,10);
    if(!*argv[i] || *end || v>(i==2?16u:5u)) return 2; if(i==2) depth=v; else passes=v;
  }
  uint32_t n=1u<<depth,batch=verify && n>512?512:n,*out,*heights=nullptr,result=0;
  CUDA(cudaMalloc(&out,batch*4)); if(verify) { CUDA(cudaMalloc(&heights,size_t(batch)*4096*4)); }
  std::vector<uint32_t> values(batch),actual(verify?size_t(batch)*4096:0);
  cudaEvent_t begin,end; CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end)); double total_ms=0;
  for(uint32_t first=0;first<n;first+=batch) {
    uint32_t count=n-first<batch?n-first:batch;
    CUDA(cudaEventRecord(begin)); tiles<<<count,64>>>(first,passes,out,heights); CUDA(cudaGetLastError());
    CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end)); float ms; CUDA(cudaEventElapsedTime(&ms,begin,end)); total_ms+=ms;
    CUDA(cudaMemcpy(values.data(),out,count*4,cudaMemcpyDeviceToHost));
    if(verify) {
      CUDA(cudaMemcpy(actual.data(),heights,size_t(count)*4096*4,cudaMemcpyDeviceToHost));
      for(uint32_t i=0;i<count;i++) {
        uint32_t t=first+i,h[4096],hist[64]={}; tile_fill((t&255)<<6,(t>>8)<<6,h); tile_smooth(passes,h);
        if(memcmp(h,actual.data()+size_t(i)*4096,sizeof h) || tile_hist(h,hist,t+1)!=values[i]) { fprintf(stderr,"Tile mismatch %u\n",t); return 3; }
      }
    }
    for(uint32_t i=0;i<count;i++) result+=values[i];
  }
  fprintf(stderr,"EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n",total_ms/1000);
  if(verify) { fprintf(stderr,"FULL_OUTPUT_VERIFIED=%llu\n",(unsigned long long)n*4096); CUDA(cudaFree(heights)); }
  printf("%u\n",result); CUDA(cudaFree(out)); CUDA(cudaEventDestroy(begin)); CUDA(cudaEventDestroy(end));
}
