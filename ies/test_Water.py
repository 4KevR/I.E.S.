#Das ist das Test/Kalibrierungsprogramm für die Pumpe
#Programmiert von Kevin Wiesner

#Variablen+Implementierungen
import RPi.GPIO as GPIO
import time
import sys

#GPIO-Pins
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(14, GPIO.OUT) #Pumpenlauf
GPIO.setup(15, GPIO.OUT) #vorwärts/rückwärts
GPIO.output(14, GPIO.LOW)
GPIO.output(15, GPIO.HIGH)

control_pins = [6, 13, 19, 26]
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

#Input für die Pumpenkalibierung
horu = input("Eingabe Pumpe hoch oder runter (h/r): ")
stufe = input("Stufe des Potentiometers: ")

if horu == "h":
    GPIO.output(15, GPIO.LOW)
elif horu == "r":
    GPIO.output(15, GPIO.HIGH)
else:
    print("Falsche Eingabe")
    sys.exit()
    
print("Setze Potentiometer auf Position...")

#Potentiometer auf angefragte Position setzen
for i in range(int(90+168*(int(stufe)/12))):
    for halfstep in range(8):
        for pin in range(4):
            GPIO.output(control_pins[pin],halfstep_seq[halfstep][pin])
        time.sleep(0.002)
for pin in control_pins:
    GPIO.output(pin, 0)
        
#PUMPE
start = input("Start durch irgenteine Taste bestätigen: ")
GPIO.output(14, GPIO.HIGH)
start_time = time.time()
stop = input("Stopp durch irgenteine Taste bestätigen: ")
stop_time = time.time()
GPIO.output(14, GPIO.LOW)

#Benötigte Zeit
print("\nBenötigte Zeit:", (stop_time-start_time), "s")
print("Berechnete Leistung:", 3600000/(stop_time-start_time), "W")
     
#Ende
#Potentiometer auf 0 setzen
control_pins = [26, 19, 13, 6]
for i in range(int(90+168*(int(stufe)/12))):
    for halfstep in range(8):
        for pin in range(4):
            GPIO.output(control_pins[pin],halfstep_seq[halfstep][pin])
        time.sleep(0.002)        
for pin in control_pins:
    GPIO.output(pin, 0)
    
#Pumpenrelais auf 0 setzen
GPIO.output(14, GPIO.LOW)
GPIO.output(15, GPIO.HIGH)
print("Beendet")