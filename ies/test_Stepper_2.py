import RPi.GPIO as GPIO
import time
import sys

GPIO.setmode(GPIO.BCM)

if sys.argv[1] == "+":
    control_pins = [6, 13, 19, 26]
else:
    control_pins = [26, 19, 13, 6]

for pin in control_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, 0)
    
halfstep_seq = [
    [1,0,0,0],
    [1,1,0,0],
    [0,1,0,0],
    [0,1,1,0],
    [0,0,1,0],
    [0,0,1,1],
    [0,0,0,1],
    [1,0,0,1],
    ]

for i in range(440):
    for halfstep in range(8):
        for pin in range(4):
            GPIO.output(control_pins[pin],halfstep_seq[halfstep][pin])
        time.sleep(0.002)
            
GPIO.cleanup()