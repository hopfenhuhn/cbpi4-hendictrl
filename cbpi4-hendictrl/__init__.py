import asyncio
import logging
from unittest.mock import MagicMock, patch

from cbpi.api import *

logger = logging.getLogger(__name__)

#GPIO available? When not, use Mock for simulate GPIO
try:
    import RPi.GPIO as GPIO
except Exception:
    logger.error("Failed to load RPi.GPIO. Using Mock")
    MockRPi = MagicMock()
    modules = {
        "RPi": MockRPi,
        "RPi.GPIO": MockRPi.GPIO
    }
    patcher = patch.dict("sys.modules", modules)
    patcher.start()
    import RPi.GPIO as GPIO

mode = GPIO.getmode()
if (mode == None):
    GPIO.setmode(GPIO.BCM)

#Actor Parameters
@parameters([Property.Select(label="onoff_pin", options=[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27], description="On/Off GPIO"),
             Property.Select(label="Inverted", options=["Yes", "No"],description="No: Active on high; Yes: Active on low"),
             Property.Select(label="power_pin", options=[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27], description="Power GPIO"),
             Property.Number(label="pwm_freq", configurable = True, default_value = 100, description="PWM-Frequenz [Hz] (default = 100)"),
             Property.Number(label="power_limit", configurable = True, default_value = 100, description="Power Limit [%] (default = 100)")])

#Actor HENDI 2 Pins (on/off + pwm/power)
class HendiHeater(CBPiActor):

    # Custom property which can be configured by the user
    @action("Set Power", parameters=[Property.Number(label="Power", configurable=True,description="Power Setting [0-100]")])
    async def setpower(self,Power = 100 ,**kwargs):
        logging.info(Power)
        self.power=int(Power)
        if self.power < 0:
            self.power = 0
        if self.power > 100:
            self.power = 100
        await self.set_power(self.power)

    def get_GPIO_state(self, state):
        # ON
        if state == 1:
            return 1 if self.inverted == False else 0
        # OFF
        if state == 0:
            return 0 if self.inverted == False else 1

    async def on_start(self):
        self.power_pin = self.props.get("power_pin", None)
        self.pwm_freq = self.props.get("pwm_freq", 100)
        if self.power_pin is not None:
            GPIO.setup(self.power_pin, GPIO.OUT)
            GPIO.output(self.power_pin, 0)
        self.onoff_pin = self.props.get("onoff_pin", None)
        self.inverted = True if self.props.get("Inverted", "No") == "Yes" else False
        #self.sampleTime = int(self.props.get("SamplingTime", 5))
        GPIO.setup(self.onoff_pin, GPIO.OUT)
        GPIO.output(self.onoff_pin, self.get_GPIO_state(0))
        self.power_limit = self.props.get("power_limit", 100)
        self.state = False
        self.power = 100
        self.p = None
        pass

    async def on(self, power = 100):
        #logging.debug("PWM Actor Power: {}".format(power))
        if power is not None:
            power = min(power, int(self.power_limit))
            self.power = power
            mod_power = int(power ** 3 * 3.0308e-4 + power ** 2 * -7.3273e-2 + power * 6.2810 - 9.8454e1)
            #self.power = mod_power
        else:
            self.power = 100

        #logging.debug("PWM Final Power: {}".format(self.power))

        #logger.debug("PWM ACTOR %s ON - GPIO %s - Frequency %s - Power %s" %  (self.id, self.power_pin,self.pwm_freq,self.power))
        try:
            if self.p is None:
                self.p = GPIO.PWM(int(self.power_pin), float(self.pwm_freq))

            self.p.start(mod_power)
            logger.info("ACTOR %s ON - GPIO %s " %  (self.id, self.onoff_pin))
            GPIO.output(self.onoff_pin, self.get_GPIO_state(1))
            self.state = True
            #await self.cbpi.actor.actor_update(self.id,self.power)
        except:
            pass

    async def off(self):
        logger.info("PWM ACTOR %s OFF - GPIO %s " % (self.id, self.power_pin))
        self.p.ChangeDutyCycle(0)
        logger.info("ACTOR %s OFF - GPIO %s " % (self.id, self.onoff_pin))
        GPIO.output(self.onoff_pin, self.get_GPIO_state(0))
        self.state = False

    async def set_power(self, power):
        if self.p and self.state == True:
            mod_power = int(power ** 3 * 3.0308e-4 + power ** 2 * -7.3273e-2 + power * 6.2810 - 9.8454e1)
            self.p.ChangeDutyCycle(mod_power)
        await self.cbpi.actor.actor_update(self.id,power)
        pass

    def get_state(self):
        return self.state

    async def run(self):
        while self.running == True:
            await asyncio.sleep(1)


@parameters([#Property.Number(label = "gradient_factor", configurable = True, description="Mash gradient (K), 1"),
			#Property.Number(label = "lookback_time", configurable = True, description="Lookback time (s), 15"),
			#Property.Number(label = "mash_power_limit", configurable = True, description="Maximum Mash Power (%), 100"),
			#Property.Number(label = "boil_power", configurable = True, description="Boil power (%) after reaching boiling point, 100"),
			#Property.Number(label = "boiling_point", configurable = True, description="Boilingpoint (°C), 98"),
			Property.Number(label = "boil_threshold", configurable = True, description="Threshold (°C; above boiling mode enabled), 90"),
            Property.Number(label = "Diff_on", configurable = True, description="Hysteresis below target temp. to switch on Heater, 0.2"),
            Property.Number(label = "Diff_off", configurable = True, description="Hysteresis below target temp. to switch off Heater, -0.2")])

#Kettle Controller for Hendi
class HendiControl(CBPiKettleLogic):

    async def on_stop(self):
        await self.actor_off(self.heater)
        pass

    async def run(self):
        try:
            self.kettle = self.get_kettle(self.id)
            self.heater = self.kettle.heater
            heat_percent_old = 100
            self.heater_actor = self.cbpi.actor.find_by_id(self.heater)
            self.boilthreshold = int(self.props.get("boil_threshold", 100))
            self.diffon = float(self.props.get("Diff_on", 0.2))
            self.diffoff = float(self.props.get("Diff_off", -0.2))

            while self.running == True:
                current_kettle_power = self.heater_actor.power
                sensor_value = float(self.get_sensor_value(self.kettle.sensor).get("value",999))
                target_temp = int(self.get_kettle_target_temp(self.id))
                diff = float(target_temp - sensor_value)
                try:
                    heater_state = self.heater_actor.instance.state
                except:
                    heater_state = False

                if target_temp >= self.boilthreshold: #boil mode
                    heat_percent = 100
                    if heater_state == False:
                        await self.actor_on(self.heater, heat_percent)


                else: #mash mode
                    if sensor_value >= target_temp - self.diffoff:
                        heat_percent = 0

                    elif sensor_value <= target_temp - self.diffon:
                        if diff > 2:
                            heat_percent = 100
                            #if self.actor_get_state(self.heater) == False:
                            #    await self.actor_on(self.heater, heat_percent)
                        else:
                            heat_percent = max(int(15 * diff + 25), 25)
                        #if self.actor_get_state(self.heater) == False:
                        #    await self.actor_on(self.heater, heat_percent)

                    #await self.heater_off()

                if (heat_percent != 0) and heater_state == False:
                    await self.actor_on(self.heater, heat_percent)
                elif (heat_percent == 0) and heater_state == True:
                    await self.actor_off(self.heater)

                if (heat_percent_old != heat_percent) or (heat_percent != current_kettle_power):
                    await self.actor_set_power(self.heater, heat_percent)
                    heat_percent_old = heat_percent
                await asyncio.sleep(1)


        except asyncio.CancelledError as e:
            pass
        except Exception as e:
            logger.error("HendiControl Error {}".format(e))
        finally:
            self.running = False
            await self.actor_off(self.heater)


def setup(cbpi):

    '''
    This method is called by the server during startup
    Here you need to register your plugins at the server

    :param cbpi: the cbpi core
    :return:
    '''

    cbpi.plugin.register("Hendi Heater", HendiHeater)
    cbpi.plugin.register("Hendi Control", HendiControl)
