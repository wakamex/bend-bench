// Bend benchmark adaptation, Copyright 2026 HigherOrderCO, Apache-2.0.
// Expand selected four-row prefixes by three rows, then search independent tasks.
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
struct Task { uint32_t cols,ld,rd,owner; };
static void expand(std::vector<Task>& tasks,std::vector<Stats>& initial,Task t,uint32_t full,int remaining) {
  if(!remaining) { tasks.push_back(t); return; }
  uint32_t cand=full&~(t.cols|t.ld|t.rd);
  while(cand) {
    uint32_t b=cand&-cand; cand-=b;
    initial[t.owner].nodes++;
    if((t.cols|b)==full) initial[t.owner].sols++;
    else expand(tasks,initial,{t.cols|b,(t.ld|b)<<1,(t.rd|b)>>1,t.owner},full,remaining-1);
  }
}
__global__ void search(const Task *tasks,uint32_t count,uint32_t full,Stats *out) {
  for(uint32_t i=blockIdx.x*blockDim.x+threadIdx.x;i<count;i+=gridDim.x*blockDim.x) {
    Task t=tasks[i];
    uint32_t cols[18],ld[18],rd[18],cand[18],sols=0,nodes=0;
    int depth=0;
    cols[0]=t.cols; ld[0]=t.ld; rd[0]=t.rd; cand[0]=full&~(t.cols|t.ld|t.rd);
    while(depth>=0) {
      if(!cand[depth]) { depth--; continue; }
      uint32_t b=cand[depth]&-cand[depth]; cand[depth]-=b;
      uint32_t nc=cols[depth]|b; nodes++;
      if(nc==full) { sols++; continue; }
      uint32_t nl=(ld[depth]|b)<<1,nr=(rd[depth]|b)>>1;
      depth++; cols[depth]=nc; ld[depth]=nl; rd[depth]=nr; cand[depth]=full&~(nc|nl|nr);
    }
    atomicAdd(&out[t.owner].sols,sols); atomicAdd(&out[t.owner].nodes,nodes);
  }
}
int main(int argc,char **argv) {
  bool verify=argc>1 && !strcmp(argv[1],"verify");
  if(argc>4 || (argc>1 && !verify)) return 2;
  uint32_t size=17,limit=11730;
  for(int i=2;i<argc;i++) {
    char *end=nullptr; unsigned long v=strtoul(argv[i],&end,10);
    if(!*argv[i] || *end || (i==2 ? v<4 || v>17 : v<1 || v>11730)) return 2;
    if(i==2) size=v; else limit=v;
  }
  uint32_t full=(1u<<size)-1,nn2=size*size,bound=limit<nn2*nn2?limit:nn2*nn2;
  std::vector<Stats> initial(bound),actual(bound);
  std::vector<Task> tasks;
  for(uint32_t i=0;i<bound;i++) {
    uint32_t cols=0,ld=0,rd=0;
    bool legal=true;
    for(uint32_t divisor=nn2*size;divisor;divisor/=size) {
      uint32_t b=1u<<((i/divisor)%size);
      if(b&(cols|ld|rd)) { legal=false; break; }
      cols|=b; ld=(ld|b)<<1; rd=(rd|b)>>1;
    }
    // The reference starts counting strictly below the four-row prefix.
    if(legal) expand(tasks,initial,{cols,ld,rd,i},full,3);
  }
  Task *device_tasks; Stats *out;
  CUDA(cudaMalloc(&device_tasks,(tasks.empty()?1:tasks.size())*sizeof(Task)));
  CUDA(cudaMalloc(&out,bound*sizeof(Stats)));
  cudaEvent_t begin,end; CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end));
  CUDA(cudaEventRecord(begin));
  CUDA(cudaMemcpy(out,initial.data(),bound*sizeof(Stats),cudaMemcpyHostToDevice));
  if(!tasks.empty()) {
    CUDA(cudaMemcpy(device_tasks,tasks.data(),tasks.size()*sizeof(Task),cudaMemcpyHostToDevice));
    uint32_t groups=(tasks.size()+127)/128;
    if(groups>4096) groups=4096;
    search<<<groups,128>>>(device_tasks,tasks.size(),full,out); CUDA(cudaGetLastError());
  }
  CUDA(cudaMemcpy(actual.data(),out,bound*sizeof(Stats),cudaMemcpyDeviceToHost));
  CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end));
  float ms; CUDA(cudaEventElapsedTime(&ms,begin,end));
  fprintf(stderr,"EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n",ms/1000.0);
  if(verify) {
    for(uint32_t j=0;j<(1u<<DEPTH);j++) {
      uint32_t i=(j*2654435761u)&((1u<<DEPTH)-1);
      if(i>=bound) continue;
      Stats ref=pfx(j,size,full,bound);
      if(ref.sols!=actual[i].sols || ref.nodes!=actual[i].nodes) {
        fprintf(stderr,"Prefix mismatch %u: %u/%u != %u/%u\n",i,actual[i].sols,actual[i].nodes,ref.sols,ref.nodes); return 3;
      }
    }
    fprintf(stderr,"FULL_OUTPUT_VERIFIED=%u\n",bound);
  }
  uint32_t sols=0,nodes=0;
  for(Stats s:actual) { sols+=s.sols; nodes+=s.nodes; }
  printf("%u\n",(sols*2654435761u)^nodes);
  CUDA(cudaFree(device_tasks)); CUDA(cudaFree(out)); CUDA(cudaEventDestroy(begin)); CUDA(cudaEventDestroy(end));
}
