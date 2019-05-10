import RPi.GPIO as GPIO
import time
import threading as th

GPIO.setmode(GPIO.BCM)

def leds():
    led = 21
    
    GPIO.setup(led,GPIO.OUT)
    while True:
        GPIO.output(led, GPIO.HIGH)
        time.sleep(0.5)
        GPIO.output(led, GPIO.LOW)
        time.sleep(0.5)

led = th.Thread(target=leds)
led.start()