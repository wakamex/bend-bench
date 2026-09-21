// Bend benchmark adaptation, Copyright 2026 HigherOrderCO, Apache-2.0.
// Open addressing at <=50% load; separately retain the original logical buckets.
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
constexpr uint32_t SLOTS=32768;
__device__ uint32_t random_word(uint32_t x) { x^=x<<13; x^=x>>17; return x^(x<<5); }
__device__ uint32_t key_for(uint32_t s,uint32_t j) { return random_word(((j+1)*2654435761u)^(s*340573321u))&1048575u; }
__global__ void insert_keys(uint32_t *slots,uint32_t *lengths,uint32_t count) {
  uint32_t t=blockIdx.y,j=blockIdx.x*blockDim.x+threadIdx.x;
  if(j>=count) return;
  uint32_t key=key_for((t+1)*2654435761u,j),pos=random_word(key)&(SLOTS-1);
  for(uint32_t attempt=0;attempt<SLOTS;attempt++,pos=(pos+1)&(SLOTS-1)) {
    uint32_t old=atomicCAS(slots+size_t(t)*SLOTS+pos,0u,key+1);
    if(old==0) { atomicAdd(lengths+size_t(t)*4096+(key&4095),1u); return; }
    if(old==key+1) return;
  }
  asm("trap;"); // At most 16384 distinct inserts into 32768 slots cannot fill the table.
}
__global__ void lookups(const uint32_t *slots,uint32_t *hits,uint32_t count) {
  uint32_t t=blockIdx.y,j=blockIdx.x*blockDim.x+threadIdx.x,hit=0;
  if(j<count) {
    uint32_t key=key_for(random_word((t+1)*2654435761u),j),pos=random_word(key)&(SLOTS-1);
    for(uint32_t attempt=0;attempt<SLOTS;attempt++,pos=(pos+1)&(SLOTS-1)) {
      uint32_t value=slots[size_t(t)*SLOTS+pos];
      if(!value) break;
      if(value==key+1) { hit=1; break; }
    }
  }
  for(int offset=16;offset;offset/=2) hit+=__shfl_down_sync(0xffffffff,hit,offset);
  if(!(threadIdx.x&31)) atomicAdd(hits+t,hit);
}
__global__ void fold_tables(const uint32_t *lengths,const uint32_t *hits,uint32_t *out,uint32_t tables) {
  uint32_t t=blockIdx.x*blockDim.x+threadIdx.x;
  if(t>=tables) return;
  uint32_t count=0,acc=0;
  for(uint32_t b=0;b<4096;b++) { uint32_t n=lengths[size_t(t)*4096+b]; count+=n; acc=(acc*2654435761u)^(n*(b+3)); }
  out[t]=(acc^(hits[t]*2654435761u))+count*340573321u;
}
int main(int argc,char **argv) {
  bool verify=argc>1 && !strcmp(argv[1],"verify");
  if(argc>4 || (argc>1 && !verify)) return 2;
  uint32_t depth=11,count=16384;
  for(int i=2;i<argc;i++) { char *end=nullptr; unsigned long v=strtoul(argv[i],&end,10);
    if(!*argv[i] || *end || v>(i==2?11u:16384u)) return 2; if(i==2) depth=v; else count=v;
  }
  uint32_t tables=1u<<depth,*slots,*lengths,*hits,*out;
  CUDA(cudaMalloc(&slots,size_t(tables)*SLOTS*4)); CUDA(cudaMalloc(&lengths,size_t(tables)*4096*4));
  CUDA(cudaMalloc(&hits,tables*4)); CUDA(cudaMalloc(&out,tables*4));
  cudaEvent_t begin,end; CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end)); CUDA(cudaEventRecord(begin));
  CUDA(cudaMemset(slots,0,size_t(tables)*SLOTS*4)); CUDA(cudaMemset(lengths,0,size_t(tables)*4096*4)); CUDA(cudaMemset(hits,0,tables*4));
  if(count) {
    insert_keys<<<dim3((count+255)/256,tables),256>>>(slots,lengths,count); CUDA(cudaGetLastError());
    lookups<<<dim3((count+255)/256,tables),256>>>(slots,hits,count); CUDA(cudaGetLastError());
  }
  fold_tables<<<(tables+127)/128,128>>>(lengths,hits,out,tables); CUDA(cudaGetLastError());
  CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end));
  float ms; CUDA(cudaEventElapsedTime(&ms,begin,end)); fprintf(stderr,"EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n",ms/1000.0);
  std::vector<uint32_t> values(tables); CUDA(cudaMemcpy(values.data(),out,tables*4,cudaMemcpyDeviceToHost));
  if(verify) {
    std::vector<uint32_t> bucket_lengths(size_t(tables)*4096),actual_hits(tables);
    CUDA(cudaMemcpy(bucket_lengths.data(),lengths,bucket_lengths.size()*4,cudaMemcpyDeviceToHost));
    CUDA(cudaMemcpy(actual_hits.data(),hits,tables*4,cudaMemcpyDeviceToHost));
    for(uint32_t t=0;t<tables;t++) {
      if(values[t]!=table_run(t,count)) { fprintf(stderr,"Table mismatch %u\n",t); return 3; }
      for(uint32_t b=0;b<4096;b++) if(bucket_lengths[size_t(t)*4096+b]!=table_len(&tab,b)) return 4;
      uint32_t expected_hits=0,s=word_prng((t+1)*2654435761u);
      for(uint32_t j=0;j<count;j++) { uint32_t key=draw_key(s,j); expected_hits+=table_has(&tab,key&4095,key); }
      if(actual_hits[t]!=expected_hits) return 5;
    }
    fprintf(stderr,"FULL_OUTPUT_VERIFIED=%u\n",tables*4096);
  }
  uint32_t result=0; for(uint32_t v:values) result+=v; printf("%u\n",result);
  CUDA(cudaFree(slots)); CUDA(cudaFree(lengths)); CUDA(cudaFree(hits)); CUDA(cudaFree(out)); CUDA(cudaEventDestroy(begin)); CUDA(cudaEventDestroy(end));
}
