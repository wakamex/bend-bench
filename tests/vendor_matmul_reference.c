// Use the actual pinned quadtree implementation as an independent layout oracle.
#define main vendor_main
#include "main.c"
#undef main
int main(int argc,char **argv) {
  if(argc!=3) return 2;
  unsigned depth=atoi(argv[1]),batches=atoi(argv[2]);
  uint32_t result=0;
  for(unsigned i=0;i<batches;i++) result+=round_run(depth,i*2654435761u);
  printf("%u\n",result);
}
