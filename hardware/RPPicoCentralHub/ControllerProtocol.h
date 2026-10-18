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

// Types live in the header so Arduino-generated function prototypes can see them.
struct Pending { ControllerPacket packet; uint32_t at; };
static constexpr uint32_t CONTROLLER_TIMEOUT_MS=500;
struct Player {
 bool seen=false,online=false; uint8_t sequence=0; uint32_t last=0;
 int8_t forward=0,steer=0,tilt=0;
 bool fresh(uint32_t now) const {return seen && uint32_t(now-last)<CONTROLLER_TIMEOUT_MS;}
 void neutral(){forward=steer=tilt=0;}
 char accept(const ControllerPacket& e,uint32_t at){
  // Duplicate radio reports are not new sensor samples and cannot prolong
  // stale input. After a reboot accept a new sequence after the timeout.
  if(seen && e.sequence==sequence)return 0;
  const bool reconnect=!fresh(at);
  if(seen && !reconnect && uint8_t(e.sequence-sequence)>=128)return 0;
  if(reconnect)neutral();
  seen=online=true;sequence=e.sequence;last=at;
  if(e.snapshot){forward=e.forward;steer=e.steer;tilt=e.tilt;}
  else switch(e.action){
   case 'U':forward=100;steer=0;break;case 'D':forward=-100;steer=0;break;
   case 'J':steer=-100;forward=0;break;case 'K':steer=100;forward=0;break;
   case 'Z':forward=steer=0;break;
   case 'L':tilt=-100;break;case 'R':tilt=100;break;case 'C':tilt=0;break;
  }
  // First sight/reconnect restores axes, but never replays an old gesture.
  return !reconnect && (e.action=='B'||e.action=='S'||e.action=='F')?e.action:0;
 }
};
