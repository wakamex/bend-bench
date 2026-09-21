// Bend benchmark adaptation, Copyright 2026 HigherOrderCO, Apache-2.0.
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
__constant__ char pattern[]="i = ( n o i ) o ( n o i ) o ( n o i ) ;";
__device__ uint32_t random_word(uint32_t x) { x^=x<<13; x^=x>>17; return x^(x<<5); }
__device__ uint32_t line_value(uint32_t id) {
  char text[128]; uint32_t n=0,s=random_word((id+1)*2654435761u);
  for(uint32_t k=0;k<sizeof(pattern)-1;k++) {
    uint32_t t=random_word(s^(k*2654435761u)); char c=pattern[k];
    if(c=='i' || c=='n') {
      uint32_t count=c=='i'?1+(t&7):1+t%6;
      for(uint32_t j=0;j<count;j++) { t=random_word(t); text[n++]=c=='i'?'a'+t%26:'0'+t%10; }
    } else if(c=='o') text[n++]="+-*/"[t&3];
    else text[n++]=c;
  }
  uint32_t acc=0,i=0;
  while(i<n) {
    char c=text[i]; uint32_t kind,value;
    if(c>='a' && c<='z') {
      kind=1; value=2166136261u;
      do { value=(value^uint32_t(text[i]))*16777619u; i++; } while(i<n && text[i]>='a' && text[i]<='z');
    } else if(c>='0' && c<='9') {
      kind=2; value=0;
      do { value=value*10+uint32_t(text[i]-'0'); i++; } while(i<n && text[i]>='0' && text[i]<='9');
    } else if(c==' ') { i++; continue; }
    else { kind=3; value=uint32_t(c); i++; }
    acc=(acc*2654435761u)^(kind*40503u+value);
  }
  return acc;
}
__global__ void scan(uint32_t n,uint32_t *sum,uint32_t *values) {
  uint32_t total=0;
  for(uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;i<n;i+=gridDim.x*blockDim.x) {
    uint32_t v=line_value(i); total+=v; if(values) values[i]=v;
  }
  for(int offset=16;offset;offset/=2) total+=__shfl_down_sync(0xffffffff,total,offset);
  if(!(threadIdx.x&31)) atomicAdd(sum,total);
}
int main(int argc,char **argv) {
  bool verify=argc>1 && !strcmp(argv[1],"verify");
  if(argc>3 || (argc>1 && !verify)) return 2;
  uint32_t depth=23;
  if(argc==3) { char *end=nullptr; unsigned long v=strtoul(argv[2],&end,10); if(!*argv[2] || *end || v>23) return 2; depth=v; }
  uint32_t n=1u<<depth,groups=(n+127)/128; if(groups>4096) groups=4096;
  uint32_t *sum,*values=nullptr; CUDA(cudaMalloc(&sum,4)); if(verify) { CUDA(cudaMalloc(&values,size_t(n)*4)); }
  cudaEvent_t begin,end; CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end)); CUDA(cudaEventRecord(begin));
  CUDA(cudaMemset(sum,0,4)); scan<<<groups,128>>>(n,sum,values); CUDA(cudaGetLastError());
  CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end));
  float ms; CUDA(cudaEventElapsedTime(&ms,begin,end)); fprintf(stderr,"EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n",ms/1000.0);
  uint32_t result; CUDA(cudaMemcpy(&result,sum,4,cudaMemcpyDeviceToHost));
  if(verify) {
    std::vector<uint32_t> actual(n); CUDA(cudaMemcpy(actual.data(),values,size_t(n)*4,cudaMemcpyDeviceToHost));
    uint32_t expected=0;
    for(uint32_t i=0;i<n;i++) {
      char buf[128]; uint32_t len=gen(seed(i),buf),v=lex(buf,len);
      if(actual[i]!=v) { fprintf(stderr,"Line mismatch %u\n",i); return 3; } expected+=v;
    }
    if(result!=expected) return 4;
    fprintf(stderr,"FULL_OUTPUT_VERIFIED=%u\n",n); CUDA(cudaFree(values));
  }
  printf("%u\n",result); CUDA(cudaFree(sum)); CUDA(cudaEventDestroy(begin)); CUDA(cudaEventDestroy(end));
}
