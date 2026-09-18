// Compile against an unmodified Rodinia 3.1 OpenMP HotSpot source.
#define main rodinia_original_main
#include "hotspot_openmp.cpp"
#undef main
#include <algorithm>
#include <cmath>
#include <vector>

int main() {
  const int n=64;
  std::vector<float> temp(n*n), power(n*n), actual(n*n), expected(n*n);
  for(int i=0;i<n*n;++i) { temp[i]=50.0f+(i%97)*0.25f; power[i]=(i%31)*0.5f; }
  num_omp_threads=1;
  single_iteration(actual.data(),temp.data(),power.data(),n,n,0.001f,0.1f,0.1f,0.01f,1.0f);
  int boundary_tile_errors=0, interior_tile_errors=0;
  float max_error=0;
  for(int r=0;r<n;++r) for(int c=0;c<n;++c) {
    int i=r*n+c;
    float center=temp[i];
    float north=temp[std::max(r-1,0)*n+c], south=temp[std::min(r+1,n-1)*n+c];
    float west=temp[r*n+std::max(c-1,0)], east=temp[r*n+std::min(c+1,n-1)];
    expected[i]=center+0.001f*(power[i]+(south+north-2.0f*center)*0.1f+
                            (east+west-2.0f*center)*0.1f+(80.0f-center)*0.01f);
    float error=std::abs(expected[i]-actual[i]); max_error=std::max(error,max_error);
    if(error>0.00001f) {
      if(r<16 || c<16 || r>=48 || c>=48) ++boundary_tile_errors;
      else ++interior_tile_errors;
    }
  }
  printf("boundary_tile_errors=%d interior_tile_errors=%d max_abs_error=%.9g\n",
         boundary_tile_errors,interior_tile_errors,max_error);
  return boundary_tile_errors || interior_tile_errors ? 1 : 0;
}
