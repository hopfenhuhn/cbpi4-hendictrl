# Craftbeerpi 4 - Hendi Control
Control Hendi induction cooker unsing an internal pcb following https://hobbybrauer.de/forum/viewtopic.php?t=24385&hilit=hendi&start=100#p390720

The Plugin provides an actor for the cooker and a Kettle Logic for mashing. During wort boiling, the cooker is always driven with full power (boil threshold).

The calibration of Controler-Power (CBPi) to match real Hendi Power is currently fixed in the code (see lines 78 & 107) and was calculated manually.

The Kettle Logic uses a hysteresis, while the power of the heater is predefined by steps (fixed in code lines 162-172).

Next steps will be to allow more customisation (calibration & heater steps/mash mode).