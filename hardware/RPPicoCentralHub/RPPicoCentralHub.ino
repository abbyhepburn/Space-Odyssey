// Pico 2 W / Earle Philhower Arduino-Pico core, Bluetooth enabled.
// Continuous BLE advertisement receiver -> USB CDC, 115200 baud.
#include <Arduino.h>
#include <BLE.h>
#include <BluetoothLock.h>
#include <btstack.h>
#include "ControllerProtocol.h"

static btstack_packet_callback_registration_t handler;
struct Pending { ControllerPacket packet; uint32_t at; };
static Pending pending[32];
static volatile uint8_t head=0, tail=0;
struct Player { bool seen=false, sequenceSeen=false, online=false; uint8_t sequence=0; uint32_t last=0; int8_t forward=0,steer=0,tilt=0; };
static Player players[2];
static uint32_t sentAt=0;

void receiveAdvertisement(uint8_t type,uint16_t channel,uint8_t* packet,uint16_t size){
  (void)channel;(void)size;
  if(type!=HCI_EVENT_PACKET || hci_event_packet_get_type(packet)!=GAP_EVENT_ADVERTISING_REPORT)return;
  const uint8_t* adv=gap_event_advertising_report_get_data(packet);
  const uint8_t length=gap_event_advertising_report_get_data_length(packet);
  for(size_t pos=0;pos<length;){
    const size_t field=adv[pos];
    if(!field || pos+1+field>length)break;
    ControllerPacket decoded;
    if(adv[pos+1]==0xff && decodeController(adv+pos+2,field-1,decoded)){
      uint8_t next=(head+1)%32;
      if(next!=tail){pending[head]={decoded,millis()};head=next;}
    }
    pos+=field+1;
  }
}
void actionLine(uint8_t player,const char* action){
  Serial.print("REMOTE,P");Serial.print(player+1);Serial.print(',');Serial.println(action);
}
void accept(const Pending& entry){
  const auto& e=entry.packet;auto& p=players[e.player];
  bool reconnect=!p.seen || uint32_t(entry.at-p.last)>500;
  p.seen=true;p.online=true;p.last=entry.at;
  if(e.snapshot){p.forward=e.forward;p.steer=e.steer;p.tilt=e.tilt;}
  // Legacy 7-byte controllers remain readable. Upgrade both ESPs for periodic
  // state recovery when an advertisement carrying a center event is lost.
  if(!e.snapshot){
    switch(e.action){
      case 'U':p.forward=100;p.steer=0;break;case 'D':p.forward=-100;p.steer=0;break;
      case 'J':p.steer=-100;p.forward=0;break;case 'K':p.steer=100;p.forward=0;break;
      case 'Z':p.forward=p.steer=0;break;
      case 'L':p.tilt=-100;break;case 'R':p.tilt=100;break;case 'C':p.tilt=0;break;
    }
  }
  bool fresh=!p.sequenceSeen || p.sequence!=e.sequence;
  // On reconnect restore axes, but don't replay a stale advertised button.
  if(reconnect){p.sequenceSeen=true;p.sequence=e.sequence;return;}
  if(e.action=='I')return;
  if(!fresh)return;
  p.sequenceSeen=true;p.sequence=e.sequence;
  if(e.action=='B')actionLine(e.player,"SELECT");
  else if(e.action=='S')actionLine(e.player,"SHAKE");
  else if(e.action=='F')actionLine(e.player,"UPWARD_FLICK");
}
void setup(){
  Serial.begin(115200);
  BLE.begin("AstroLab-Pico");
  {BluetoothLock lock;
   handler.callback=receiveAdvertisement;hci_add_event_handler(&handler);
   gap_set_scan_parameters(0,48,48);gap_start_scan();}
}
void loop(){
  for(int n=0;n<32;n++){
    Pending entry;bool available=false;
    {BluetoothLock lock;if(tail!=head){entry=pending[tail];tail=(tail+1)%32;available=true;}}
    if(!available)break;
    if(uint32_t(millis()-entry.at)<250)accept(entry);
  }
  // No scoring or camera processing here; Python remains game authority.
  if(uint32_t(millis()-sentAt)>=50 && Serial){
    sentAt=millis();
    for(uint8_t i=0;i<2;i++){
      auto& p=players[i];bool fresh=p.seen&&uint32_t(sentAt-p.last)<500;
      if(!fresh){
        if(p.online){actionLine(i,"DISCONNECTED");p.online=false;}
        p.forward=p.steer=p.tilt=0;continue;
      }
      Serial.print("REMOTE,P");Serial.print(i+1);Serial.print(",STATE,");
      Serial.print(p.forward/100.f,2);Serial.print(',');Serial.print(p.steer/100.f,2);Serial.print(',');Serial.println(p.tilt/100.f,2);
    }
  }
  // Legacy GET_STATE/CAPABILITIES may arrive; consume without blocking.
  while(Serial.available())Serial.read();
  delay(1);
}
