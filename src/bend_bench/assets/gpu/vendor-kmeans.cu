// Bend benchmark adaptation, Copyright 2026 HigherOrderCO, Apache-2.0.
#include <cuda_runtime.h>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#define realloc(p,n) ((St*)std::realloc(p,n))
#define main upstream_main
#include "main.c"
#undef main
#undef realloc
#define CUDA(call) do { auto e=(call); if(e!=cudaSuccess) { fprintf(stderr,"%s: %s\n",#call,cudaGetErrorString(e)); return 2; } } while(0)
__device__ uint32_t rng(uint32_t x) { x^=x<<13; x^=x>>17; return x^(x<<5); }
__global__ void initialize(uint32_t *points,uint32_t n,uint32_t *centers,uint32_t starts) {
  uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;
  if(i<n) { uint32_t h=rng((i+1)*2654435761u); points[i]=(h&1023)|((h>>16)&1023)<<16; }
  if(i<starts*8) { uint32_t h=rng(12346+i); centers[i]=(h&1023)|((h>>16)&1023)<<16; }
}
__global__ void assign(const uint32_t *points,uint32_t n,const uint32_t *centers,uint32_t *partials) {
  __shared__ uint32_t c[8],sums[24];
  if(threadIdx.x<8) c[threadIdx.x]=centers[blockIdx.y*8+threadIdx.x];
  if(threadIdx.x<24) sums[threadIdx.x]=0;
  __syncthreads();
  uint32_t local[24]={};
  for(uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;i<n;i+=gridDim.x*blockDim.x) {
    uint32_t p=points[i],x=p&65535,y=p>>16,best=0xffffffff;
    #pragma unroll
    for(uint32_t k=0;k<8;k++) {
      // Squared wrapping differences equal the original absolute differences here.
      uint32_t dx=x-(c[k]&65535),dy=y-(c[k]>>16);
      best=min(best,((dx*dx+dy*dy)<<3)|k);
    }
    uint32_t k=best&7; local[3*k]+=x; local[3*k+1]+=y; local[3*k+2]++;
  }
  for(int k=0;k<24;k++) {
    uint32_t v=local[k];
    for(int offset=16;offset;offset/=2) v+=__shfl_down_sync(0xffffffff,v,offset);
    if(!(threadIdx.x&31)) atomicAdd(sums+k,v);
  }
  __syncthreads();
  if(threadIdx.x<24) partials[(blockIdx.y*gridDim.x+blockIdx.x)*24+threadIdx.x]=sums[threadIdx.x];
}
__global__ void update(uint32_t *centers,const uint32_t *partials,uint32_t groups,uint32_t starts,uint32_t *history,uint32_t iter) {
  uint32_t r=blockIdx.x*blockDim.x+threadIdx.x;
  if(r>=starts) return;
  for(uint32_t k=0;k<8;k++) {
    uint32_t x=0,y=0,n=0;
    for(uint32_t g=0;g<groups;g++) { const uint32_t *s=partials+(r*groups+g)*24+3*k; x+=s[0]; y+=s[1]; n+=s[2]; }
    if(n) centers[r*8+k]=x/n|((y/n)<<16);
    if(history) history[(iter*starts+r)*8+k]=centers[r*8+k];
  }
}
int main(int argc,char **argv) {
  bool verify=argc>1 && !strcmp(argv[1],"verify");
  if(argc>4 || (argc>1 && !verify)) return 2;
  uint32_t depth=19,start_depth=6;
  for(int i=2;i<argc;i++) { char *end=nullptr; unsigned long v=strtoul(argv[i],&end,10);
    if(!*argv[i] || *end || (i==2?v<6 || v>19:v>6)) return 2;
    if(i==2) depth=v; else start_depth=v;
  }
  uint32_t n=1u<<depth,starts=1u<<start_depth,groups=(n+255)/256; if(groups>64) groups=64;
  uint32_t *points,*centers,*partials,*history=nullptr;
  CUDA(cudaMalloc(&points,size_t(n)*4)); CUDA(cudaMalloc(&centers,starts*8*4)); CUDA(cudaMalloc(&partials,starts*groups*24*4));
  if(verify) { CUDA(cudaMalloc(&history,20*starts*8*4)); }
  cudaEvent_t begin,end; CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end)); CUDA(cudaEventRecord(begin));
  uint32_t init_count=n>starts*8?n:starts*8;
  initialize<<<(init_count+255)/256,256>>>(points,n,centers,starts); CUDA(cudaGetLastError());
  for(uint32_t it=0;it<20;it++) {
    assign<<<dim3(groups,starts),256>>>(points,n,centers,partials); CUDA(cudaGetLastError());
    update<<<(starts+63)/64,64>>>(centers,partials,groups,starts,history,it); CUDA(cudaGetLastError());
  }
  CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end));
  float ms; CUDA(cudaEventElapsedTime(&ms,begin,end)); fprintf(stderr,"EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n",ms/1000.0);
  std::vector<uint32_t> actual(starts*8); CUDA(cudaMemcpy(actual.data(),centers,actual.size()*4,cudaMemcpyDeviceToHost));
  if(verify) {
    std::vector<uint32_t> trace(20*starts*8),input(n);
    CUDA(cudaMemcpy(trace.data(),history,trace.size()*4,cudaMemcpyDeviceToHost));
    CUDA(cudaMemcpy(input.data(),points,input.size()*4,cudaMemcpyDeviceToHost));
    for(uint32_t i=0;i<n;i++) { uint32_t h=prng((i+1)*2654435761u); if(input[i]!=((h&1023)|((h>>16)&1023)<<16)) return 3; }
    Arena arena={};
    for(uint32_t r=0;r<starts;r++) {
      Cs c={cini(r*8+1),cini(r*8+2),cini(r*8+3),cini(r*8+4),cini(r*8+5),cini(r*8+6),cini(r*8+7),cini(r*8+8)};
      for(uint32_t it=0;it<20;it++) {
        c=step(&arena,depth,c.c0,c.c1,c.c2,c.c3,c.c4,c.c5,c.c6,c.c7);
        uint32_t expected[]={c.c0,c.c1,c.c2,c.c3,c.c4,c.c5,c.c6,c.c7};
        if(memcmp(expected,trace.data()+(it*starts+r)*8,sizeof expected)) { fprintf(stderr,"Centroid mismatch start=%u iteration=%u\n",r,it); return 4; }
        if(it==19 && memcmp(expected,actual.data()+r*8,sizeof expected)) return 5;
      }
    }
    free(arena.at); fprintf(stderr,"FULL_OUTPUT_VERIFIED=%u\n",20*starts*8); CUDA(cudaFree(history));
  }
  uint32_t result=0;
  for(uint32_t r=0;r<starts;r++) { uint32_t mix=0; for(int k=0;k<8;k++) mix=mix*2654435761u+actual[r*8+k]; result+=mix; }
  printf("%u\n",result);
  CUDA(cudaFree(points)); CUDA(cudaFree(centers)); CUDA(cudaFree(partials)); CUDA(cudaEventDestroy(begin)); CUDA(cudaEventDestroy(end));
}
