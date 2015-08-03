#!/usr/bin/python

import os
from time import sleep
from threading import Thread

try:
    import smbus
except ImportError:
    print 'smbus is not installed! Please run \'sudo apt-get install python-smbus\''


CHECK_TIME = 1
PRIMARY_POWER = 'primary_power'
SECONDARY_POWER = 'secondary_power'
BATTERY_LOW = 'battery_low'


class PyUSVlib(object):
    def __init__(self, device=1, device_address=0x18):
        self._bus = smbus.SMBus(device)    # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
        self._device_address = device_address

    def getVersion(self):
        self._bus.write_byte(self._device_address, 0x01)
        version = ''
        for i in range(12):
            version += chr(self._bus.read_byte(self._device_address))
        return version

    def getCurrentStatus(self):
        self._bus.write_byte(self._device_address, 0x00)
        state = self._bus.read_byte(self._device_address)
        result = []
        if 0x1 & state:
            result.append(PRIMARY_POWER)
        if 0x2 & state:
            result.append(SECONDARY_POWER)
        if 0x4 & state:
            result.append(BATTERY_LOW)
        return result

    def shutdown(self, turnoff_time=30, repeat=3):
        for i in range(repeat):
            self._bus.write_byte(self._device_address, 0x10)
            self._bus.write_byte(self._device_address, turnoff_time)
            sleep(0.07)


class PyUSV(Thread):
    def __init__(self, device, device_address):
        Thread.__init__(self)
        self._pyusv = PyUSVlib(device, device_address)
        self._state = []
        self._callback_methods = []
        self._should_stop = False
        self.daemon = True

    def run(self):
        while not self._should_stop:
            state = self._pyusv.getCurrentStatus()
            if state != self._state:
                self._state = state
                for callback_method in self._callback_methods:
                    callback_method(state)
            sleep(CHECK_TIME)

    def register_callback_method(self, callback_method):
        if callback_method not in self._callback_methods:
            self._callback_methods.append(callback_method)

    def unregister_callback_method(self, callback_method):
        if callback_method in self._callback_methods:
            self._callback_methods.remove(callback_method)

    def shutdown(self, turnoff_time=30, repeat=3, shutdown_cmd='sudo shutdown -h 0'):
        self._pyusv.shutdown(turnoff_time=turnoff_time, repeat=repeat)
        if os.system(shutdown_cmd):
            return "You need to have root privileges to run this script.\nPlease try again, this time using 'sudo'."

    def stop(self):
        self._should_stop = True