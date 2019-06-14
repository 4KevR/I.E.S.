import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

class Stepper():
    def __init__(self):
        self.__stepper1 = 6
        self.__stepper2 = 13
        self.__stepper3 = 19
        self.__stepper4 = 26
        GPIO.setup(self.__stepper1,GPIO.OUT)
        GPIO.setup(self.__stepper2,GPIO.OUT)
        GPIO.setup(self.__stepper3,GPIO.OUT)
        GPIO.setup(self.__stepper4,GPIO.OUT)
        
    def step(self,w1,w2,w3,w4):
        GPIO.output(self.__stepper1,w1)
        GPIO.output(self.__stepper2,w2)
        GPIO.output(self.__stepper3,w3)
        GPIO.output(self.__stepper4,w4)
        time.sleep(0.05)

stepper = Stepper()
for i in range(32):
    stepper.step(1,0,0,0)
    stepper.step(1,1,0,0)
    stepper.step(0,1,0,0)
    stepper.step(0,1,1,0)
    stepper.step(0,0,1,0)
    stepper.step(0,0,1,1)
    stepper.step(0,0,0,1)
    stepper.step(1,0,0,1)

stepper.step(0,0,0,0)