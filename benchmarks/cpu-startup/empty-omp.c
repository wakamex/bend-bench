#include <omp.h>
#include <stdio.h>
int main(void) { unsigned s = 0;
#pragma omp parallel reduction(+:s)
  s += 1;
  printf("%u\n", s); return 0; }
