#pragma once
#include <stdint.h>
#include <stddef.h>
struct ControllerPacket { uint8_t player, sequence; char action; bool snapshot; int8_t forward, steer, tilt; };
inline bool decodeController(const uint8_t* data, size_t size, ControllerPacket& out) {
  if (!data || (size!=7 && size!=10) || data[0]!=255 || data[1]!=255 || data[2]!='A' || data[3]!='L' || (data[4]!='1' && data[4]!='2')) return false;
  const char a=(char)data[5];
  const char* valid="ISFLRCJKUDZBb";bool found=false;
  for (const char* p=valid;*p;++p)if(*p==a)found=true;
  if(!found)return false;
  out={uint8_t(data[4]-'1'),data[6],a,size==10,0,0,0};
  if(size==10){
    out.forward=(int8_t)data[7];out.steer=(int8_t)data[8];out.tilt=(int8_t)data[9];
    if(out.forward < -100 || out.forward > 100 || out.steer < -100 || out.steer > 100 || out.tilt < -100 || out.tilt > 100)return false;
  }
  return true;
}
