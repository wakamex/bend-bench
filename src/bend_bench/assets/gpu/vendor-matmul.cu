// Exact bounded-integer GEMM plus the published wrapping-U32 Freivalds check.
#include <cuda_runtime.h>
#include <cublas_v2.h>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#define CUDA(call) do { auto e=(call); if(e!=cudaSuccess) { fprintf(stderr,"%s: %s\n",#call,cudaGetErrorString(e)); return 2; } } while(0)
#define BLAS(call) do { auto e=(call); if(e!=CUBLAS_STATUS_SUCCESS) { fprintf(stderr,"%s: cuBLAS status %d\n",#call,int(e)); return 2; } } while(0)

__host__ __device__ uint32_t branch(uint32_t s,unsigned quadrant) {
  switch(quadrant) {
    case 0: return s*1664525u+1u;
    case 1: return s*214013u+3u;
    case 2: return s*16843009u+5u;
    default: return s*48271u+7u;
  }
}
__host__ __device__ uint32_t entry(unsigned depth,unsigned row,unsigned col,uint32_t seed) {
  for(unsigned bit=depth;bit-->0;) seed=branch(seed,2*((row>>bit)&1)+((col>>bit)&1));
  return seed%100u;
}
__host__ __device__ uint32_t vector_entry(unsigned depth,unsigned row,uint32_t seed) {
  for(unsigned bit=depth;bit-->0;) seed=branch(seed,(row>>bit)&1);
  return (seed*2654435761u)%100u+1u;
}
__global__ void generate(int8_t *a,int8_t *b,uint32_t *r,unsigned depth,unsigned batches) {
  unsigned n=1u<<depth, i=blockIdx.x*blockDim.x+threadIdx.x;
  if(i>=batches*n*n) return;
  unsigned batch=i/(n*n),row=(i/n)%n,col=i%n;
  uint32_t s=batch*2654435761u;
  a[i]=int8_t(entry(depth,row,col,s+1)); b[i]=int8_t(entry(depth,row,col,s+2));
  if(col==0) r[batch*n+row]=vector_entry(depth,row,s+3);
}
struct Result { uint32_t value,bad; };
__global__ void verify_and_sum(const int8_t *a,const int8_t *b,const int32_t *c,
                               const uint32_t *r,Result *results,unsigned n) {
  unsigned batch=blockIdx.x,row=threadIdx.x;
  a+=batch*n*n; b+=batch*n*n; c+=batch*n*n; r+=batch*n;
  __shared__ uint32_t br[128],sums[128],diffs[128];
  uint32_t v=0;
  for(unsigned j=0;j<n;j++) v+=uint32_t(b[row*n+j])*r[j];
  br[row]=v; __syncthreads();
  uint32_t cr=0,abr=0,sum=0;
  for(unsigned j=0;j<n;j++) {
    cr+=uint32_t(c[row*n+j])*r[j]; abr+=uint32_t(a[row*n+j])*br[j]; sum+=uint32_t(c[row*n+j]);
  }
  sums[row]=sum; diffs[row]=cr^abr; __syncthreads();
  if(row==0) {
    uint32_t total=0,bad=0;
    for(unsigned j=0;j<n;j++) { total+=sums[j]; bad|=diffs[j]; }
    uint32_t seed=batch*2654435761u;
    results[batch]={(total^(seed*2654435761u))+uint32_t(bad==0),bad};
  }
}
int main(int argc,char **argv) {
  bool verify=argc>1 && !strcmp(argv[1],"verify");
  if(argc>4 || (argc>1 && !verify) || argc==3) return 2;
  unsigned depth=7,batches=384;
  if(argc==4) {
    char *end=nullptr; unsigned long d=strtoul(argv[2],&end,10);
    if(!*argv[2] || *end || d<2 || d>7) return 2;
    unsigned long count=strtoul(argv[3],&end,10);
    if(!*argv[3] || *end || count<1 || count>384) return 2;
    depth=unsigned(d); batches=unsigned(count);
  }
  unsigned n=1u<<depth,items=batches*n*n;
  int8_t *a,*b; int32_t *c; uint32_t *r; Result *results;
  CUDA(cudaMalloc(&a,items)); CUDA(cudaMalloc(&b,items)); CUDA(cudaMalloc(&c,size_t(items)*4));
  CUDA(cudaMalloc(&r,batches*n*4)); CUDA(cudaMalloc(&results,batches*sizeof(Result)));
  cublasHandle_t handle; BLAS(cublasCreate(&handle));
  int version; BLAS(cublasGetVersion(handle,&version)); fprintf(stderr,"CUBLAS_VERSION=%d\n",version);
  int32_t alpha=1,beta=0;
  cudaEvent_t begin,end; CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end));
  CUDA(cudaEventRecord(begin));
  generate<<<(items+255)/256,256>>>(a,b,r,depth,batches); CUDA(cudaGetLastError());
  // Row-major C=A*B equals column-major C^T=B^T*A^T.
  BLAS(cublasGemmStridedBatchedEx(handle,CUBLAS_OP_N,CUBLAS_OP_N,n,n,n,&alpha,
       b,CUDA_R_8I,n,n*n,a,CUDA_R_8I,n,n*n,&beta,c,CUDA_R_32I,n,n*n,batches,
       CUBLAS_COMPUTE_32I,CUBLAS_GEMM_DEFAULT));
  verify_and_sum<<<batches,n>>>(a,b,c,r,results,n); CUDA(cudaGetLastError());
  CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end));
  float ms; CUDA(cudaEventElapsedTime(&ms,begin,end));
  fprintf(stderr,"EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n",ms/1000.0);
  std::vector<Result> out(batches); CUDA(cudaMemcpy(out.data(),results,batches*sizeof(Result),cudaMemcpyDeviceToHost));
  uint32_t result=0;
  for(auto value:out) { if(value.bad) return 3; result+=value.value; }
  if(verify) {
    std::vector<int32_t> actual(items); CUDA(cudaMemcpy(actual.data(),c,size_t(items)*4,cudaMemcpyDeviceToHost));
    std::vector<uint32_t> aa(n*n),bb(n*n);
    for(unsigned batch=0;batch<batches;batch++) {
      uint32_t seed=batch*2654435761u;
      for(unsigned i=0;i<n;i++) for(unsigned j=0;j<n;j++) {
        aa[i*n+j]=entry(depth,i,j,seed+1); bb[i*n+j]=entry(depth,i,j,seed+2);
      }
      for(unsigned i=0;i<n;i++) for(unsigned j=0;j<n;j++) {
        uint32_t expected=0;
        for(unsigned k=0;k<n;k++) expected+=aa[i*n+k]*bb[k*n+j];
        if(uint32_t(actual[batch*n*n+i*n+j])!=expected) return 4;
      }
    }
    fprintf(stderr,"FULL_OUTPUT_VERIFIED=%u\n",items);
  }
  printf("%u\n",result);
  BLAS(cublasDestroy(handle));
  CUDA(cudaFree(a)); CUDA(cudaFree(b)); CUDA(cudaFree(c)); CUDA(cudaFree(r)); CUDA(cudaFree(results));
  CUDA(cudaEventDestroy(begin)); CUDA(cudaEventDestroy(end));
}
