// Bend benchmark adaptation, Copyright 2026 HigherOrderCO, Apache-2.0.
// One warp per 32x32 maze; each lane holds a bit row of the frontier.
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
__device__ uint32_t rng(uint32_t x) { x^=x<<13; x^=x>>17; return x^(x<<5); }
__global__ void mazes(uint32_t first,uint32_t count,uint32_t *out,uint32_t *all_distances) {
  __shared__ uint32_t distance[4][1024];
  uint32_t warp=threadIdx.x/32,row=threadIdx.x&31,local=blockIdx.x*4+warp;
  if(local>=count) return; // Whole warps leave together.
  uint32_t seed=(first+local+1)*2654435761u,open=0;
  for(uint32_t x=0;x<32;x++) {
    uint32_t c=row*32+x,h=rng(seed^((c+1)*340573321u));
    if(!c || h%100>=30) open|=1u<<x;
    distance[warp][c]=UNSEEN;
  }
  uint32_t frontier=row==0?1u:0u,seen=frontier,depth=0;
  while(__any_sync(0xffffffff,frontier!=0)) {
    uint32_t bits=frontier;
    while(bits) { uint32_t x=__ffs(bits)-1; distance[warp][row*32+x]=depth; bits&=bits-1; }
    uint32_t up=__shfl_up_sync(0xffffffff,frontier,1),down=__shfl_down_sync(0xffffffff,frontier,1);
    uint32_t next=(frontier<<1)|(frontier>>1)|(row?up:0)|(row<31?down:0);
    frontier=next&open&~seen; seen|=frontier; depth++;
  }
  __syncwarp();
  if(all_distances) for(uint32_t x=0;x<32;x++) all_distances[size_t(local)*1024+row*32+x]=distance[warp][row*32+x];
  if(row==0) {
    uint32_t acc=0,reached=0;
    for(uint32_t c=0;c<1024;c++) {
      uint32_t d=distance[warp][c],hit=d!=UNSEEN;
      acc=(acc*2654435761u)^(hit?d*(c+1):0); reached+=hit;
    }
    out[local]=acc^(reached*2246822519u);
  }
}
int main(int argc,char **argv) {
  bool verify=argc>1 && !strcmp(argv[1],"verify");
  if(argc>3 || (argc>1 && !verify)) return 2;
  uint32_t depth=19;
  if(argc==3) { char *end=nullptr; unsigned long v=strtoul(argv[2],&end,10); if(!*argv[2] || *end || v>19) return 2; depth=v; }
  uint32_t n=1u<<depth,batch=n<4096?n:4096,*out,*distances=nullptr,result=0;
  CUDA(cudaMalloc(&out,batch*4)); if(verify) { CUDA(cudaMalloc(&distances,size_t(batch)*1024*4)); }
  std::vector<uint32_t> values(batch),actual(verify?size_t(batch)*1024:0);
  cudaEvent_t begin,end; CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end));
  double total_ms=0;
  for(uint32_t first=0;first<n;first+=batch) {
    uint32_t count=n-first<batch?n-first:batch;
    CUDA(cudaEventRecord(begin)); mazes<<<(count+3)/4,128>>>(first,count,out,distances); CUDA(cudaGetLastError());
    CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end));
    float ms; CUDA(cudaEventElapsedTime(&ms,begin,end)); total_ms+=ms;
    CUDA(cudaMemcpy(values.data(),out,count*4,cudaMemcpyDeviceToHost));
    if(verify) {
      CUDA(cudaMemcpy(actual.data(),distances,size_t(count)*1024*4,cudaMemcpyDeviceToHost));
      for(uint32_t i=0;i<count;i++) {
        Bfs b={}; uint32_t s=(first+i+1)*2654435761u;
        for(uint32_t c=0;c<1024;c++) { b.g[c]=cell_open(s,c); b.d[c]=UNSEEN; }
        b.d[0]=0; b.tail=1;
        while(b.head<b.tail) bfs_pop(&b);
        if(memcmp(b.d,actual.data()+size_t(i)*1024,sizeof b.d) || bfs_fold(&b)!=values[i]) { fprintf(stderr,"Maze mismatch %u\n",first+i); return 3; }
      }
    }
    for(uint32_t i=0;i<count;i++) result+=values[i];
  }
  fprintf(stderr,"EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n",total_ms/1000);
  if(verify) { fprintf(stderr,"FULL_OUTPUT_VERIFIED=%llu\n",(unsigned long long)n*1024); CUDA(cudaFree(distances)); }
  printf("%u\n",result); CUDA(cudaFree(out)); CUDA(cudaEventDestroy(begin)); CUDA(cudaEventDestroy(end));
}
