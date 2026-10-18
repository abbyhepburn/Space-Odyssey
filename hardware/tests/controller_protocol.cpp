#include "../RPPicoCentralHub/ControllerProtocol.h"
#include <cassert>
#include <cstdio>
ControllerPacket packet(uint8_t sequence,char action='I',int8_t forward=0,int8_t steer=0){
 uint8_t bytes[]={255,255,'A','L','1',uint8_t(action),sequence,uint8_t(forward),uint8_t(steer),0};
 ControllerPacket result;assert(decodeController(bytes,sizeof(bytes),result));return result;
}
int main(){
 Player p;
 assert(!p.accept(packet(20,'B',100),100)); // reconnect suppresses old button
 assert(p.forward==100 && p.fresh(200));
 assert(!p.accept(packet(20,'B',100),300)); // repeated radio report
 assert(p.last==100);
 assert(p.accept(packet(21,'B',100),320)=='B');
 assert(!p.accept(packet(21,'B',100),330));
 assert(!p.accept(packet(22,'I',0),400)); // center is in snapshots
 assert(p.forward==0);
 p.accept(packet(23,'I',100,50),480); // lost preceding event does not matter
 assert(p.forward==100 && p.steer==50);
 p.accept(packet(22,'I',0),500); // stale sequence cannot reset state or timer
 assert(p.forward==100 && p.last==480);
 p.accept(packet(23,'I',100),1200); // repeating a frozen ad cannot keep input live
 assert(!p.fresh(1200));
 p.accept(packet(1,'S',-100),1210); // transmitter reboot recovers after deadline
 assert(p.forward==-100 && p.last==1210);
 Player wrap;wrap.accept(packet(255),10);assert(wrap.accept(packet(0,'F'),90)=='F');
 uint8_t invalid[]={255,255,'A','L','1','I',1,127,0,0};ControllerPacket out;
 assert(!decodeController(invalid,10,out));assert(!decodeController(invalid,6,out));
 invalid[7]=0;assert(decodeController(invalid,7,out)&&!out.snapshot);
 // Emit the same USB text as the receiver for Python/game integration tests.
 Player usb;usb.accept(packet(1),0);usb.accept(packet(2,'I',100,-50),80);
 printf("REMOTE,P1,STATE,%.2f,%.2f,%.2f\n",usb.forward/100.,usb.steer/100.,usb.tilt/100.);
 usb.accept(packet(3),160);
 printf("REMOTE,P1,STATE,%.2f,%.2f,%.2f\n",usb.forward/100.,usb.steer/100.,usb.tilt/100.);
 puts("REMOTE,P1,DISCONNECTED");
}
