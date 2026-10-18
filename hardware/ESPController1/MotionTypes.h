#pragma once
// Included before Arduino-generated function prototypes.
struct Motion {
  float ax,ay,az;          // acceleration in m/s^2
  float gx,gy,gz;          // gyro rad/s (diagnostics / future use)
};
