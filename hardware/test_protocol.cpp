#include "RPPicoCentralHub/ControllerProtocol.h"
#include <cassert>
int main(){
 ControllerPacket p;
 uint8_t state[]={255,255,'A','L','2','I',255,100,uint8_t(-75),25};
 assert(decodeController(state,10,p));assert(p.player==1&&p.snapshot&&p.forward==100&&p.steer==-75&&p.tilt==25);
 assert(decodeController(state,7,p)&&!p.snapshot);
 assert(!decodeController(state,6,p));state[7]=127;assert(!decodeController(state,10,p));
 state[7]=0;state[4]='3';assert(!decodeController(state,10,p));
 state[4]='1';state[5]='?';assert(!decodeController(state,10,p));
}
