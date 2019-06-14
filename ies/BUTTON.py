#Das ist das Programm für die Multifunktionalen Buttons am BRAIN
#Programmiert von Kevin Wiesner

#SMD
#Brain ist an und Programm ist aus = ROT - state 0
#Programm gestartet = GRÜN - state 0
#Programm ist gerade am Starten oder startet neu - state 1
#Pis werden ausgeschaltet = ROT blinkt - state 2
#Pis werden neu gestartet = BLAU - state 3

import RPi.GPIO as GPIO
import time
import threading as th
import os

GPIO.setmode(GPIO.BCM)

button1 = 4
vorher = 0

GPIO.setup(button1,GPIO.IN)

#########################################################################
#Klassen des Programms
class SMD(th.Thread):
    def __init__(self):
        th.Thread.__init__(self)
        self.state = 0
        self.buttonLight = 20
        self.retry = 0
        GPIO.setup(self.buttonLight, GPIO.OUT)
    
    def run(self):  
        while True:
            if self.state == 2:
                while True:
                    GPIO.output(self.buttonLight, GPIO.HIGH)
                    time.sleep(0.2)
                    GPIO.output(self.buttonLight, GPIO.LOW)
                    time.sleep(0.2)
            elif self.state == 3:
                GPIO.output(self.buttonLight, GPIO.HIGH)
                time.sleep(0.5)
                GPIO.output(self.buttonLight, GPIO.LOW)
                time.sleep(0.2)
            elif testactive():
                GPIO.output(self.buttonLight, GPIO.HIGH)
                with open("/var/www/html/output/data.txt", "r") as file:
                    text = file.readlines()
                    if len(text) > 0 and text[0] == "0":
                        time.sleep(0.5)
                        GPIO.output(self.buttonLight, GPIO.LOW)
                        time.sleep(0.5)
                        self.state = 1
                        self.retry += 1
                        if self.retry > 20:
                            task=os.popen('echo %s|sudo -S %s'%('serverAI50', 'screen -XS execute kill'))
                            self.retry = 0
                            log("Programm wurde aufgrund von eines inaktiven Pis geschlossen")
                    elif self.state == 1:
                        self.state = 0
                        self.retry = 0
            else:
                GPIO.output(self.buttonLight, GPIO.LOW)
            
#Funktionen des Programms
def log(text):
    maxtext = 30 #maximale Länge eines Textes
    tab = ""
    for i in range(len(time.strftime("[%d.%m.%Y %H:%M:%S]")), maxtext):
        tab = tab + "."
    print(time.strftime("[%d.%m.%Y %H:%M:%S]")+tab+text)

def testactive():
    return "python3 /home/BRAIN/ies/BRAIN.py" in " ".join(os.popen("ps aux").readlines())

def write(task):
    if testactive() and lights.state == 0:
        with open("/var/www/html/input/queue.txt", "a") as file:
            file.write(task+"\n")
    else:
        log("Starte zuerst das Programm oder Task wurde schon gestartet...")

#########################################################################
#Programm
lights = SMD()
lights.start()

while True:
    if GPIO.input(button1) == GPIO.HIGH and vorher == 0:
        state = 1
        state_vorher = 0
        click = 0
        counter = 0
        while counter != 100:
            if state != state_vorher:
                if state == 1:
                    log("click")
                    click += 1
            time.sleep(0.01)
            state_vorher = state
            state = GPIO.input(button1)
            counter += 1
        if click == 3:
            log("Starte die Pis neu")
            os.system("/UTILITY_reboot.sh")
            lights.state = 3
        elif click == 2:
            log("Schalte die Pis aus")
            os.system("/UTILITY_shutdown.sh")
            lights.state = 2
        elif click == 1 and GPIO.input(button1) == GPIO.LOW:
            if testactive():
                log("Schließe das Programm")
                write("close")
            else:
                log("Starte das Programm")
                os.system("/UTILITY_start.sh")
        elif click == 1 and GPIO.input(button1) == GPIO.HIGH:
            log("Starte das Programm neu")
            write("restart")
        vorher = 1
    elif GPIO.input(button1) == GPIO.LOW:
        vorher = 0
    time.sleep(0.1)