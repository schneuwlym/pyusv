#!/usr/bin/env python

import argparse
from PyUSV import PyUSV, PRIMARY_POWER, SECONDARY_POWER, BATTERY_LOW
import ast
import signal
from Queue import Queue, Empty
import os
import sys


DEFAULT_CONFIG_FILE = '/etc/pyusv.conf'
signal_queue = Queue()


def signal_handler(signal, frame):
    global signal_queue
    print 'Got signal: %d' % signal
    signal_queue.put(signal)


def pyusv_callback(state):
    global signal_queue
    print 'Got state: %s' % str(state)
    if SECONDARY_POWER in state:
        signal_queue.put('shutdown')
    elif PRIMARY_POWER in state:
        signal_queue.put('clear_shutdown')


def main():
    parser = argparse.ArgumentParser(description='PyUSV daemon')
    parser.add_argument('-c', '--config', default=DEFAULT_CONFIG_FILE, dest='config_file',
                        help='Path to the config file. Default: %s' % DEFAULT_CONFIG_FILE)

    args = parser.parse_args()
    if not os.path.isfile(args.config_file):
        print 'Config file %s does not exist!' % args.config_file
        sys.exit(1)

    with open(args.config_file, 'r') as f:
        configuration = ast.literal_eval(f.read())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    pyusv = PyUSV(device=configuration['i2c']['device'],
                  device_address=configuration['i2c']['device_address'])
    pyusv.register_callback_method(pyusv_callback)
    pyusv.start()

    shutdown_counter = 0
    while True:
        try:
            signum = signal_queue.get(block=True, timeout=1)
            if signum in [2, 15]:
                break
            elif signum in ['shutdown']:
                shutdown_counter += 1
                print 'shutdown_counter=%d' % shutdown_counter
            elif signum in ['clear_shutdown']:
                print 'Shutdown cleared'
                shutdown_counter = 0
        except Empty:
            if shutdown_counter:
                if shutdown_counter == configuration['internals']['turnoff_hold_time']:
                    print 'Shutting down PI'
                    pyusv.shutdown(turnoff_time=configuration['internals']['turnoff_time'], shutdown_cmd=configuration['shutdown_cmd'])
                    break
                shutdown_counter += 1
                print 'shutdown_counter=%d' % shutdown_counter
    pyusv.stop()


if __name__ == "__main__":
    main()

