// Bend benchmark adaptation, Copyright 2026 HigherOrderCO, Apache-2.0.
#include <cuda_runtime.h>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
// The pinned C arena has one realloc site, whose implicit C conversion needs a cast in C++.
#define realloc(p,n) ((Mt*)std::realloc(p,n))
#define main upstream_main
#include "main.c"
#undef main
#undef realloc
#define CUDA(call) do { auto e=(call); if(e!=cudaSuccess) { fprintf(stderr,"%s: %s\n",#call,cudaGetErrorString(e)); return 2; } } while(0)
__constant__ uint32_t keys[22]={256,5394,24957,5208,26905,30690,3209,52443,61418,20019,30452,22902,61067,56068,17943,62334,34740,36554,60827,14930,33321,60772};
__device__ uint32_t join_hash(uint32_t left,uint32_t right) {
  uint32_t h=left*2654435761u^right;
  uint32_t h2=(h+2246822519u)*2246822519u^(h>>13);
  return h2^(h2>>16);
}
__device__ uint32_t leaf(uint32_t b) {
  uint32_t acc=b+1;
  for(uint32_t block=b*BLOCKS;block<(b+1)*BLOCKS;block++) {
    uint32_t x=block&65535,y=block>>16;
    #pragma unroll
    for(int i=0;i<22;i++) {
      x=((((x>>7)|(x<<9))&65535)+y)&65535;
      x^=keys[i]; y=(((y<<2)|(y>>14))&65535)^x;
    }
    acc=acc*2654435761u+(x|(y<<16));
  }
  return acc;
}
__global__ void leaves(uint32_t *tree,uint32_t *audit,uint32_t n) {
  uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;
  if(i<n) tree[n+i]=audit[n+i]=leaf(i);
}
__global__ void parents(uint32_t *tree,uint32_t start,uint32_t n) {
  uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;
  if(i<n) { i+=start; tree[i]=join_hash(tree[2*i],tree[2*i+1]); }
}
__global__ void audit_parents(const uint32_t *tree,uint32_t *audit,uint32_t start,uint32_t n) {
  uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;
  if(i<n) { i+=start; uint32_t h=join_hash(audit[2*i],audit[2*i+1]); audit[i]=h+(h^tree[i]); }
}
__global__ void proof(const uint32_t *tree,const uint32_t *audit,uint32_t n,uint32_t probe,uint32_t *out) {
  uint32_t i=n+probe,h=leaf(probe);
  while(i>1) { h=(i&1)?join_hash(tree[i^1],h):join_hash(h,tree[i^1]); i>>=1; }
  out[0]=join_hash(audit[1],h); out[1]=h; out[2]=audit[1];
}
int main(int argc,char **argv) {
  bool verify=argc>1 && !strcmp(argv[1],"verify");
  if(argc>3 || (argc>1 && !verify)) return 2;
  uint32_t depth=22;
  if(argc==3) { char *end=nullptr; unsigned long v=strtoul(argv[2],&end,10); if(!*argv[2] || *end || v>22) return 2; depth=v; }
  uint32_t n=1u<<depth,probe=PROBE&(n-1);
  uint32_t *tree,*audit,*out;
  CUDA(cudaMalloc(&tree,size_t(2)*n*4)); CUDA(cudaMalloc(&audit,size_t(2)*n*4)); CUDA(cudaMalloc(&out,12));
  cudaEvent_t begin,end; CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end)); CUDA(cudaEventRecord(begin));
  leaves<<<(n+255)/256,256>>>(tree,audit,n); CUDA(cudaGetLastError());
  for(uint32_t level=n/2;level;level/=2) { parents<<<(level+255)/256,256>>>(tree,level,level); CUDA(cudaGetLastError()); }
  for(uint32_t level=n/2;level;level/=2) { audit_parents<<<(level+255)/256,256>>>(tree,audit,level,level); CUDA(cudaGetLastError()); }
  proof<<<1,1>>>(tree,audit,n,probe,out); CUDA(cudaGetLastError());
  CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end));
  float ms; CUDA(cudaEventElapsedTime(&ms,begin,end)); fprintf(stderr,"EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n",ms/1000.0);
  uint32_t result[3]; CUDA(cudaMemcpy(result,out,sizeof result,cudaMemcpyDeviceToHost));
  if(result[1]!=result[2]) return 3;
  if(verify) {
    std::vector<uint32_t> actual(size_t(2)*n),expected(size_t(2)*n),audited(size_t(2)*n);
    CUDA(cudaMemcpy(actual.data(),tree,actual.size()*4,cudaMemcpyDeviceToHost));
    CUDA(cudaMemcpy(audited.data(),audit,audited.size()*4,cudaMemcpyDeviceToHost));
    for(uint32_t i=0;i<n;i++) expected[n+i]=leaf_hash(i);
    for(uint32_t i=n-1;i;i--) expected[i]=hash_join(expected[2*i],expected[2*i+1]);
    for(uint32_t i=1;i<2*n;i++) if(actual[i]!=expected[i] || audited[i]!=expected[i]) { fprintf(stderr,"Tree mismatch %u\n",i); return 4; }
    PathArena paths={}; uint32_t p=path_gen(&paths,depth,probe,0);
    uint32_t verified=path_verify(&paths,p,leaf_hash(probe));
    if(result[1]!=verified || result[0]!=hash_join(expected[1],verified)) return 5;
    fprintf(stderr,"FULL_OUTPUT_VERIFIED=%u\n",2*n-1);
  }
  printf("%u\n",result[0]);
  CUDA(cudaFree(tree)); CUDA(cudaFree(audit)); CUDA(cudaFree(out)); CUDA(cudaEventDestroy(begin)); CUDA(cudaEventDestroy(end));
}
