// Project-written UTS CUDA frontier traversal. BOTS supplies the host RNG oracle.
#include <cuda_runtime.h>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <vector>
#include <algorithm>
extern "C" {
#include "bots.h"
#include "brg_sha1.h"
bots_verbose_mode_t bots_verbose_mode = BOTS_VERBOSE_NONE;
}
#define CUDA(call) do { auto e=(call); if(e!=cudaSuccess) { fprintf(stderr,"%s: %s\n",#call,cudaGetErrorString(e)); return 2; } } while(0)
struct State { uint32_t w[5]; };
constexpr uint32_t CAPACITY = 1u << 20;
__device__ uint32_t rol(uint32_t x, int n) { return (x<<n)|(x>>(32-n)); }
__device__ State spawn(State s, uint32_t index) {
  uint32_t w[16]={s.w[0],s.w[1],s.w[2],s.w[3],s.w[4],index,0x80000000u,0,0,0,0,0,0,0,0,192};
  uint32_t a=0x67452301u,b=0xefcdab89u,c=0x98badcfeu,d=0x10325476u,e=0xc3d2e1f0u;
  for(int t=0;t<80;t++) {
    if(t>=16) w[t&15]=rol(w[(t-3)&15]^w[(t-8)&15]^w[(t-14)&15]^w[t&15],1);
    uint32_t f=t<20?((b&c)|(~b&d)):t<40?(b^c^d):t<60?((b&c)|(b&d)|(c&d)):(b^c^d);
    uint32_t k=t<20?0x5a827999u:t<40?0x6ed9eba1u:t<60?0x8f1bbcdcu:0xca62c1d6u;
    uint32_t v=rol(a,5)+f+e+k+w[t&15]; e=d;d=c;c=rol(b,30);b=a;a=v;
  }
  return {{a+0x67452301u,b+0xefcdab89u,c+0x98badcfeu,d+0x10325476u,e+0xc3d2e1f0u}};
}
__global__ void expand(const State *in, uint32_t count, uint32_t arity, double probability,
                       State *out, uint32_t *used, unsigned long long *digest) {
  unsigned long long sums[5]={};
  uint64_t total=uint64_t(count)*arity;
  for(uint64_t i=uint64_t(blockIdx.x)*blockDim.x+threadIdx.x;i<total;i+=uint64_t(gridDim.x)*blockDim.x) {
    State child=spawn(in[i/arity],i%arity);
    for(int j=0;j<5;j++) sums[j]+=child.w[j];
    if((child.w[4]&0x7fffffffu)/2147483648.0 < probability) {
      uint32_t slot=atomicAdd(used,1u);
      if(slot<CAPACITY) out[slot]=child;
    }
  }
  for(int j=0;j<5;j++) {
    for(int offset=16;offset;offset/=2) sums[j]+=__shfl_down_sync(0xffffffff,sums[j],offset);
    if(!(threadIdx.x&31)) atomicAdd(digest+j,sums[j]);
  }
}
static State decode(const unsigned char *bytes) {
  State s;
  for(int j=0;j<5;j++) s.w[j]=(uint32_t(bytes[4*j])<<24)|(uint32_t(bytes[4*j+1])<<16)|(uint32_t(bytes[4*j+2])<<8)|bytes[4*j+3];
  return s;
}
struct Stats {
  uint64_t nodes=1,leaves=0,depth=0;
  unsigned long long digest[5]={};
};
static Stats reference(int seed, uint32_t root_arity, int branching, double probability) {
  struct Frame { unsigned char state[20]; uint32_t next,arity,depth; };
  Frame root={}; rng_init(root.state,seed);root.arity=root_arity;
  std::vector<Frame> stack{root}; Stats stats; State s=decode(root.state);
  for(int j=0;j<5;j++) stats.digest[j]=s.w[j];
  if(!root_arity) stats.leaves=1;
  while(!stack.empty()) {
    Frame &parent=stack.back();
    if(parent.next==parent.arity) { stack.pop_back();continue; }
    Frame child={}; rng_spawn(parent.state,child.state,parent.next++);child.depth=parent.depth+1;
    child.arity=rng_rand(child.state)/2147483648.0<probability?branching:0;
    stats.nodes++;stats.depth=std::max(stats.depth,uint64_t(child.depth));
    s=decode(child.state);for(int j=0;j<5;j++) stats.digest[j]+=s.w[j];
    if(child.arity) stack.push_back(child); else stats.leaves++;
  }
  return stats;
}
int main(int argc,char **argv) {
  bool verify=argc==3 && !strcmp(argv[2],"verify");
  if(argc!=2 && !verify) return 2;
  FILE *f=fopen(argv[1],"r");
  double root_branch,probability;int branching,seed,granularity,expected_depth;
  unsigned long long expected,expected_leaves;
  if(!f || fscanf(f,"%lf %lf %d %d %d %llu %d %llu",&root_branch,&probability,&branching,&seed,&granularity,&expected,&expected_depth,&expected_leaves)!=8) return 2;
  fclose(f);
  if(!std::isfinite(root_branch)||root_branch<0||root_branch>1000000||root_branch!=floor(root_branch)||
     !std::isfinite(probability)||probability<0||probability>1||branching<1||branching>100||seed<0||granularity!=1||!expected) return 2;
  unsigned char bytes[20];rng_init(bytes,seed);State root=decode(bytes);
  State *front,*next;uint32_t *used;unsigned long long *digest;
  CUDA(cudaMalloc(&front,CAPACITY*sizeof(State)));CUDA(cudaMalloc(&next,CAPACITY*sizeof(State)));
  CUDA(cudaMalloc(&used,sizeof(uint32_t)));CUDA(cudaMalloc(&digest,5*sizeof(unsigned long long)));
  Stats stats;for(int j=0;j<5;j++) stats.digest[j]=root.w[j];
  cudaEvent_t begin,end;CUDA(cudaEventCreate(&begin));CUDA(cudaEventCreate(&end));CUDA(cudaEventRecord(begin));
  CUDA(cudaMemcpy(front,&root,sizeof(root),cudaMemcpyHostToDevice));
  CUDA(cudaMemcpy(digest,stats.digest,sizeof(stats.digest),cudaMemcpyHostToDevice));
  uint32_t count=1,arity=uint32_t(root_branch);
  if(!arity) stats.leaves=1;
  while(count && arity) {
    CUDA(cudaMemset(used,0,sizeof(uint32_t)));
    uint64_t children=uint64_t(count)*arity;
    expand<<<unsigned(std::min<uint64_t>((children+255)/256,4096)),256>>>(front,count,arity,probability,next,used,digest);
    CUDA(cudaGetLastError());CUDA(cudaMemcpy(&count,used,sizeof(count),cudaMemcpyDeviceToHost));
    if(count>CAPACITY) { fprintf(stderr,"UTS frontier capacity exceeded: %u\n",count);return 3; }
    stats.nodes+=children;stats.leaves+=children-count;stats.depth++;
    if(stats.nodes>expected) { fprintf(stderr,"UTS node count exceeded contract\n");return 3; }
    std::swap(front,next);arity=branching;
  }
  CUDA(cudaMemcpy(stats.digest,digest,sizeof(stats.digest),cudaMemcpyDeviceToHost));
  CUDA(cudaEventRecord(end));CUDA(cudaEventSynchronize(end));
  float ms;CUDA(cudaEventElapsedTime(&ms,begin,end));fprintf(stderr,"EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n",ms/1000.0);
  fprintf(stderr,"UTS_LEAVES=%llu UTS_DEPTH=%llu\n",(unsigned long long)stats.leaves,(unsigned long long)stats.depth);
  if(verify) {
    Stats ref=reference(seed,uint32_t(root_branch),branching,probability);
    if(stats.nodes!=ref.nodes||stats.leaves!=ref.leaves||stats.depth!=ref.depth||memcmp(stats.digest,ref.digest,sizeof(stats.digest))) {
      fprintf(stderr,"UTS BOTS reference mismatch\n");return 3;
    }
    fprintf(stderr,"BOTS_TREE_VERIFIED=%llu\n",(unsigned long long)stats.nodes);
  }
  printf("%llu\n",(unsigned long long)stats.nodes);
  CUDA(cudaEventDestroy(begin));CUDA(cudaEventDestroy(end));
  CUDA(cudaFree(front));CUDA(cudaFree(next));CUDA(cudaFree(used));CUDA(cudaFree(digest));
  return stats.nodes==expected?0:1;
}
