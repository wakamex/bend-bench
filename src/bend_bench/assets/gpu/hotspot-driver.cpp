// Preserve Rodinia's compute implementation; replace only its IO/timing driver.
#ifdef HOTSPOT_CUDA
#include <cuda_runtime.h>
#define main rodinia_original_main
#include "hotspot.cu"
#undef main
#else
#define main rodinia_original_main
#include "hotspot_openmp.cpp"
#undef main
#endif
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>

static bool input(const char *path,std::vector<float> &data) {
  FILE *f=fopen(path,"r"); if(!f) return false;
  for(float &v:data) if(fscanf(f,"%f",&v)!=1 || !std::isfinite(v)) { fclose(f); return false; }
  float extra; bool ok=fscanf(f,"%f",&extra)==EOF; fclose(f); return ok;
}
#define CUDA(call) do { cudaError_t e=(call); if(e!=cudaSuccess) { fprintf(stderr,"%s: %s\n",#call,cudaGetErrorString(e)); return 2; } } while(0)
int main(int argc,char **argv) {
  if(argc!=6 && argc!=3) return 2;
  int n=atoi(argv[1]); if(n<16 || n>1024 || n%16) return 2;
  float height=chip_height/n,width=chip_width/n;
  float cap=FACTOR_CHIP*SPEC_HEAT_SI*t_chip*width*height;
  float rx=width/(2.0*K_SI*t_chip*height),ry=height/(2.0*K_SI*t_chip*width);
  float rz=t_chip/(K_SI*height*width);
  float slope=MAX_PD/(FACTOR_CHIP*t_chip*SPEC_HEAT_SI), step=PRECISION/slope;
  float c=step/cap,x=1.0f/rx,y=1.0f/ry,z=1.0f/rz;
  if(argc==3) { if(strcmp(argv[2],"coeff")) return 2; printf("%.9g %.9g %.9g %.9g\n",c,x,y,z); return 0; }
  int steps=atoi(argv[2]),variant=atoi(argv[3]); if(steps<1 || steps>1000 || variant<1) return 2;
  std::vector<float> t(n*n),p(n*n),out(n*n);
  if(!input(argv[4],t) || !input(argv[5],p)) return 2;
#ifdef HOTSPOT_CUDA
  if(variant>7) return 2;
  float *temps[2],*power; size_t bytes=n*n*sizeof(float);
  CUDA(cudaMalloc(&temps[0],bytes)); CUDA(cudaMalloc(&temps[1],bytes)); CUDA(cudaMalloc(&power,bytes));
  CUDA(cudaMemcpy(temps[0],t.data(),bytes,cudaMemcpyHostToDevice));
  CUDA(cudaMemcpy(power,p.data(),bytes,cudaMemcpyHostToDevice));
  cudaEvent_t begin,end; CUDA(cudaEventCreate(&begin)); CUDA(cudaEventCreate(&end));
  CUDA(cudaEventRecord(begin));
  int block=(n+BLOCK_SIZE-2*variant-1)/(BLOCK_SIZE-2*variant);
  int dst=compute_tran_temp(power,temps,n,n,steps,variant,block,block,variant,variant);
  CUDA(cudaGetLastError()); CUDA(cudaEventRecord(end)); CUDA(cudaEventSynchronize(end));
  float ms; CUDA(cudaEventElapsedTime(&ms,begin,end));
  fprintf(stderr,"EVAL_DEVICE_SEQUENCE_SECONDS=%.9f\n",ms/1000.0);
  CUDA(cudaMemcpy(out.data(),temps[dst],bytes,cudaMemcpyDeviceToHost));
  CUDA(cudaFree(temps[0])); CUDA(cudaFree(temps[1])); CUDA(cudaFree(power));
  CUDA(cudaEventDestroy(begin)); CUDA(cudaEventDestroy(end));
#else
  num_omp_threads=variant;
  auto begin=std::chrono::steady_clock::now();
  for(int iter=0;iter<steps;++iter) {
#ifdef HOTSPOT_REFERENCE
    for(int r=0;r<n;++r) for(int col=0;col<n;++col) {
      int i=r*n+col; float center=t[i];
      float north=t[std::max(r-1,0)*n+col],south=t[std::min(r+1,n-1)*n+col];
      float west=t[r*n+std::max(col-1,0)],east=t[r*n+std::min(col+1,n-1)];
      out[i]=center+c*(p[i]+(south+north-2.0f*center)*y+(east+west-2.0f*center)*x+(80.0f-center)*z);
    }
#else
    single_iteration(out.data(),t.data(),p.data(),n,n,c,x,y,z,step);
#endif
    t.swap(out);
  }
  out.swap(t);
  fprintf(stderr,"EVAL_COMPUTE_SECONDS=%.9f\n",std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count());
#endif
  for(float v:out) { if(!std::isfinite(v)) return 3; uint32_t bits; memcpy(&bits,&v,4); printf("%u\n",bits); }
}
