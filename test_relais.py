import RPi.GPIO as GPIO
import time

print("Starting Program")

GPIO.setmode(GPIO.BCM)

relais1 = 6
relais2 = 13
relais3 = 19
relais4 = 26

GPIO.setup(relais1, GPIO.OUT)
GPIO.setup(relais2, GPIO.OUT)
GPIO.setup(relais3, GPIO.OUT)
GPIO.setup(relais4, GPIO.OUT)

print("Setup completed / Starting Loop")

while True:
    print("Relais 1 & 2 active")
    GPIO.output(relais1, 1)
    GPIO.output(relais2, 1)
    GPIO.output(relais3, 0)
    GPIO.output(relais4, 0)
    time.sleep(15)
    print("Relais 3 & 4 active")
    GPIO.output(relais3, 1)
    GPIO.output(relais4, 1)
    GPIO.output(relais1, 0)
    GPIO.output(relais2, 0)
    time.sleep(15)
    
