Overview
--------
The Orphan Maker is a module you can add to your very own slip and slide to increase initial speed and therefore entertainment value.

Diagram
--------
Consult the following diagram to understand the components of the orphan-maker.
```
         D                       F                      E
   o B   +o=======#====================================o+                             
   +-#  *#  >-+o_/                                      |                             
 __[_:_/_|__(==)____________                            |                             
   A          C             '''------------...__________|__                            
```

# A - Operator
The operator is a sober individual without malicious intent.  He or she operates the controls and is responsible for ensuring the (relative) safety of the Orphan Maker.  It is the operator who initiates fun.
* Operator
* Sobriety

# B - Control Panel
The control panel contains the majority of the electronics for the Orphan Maker as well as the connection to power.  Mounted to the box is also a set of controls for the system.
* 240v input
* Main power switch
* Main circuit breaker
* 24v circuit
* 5v circuit
* Control circuit lock
* Motor control
* E-Stop
* Engaged button
* Go button
* Return button
* Jog 3-way switch

# C - Passenger
The passenger rides an inflated tube down the acceleration corrider and is delivered to the top of the slip and slide at a safe and satisfying speed.  Their job is mostly to chortle with joy.
* Passenger
* Tube
* Smile

# D - Riblet 1
Riblet one provides the power to the system.  A 3phase AC motor turns a belt which is attached to the axle for the drive pulley which actuates the acceleration loop.  To this riblet is also mounted the braking system and several sensors.
* Riblet 1 structural beam
* Riblet 1 mount plate
* Riblet 1 foundation
* Riblet 1 guy wire
* Rotation sensor
* Rotation sensor magnet
* Return switch
* Motor
* Motor mount
* Motor drive belt pulley
* Motor belt
* Drive fork
* Drive axle
* Drive axle belt pulley
* Brake disk
* Brake calipers
* Brake cylinder
* Brake hydraulic line
* Brake engage spring
* Brake disengage cylinder
* Brake disengage valve
* Pneumatic pressure line
* Pneumatic pressure source

# E - Riblet 2
Riblet 2 is at the other end of the pulley from Riblet 1.  It mostly holds the pulley in tension, aided by guy wires and provides mount points for the overhead sprinkler system.
* Riblet 2 bottom upright beam
* Riblet 2 top upright beam
* Riblet 2 pulley arm
* Riblet 2 foundation
* Riblet 2 mount plate
* Return pulley
* Return pull axle
* Return pulley fork
* Return pulley mount
* Arm guy wire attachment
* Pole guy wire attachment
* Overhead sprinkler attachment
* Riblet 2 base
* Arm guy wire
* Upright guy wire

# F - Acceleration Loop
A steel cable makes a circuit around the drive pulley and the return pulley.  Attached to this cable is a pull line which is a ski-rope that the passenger holds until attaining appropriate acceleration.
* Cable
* Turnbuckle
* Return switch actuator
* Pull line attach point
* Pull line
* Pull handle

System Inputs
------------
## Power switch
The entire system must be powered.  This is gated by a power switch which controls power to everything within the control panel.

## E-Stop
Does not involve software.  Immediately cuts the control signal to the motor which will cause it to come to a stop.

Software Inputs
------
## Engage Button
When this button is held the system may be engaged.

## Go Button
Actuates the acceleration of the passenger.

## Return Button
Actuates the return of the pull line.

## Return sensor
Indicates that the acceleration loop has returned to the proper position.

## Jog switch
Allows the acceleration loop to be manually shifted forward or backwards.

## Rotation sensor
Indicates each time the drive pulley passes a particular point.

## E-Stop
Directly puts the system in an error state to ensure when E-Stop is
disengaged, the system does not function.

Software Outputs
-------
## Motor forward
Drive motor forward

## Motor reverse
Drive motor reverse

## Motor speed
PWM with 100hz == maximum speed and 0hz = no speed

Pin will PWM to an analog voltage converter to the motor control

## Brake off
Disables the break by relieving pneumatic pressure.

## Jog forward
Drive jog forward pin high

## Jog reverse
Drive jog reverse pin high

## Engage LED
Light the orange engage button

## Return LED
Light the white return button

## Go LED
Light the green go button

Configuration
-------------
## Maximum speed
Target max speed at end of acceleration in meters per second.

## Drive pulley diameter
Diameter of the pulley that drives the system in meters.
~9in

## Acceleration length
The full lenght of acceleration in meters.
~70ft

## Braking length
How many meters are allowed for braking in meters.
~30ft

## Start position
The number of meters in front of the center of the drive pulley that the expected start position is.
~12ft

## Line length
The full length of the drive line system from center of pulley to center of pulley.
Used as a check and should match start_pos + accel_len + brake_len
110

## Set sensor range
A range of meters from the start position in which we expect the set sensor to trigger.
~4 inches

## Brake delay
The number of seconds it takes to release the brake fully.

## Jog speed
Maximum jog speed, with some small ramp-up for precision

