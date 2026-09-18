// Independent host reference for wrapping-U32 primitive input/output contracts.
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
int main(int argc,char **argv) {
  if(argc!=3) return 2;
  unsigned depth=unsigned(atoi(argv[2])); if(depth>26) return 2;
  uint32_t n=1u<<depth,sum=0;
  std::vector<uint32_t> a(n);
  for(uint32_t i=0;i<n;i++) {
    uint32_t x=(i+1)*2654435761u; x^=x<<13; x^=x>>17; x^=x<<5;
    a[i]=x; sum+=x;
  }
  if(!strcmp(argv[1],"reduce")) { printf("%u\n",sum); return 0; }
  if(strcmp(argv[1],"sort")) return 2;
  std::sort(a.begin(),a.end()); uint32_t lo=a.front(),hi=a.back();
  for(uint32_t width=n;width>1;width/=2)
    for(uint32_t i=0;i<width/2;i++) a[i]=a[2*i]*2654435761u+a[2*i+1];
  printf("%u\n",((a[0]*2654435761u)^(hi+lo*340573321u))+2246822519u);
}
