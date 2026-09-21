// Bend benchmark adaptation, Copyright 2026 HigherOrderCO, Apache-2.0.
// One warp per fixed-depth candidate, with independent fitness points across lanes.
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
__host__ __device__ uint32_t rng(uint32_t x) { x^=x<<13; x^=x>>17; return x^(x<<5); }
__host__ __device__ uint32_t candidate_seed(uint32_t index,uint32_t depth) {
  uint32_t s=42;
  while(depth) { depth--; s=(index&(1u<<depth))?s*214013u+3:s*1664525u+1; }
  return rng(s);
}
template<int D> __device__ __forceinline__ uint32_t evaluate(const uint32_t *tree,uint32_t node,uint32_t x) {
  uint32_t h=tree[node];
  if constexpr(D==0) return ((h>>8)&1)?h&255:x;
  else {
    uint32_t a=evaluate<D-1>(tree,node*2,x),b=evaluate<D-1>(tree,node*2+1,x);
    switch(h&3) { case 0:return a+b; case 1:return a-b; case 2:return a*b; default:return a^b; }
  }
}
__device__ uint32_t fitness(uint32_t seed,uint32_t points,uint32_t *tree) {
  uint32_t lane=threadIdx.x&31;
  if(lane==0) tree[1]=rng(seed);
  __syncwarp();
  for(uint32_t level=1;level<32;level*=2) {
    if(lane<level) { uint32_t i=level+lane,h=tree[i]; tree[2*i]=rng(h^2654435761u); tree[2*i+1]=rng(h+340573321u); }
    __syncwarp();
  }
  uint32_t total=0;
  for(uint32_t x=lane;x<points;x+=32) {
    uint32_t actual=evaluate<5>(tree,1,x),target=x*x+(3*x+7);
    total+=actual<target?target-actual:actual-target;
  }
  for(int offset=16;offset;offset/=2) total+=__shfl_down_sync(0xffffffff,total,offset);
  return __shfl_sync(0xffffffff,total,0)+63*8;
}
__global__ void population(Sel *tree,uint32_t n,uint32_t depth,uint32_t points) {
  __shared__ uint32_t expressions[4][64];
  uint32_t warp=threadIdx.x/32,index=blockIdx.x*4+warp;
  if(index>=n) return;
  uint32_t seed=candidate_seed(index,depth),fit=fitness(seed,points,expressions[warp]);
  if(!(threadIdx.x&31)) tree[n+index]={fit,seed,fit^(seed*2654435761u)};
}
__global__ void tournament(Sel *tree,uint32_t level) {
  uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;
  if(i>=level) return;
  i+=level; Sel a=tree[2*i],b=tree[2*i+1],best=a.fit<b.fit?a:b;
  tree[i]={best.fit,best.seed,a.sum+b.sum};
}
__global__ void climb(const Sel *tree,uint32_t points,uint32_t *out,Sel *trace) {
  __shared__ uint32_t expression[64];
  Sel best=tree[1];
  for(uint32_t r=32;r;r--) {
    uint32_t seed=rng(best.seed^(r*40503u)),fit=fitness(seed,points,expression);
    if(threadIdx.x==0 && trace) trace[32-r]={fit,seed,fit^(seed*2654435761u)};
    if(fit<best.fit) { best.fit=fit; best.seed=seed; }
    __syncwarp();
  }
  if(threadIdx.x==0) *out=(best.fit^(best.seed*2654435761u))+best.sum;
}
int main(int argc,char **argv) {
  bool verify=argc>1 && !strcmp(argv[1],"verify");
  if(argc>4 || (argc>1 && !verify)) return 2;
  uint32_t depth=18,points=110;
  for(int i=2;i<argc;i++) { char *end=nullptr; unsigned long v=strtoul(argv[i],&end,10);
    if(!*argv[i] || *end || v>(i==2?18u:110u)) return 2; if(i==2) depth=v; else points=v;
  }
  uint32_t n=1u<<depth,*out; Sel *tree,*trace=nullptr;
  CUDA(cudaMalloc(&tree,size_t(2)*n*sizeof(Sel))); CUDA(cudaMalloc(&out,4)); if(verify) { CUDA(cudaMalloc(&trace,32*sizeof(Sel))); }
  cudaEvent_t begin,end; CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end)); CUDA(cudaEventRecord(begin));
  population<<<(n+3)/4,128>>>(tree,n,depth,points); CUDA(cudaGetLastError());
  for(uint32_t level=n/2;level;level/=2) { tournament<<<(level+255)/256,256>>>(tree,level); CUDA(cudaGetLastError()); }
  climb<<<1,32>>>(tree,points,out,trace); CUDA(cudaGetLastError());
  CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end));
  float ms; CUDA(cudaEventElapsedTime(&ms,begin,end)); fprintf(stderr,"EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n",ms/1000.0);
  uint32_t result; CUDA(cudaMemcpy(&result,out,4,cudaMemcpyDeviceToHost));
  if(verify) {
    std::vector<Sel> actual(size_t(2)*n),expected(size_t(2)*n); Sel mutations[32];
    CUDA(cudaMemcpy(actual.data(),tree,actual.size()*sizeof(Sel),cudaMemcpyDeviceToHost));
    CUDA(cudaMemcpy(mutations,trace,sizeof mutations,cudaMemcpyDeviceToHost));
    for(uint32_t i=0;i<n;i++) expected[n+i]=candidate_evaluate(candidate_seed(i,depth),points);
    for(uint32_t i=n-1;i;i--) expected[i]=winner_pick(expected[2*i],expected[2*i+1]);
    for(uint32_t i=1;i<2*n;i++) if(memcmp(&actual[i],&expected[i],sizeof(Sel))) { fprintf(stderr,"Candidate/tournament mismatch %u\n",i); return 3; }
    Sel best=expected[1];
    for(uint32_t r=32;r;r--) {
      Sel v=candidate_evaluate(word_prng(best.seed^(r*40503u)),points);
      if(memcmp(&v,mutations+32-r,sizeof(Sel))) return 4;
      if(v.fit<best.fit) { best.fit=v.fit; best.seed=v.seed; }
    }
    if(result!=run_finish(32,points,expected[1])) return 5;
    // Also exercise the original recursive seed traversal on small populations.
    if(depth<=8 && result!=run(depth,42,32,points)) return 6;
    fprintf(stderr,"FULL_OUTPUT_VERIFIED=%u\n",2*n-1+32); CUDA(cudaFree(trace));
  }
  printf("%u\n",result); CUDA(cudaFree(tree)); CUDA(cudaFree(out)); CUDA(cudaEventDestroy(begin)); CUDA(cudaEventDestroy(end));
}
