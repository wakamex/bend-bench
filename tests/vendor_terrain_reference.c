// Counterfactual: diagonal scheduling and polynomial fold vs pinned serial C.
#define main upstream_main
#include "main.c"
#undef main
static uint32_t power(uint32_t n) {
  uint32_t r=1,a=2654435761u;
  while(n) { if(n&1) r*=a; a*=a; n>>=1; }
  return r;
}
int main(void) {
  for(uint32_t t=0;t<65536;t+=257) for(uint32_t passes=0;passes<=5;passes++) {
    uint32_t serial[4096],wave[4096],hist[64]={};
    tile_fill((t&255)<<6,(t>>8)<<6,serial); memcpy(wave,serial,sizeof wave);
    tile_smooth(passes,serial);
    for(uint32_t p=passes;p;p--) for(int diag=0;diag<127;diag++) for(int x=0;x<64;x++) {
      int y=diag-x; if(y>=0 && y<64) erode_cell(y*64+x,p,wave);
    }
    if(memcmp(serial,wave,sizeof wave)) return 1;
    uint32_t folded=(t+1)*power(4096),weight=1;
    for(int i=4095;i>=0;i--) { folded+=wave[i]*(i+1u)*weight; weight*=2654435761u; hist[(wave[i]>>2)&63]++; }
    folded=hist_fold(hist,folded); memset(hist,0,sizeof hist);
    if(folded!=tile_hist(serial,hist,t+1)) return 2;
  }
  puts("Wavefront and weighted fold match pinned serial semantics");
}
