import RPi.GPIO as GPIO
import time
import datetime
import threading
import busio
import digitalio
import board
import adafruit_pcd8544
import spidev
import cgitb ; cgitb.enable() 
import requests
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from adafruit_bus_device.spi_device import SPIDevice

#kleuren
# PIN 17 = geel
# PIN 18 = bruin
# PIN 26 = wit
# PIN 16 = paars

#ubeac variabelen dit zijn mijn ubeac gegevens
url = "http://arthurdroeshaut.hub.ubeac.io/iotessarthurdroeshaut"
uid = "iotessarthur droeshaut"



GPIO.setmode(GPIO.BCM)

# de pinnen die gebruikt worden en de manier waarop deze gebruikt worden met als voorbeeld de knoppen staan op 12 en 16.
GPIO.setup(22,GPIO.OUT) #geel
GPIO.setup(27,GPIO.OUT) #zwart
GPIO.setup(25,GPIO.OUT) #groen
GPIO.setup(5,GPIO.OUT) #oranje
GPIO.setup(17, GPIO.OUT)
GPIO.setup(18, GPIO.IN)
GPIO.setup(26, GPIO.OUT)
GPIO.setup(12, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(17, 0)


# globale variabelen en alsook de rotation variabele zodat ik deze meerdere keren kan gebruiken.
global is_triggered
global trap_status
global alarm_count
rotation = [
                [1,0,0,0],
                [1,1,0,0],
                [0,1,0,0],
                [0,1,1,0],
                [0,0,1,0],
                [0,0,1,1],
                [0,0,0,1],
                [1,0,0,1]
                ]


#als eerste knop maken we de resetknop aan.
def resetknop():
    global is_triggered

    # Set up GPIO voor de resetknop dit is pin12 en de relay pin 26 want deze moet ook uitgaan indien ik op de knop druk.
    button_pin = 12  
    relay_pin = 26  
    GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(relay_pin, GPIO.OUT)

#hier staat dat als de knop is ingedrukt het relay lichtje moet stoppen met branden.
    while True:
        button_state = GPIO.input(button_pin)
        if button_state == GPIO.LOW:
            is_triggered = False
            GPIO.output(26,1)  # om de relay uit te zetten.
            time.sleep(0.1)

        time.sleep(0.2)  # kleine delay toevoegen aan de knop. 
    
    
# nu komt de triggerknop, deze moet de val laten afgaan, dus de motor laten draaien en het lampje laten branden.    
def triggerknop():
    global is_triggered
    global alarm_count
    global rotation
    
    # Setup the GPIO voor de knop en de relais de knop is pin 16 en de relais weeral pin 26
    button_pin = 16
    relay_pin = 26 #lampje
    motor_pins = [22, 27, 5, 25] #de gebruikte pinnen voor de motor.
    GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(relay_pin, GPIO.OUT)
    for pin in motor_pins:
        GPIO.setup(pin, GPIO.OUT)
    
# hier ook weer de knop wordt ingedrukt en de acties vinden plaats, nu wordt de rotatie uitgevoerd die onder variabele staan en wordt het relais lampje aangezet.    
    while True:
        button_state = GPIO.input(button_pin)
        if button_state == GPIO.LOW:
            is_triggered = True
            GPIO.output(26,0)  # zet de relais aan.
            time.sleep(0.1)
            
            # draai de motor.
            for _ in range(80):
                for halfstep in range(8):
                    for pin in range(4):
                        GPIO.output(motor_pins[pin], rotation[halfstep][pin])
                    time.sleep(0.001)
            
            time.sleep(1)  # deze functie zodat je dit niet kan blijven indrukken zonder problemen, zodat er tijd tussen zit.
        
        time.sleep(0.2)  # kleine delay toevoegen aan de knop.


    
# over naar de sensor. ter info mijn sensor zit aan de zijkant en de afstand van de zijkant tot de andere zijkant is 12cm. dus als er een muis in zit is de afstand zeker kleiner dan 6cm
def sensor():
    global is_triggered
    global alarm_count
    alarm_count = 0
    is_triggered = True
    while True:
        global trap_status
        GPIO.output(17,1)
        time.sleep(0.0001)
        GPIO.output(17,0)
#zolang de input van 18 dus de sensor 0 is gebeurt er niks.
        while (GPIO.input(18) == 0):
            pass
        signal_high = time.time()

        while (GPIO.input(18) == 1):
            pass
        signal_low = time.time()

        timepassed = signal_low - signal_high
#om de afstand van de sensor te meten
        distance_sensor = round(timepassed * 17000)
        print("Distance: ", distance_sensor," cm")

        #relay bordje
        if distance_sensor <= 6  and is_triggered == False:
            # Als de afstand korter is dan 6cm dan zit er een muis in de val waardoor er op de LCD "Triggered" komt te staan de de muizen counter omhoog gaat
            GPIO.output(26,0)
            print("Mouse detected!")
            trap_status = "Triggered"
            alarm_count += 1
            is_triggered = True
#zolang de afstand niet kleiner is dan 10cm zal de val op armed blijven staan. binnen de sensor functie.
        elif distance_sensor <= 10:
            trap_status = "Armed"

        else:
            #Als de afstand van de sensor weer hoog is, is de val terug in "armed" mode
            is_triggered = False
            trap_status = "Armed"


        time.sleep(2)

# nu gaan we de lcd maken.
def lcd():
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

    # Initialize display
    dc = digitalio.DigitalInOut(board.D23)  # data/command
    cs1 = digitalio.DigitalInOut(board.CE1)  # chip select CE1 for display
    reset = digitalio.DigitalInOut(board.D24)  # reset
    display = adafruit_pcd8544.PCD8544(spi, dc, cs1, reset, baudrate= 1000000)
    display.bias = 4
    display.contrast = 60
    display.invert = True


#  clear het lcd scherm van vorige configuraties.  altijd call show oproepen om de display duidelijk te laten blijken.
    display.fill(0)
    display.show()
    current_time = datetime.datetime.now()
    while True:
        display.show()

        font = ImageFont.load_default()

        image = Image.new('1', (display.width, display.height))
        draw = ImageDraw.Draw(image)

        draw.rectangle((0, 0, display.width, display.height), outline=255, fill=255)
# hier voeg je de tijd toe en hieronder de status van de val en de counter van de triggered vallen.
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M:%S")
        text = "tijd: " + str(current_time)
        # Write some text.
        nummer=4
        draw.text((1,0), text , font=font)
        draw.text((1,8), trap_status , font=font)
        draw.text((1,24), (str(alarm_count)), font=font)
        # draw.text((1,32), (str(nummer)), font=font)
        display.image(image)
        display.show()
        

        #ubeac hieronder wordt de ubeac geprogrammeerd.
        if trap_status == "Triggered":
            trap_ubeac = 100
        else:
            trap_ubeac = 0
                #deze vorige commando's zijn omdat je geen tekst naar ubeac kunt sturen, dus doe ik het zo, als de trap getriggered is, geeft die een impuls van count 100 anders blijft de count minder dan 100 en is de val dus niet afgegaan.
                
            #hier wordt de data meegegeven voor mijn ubeac
        data = {
            "id": uid,
            "sensors" : [{
                'id': "trap status",
                'data': trap_ubeac
                }, {
                'id': "alarm count",
                'data': alarm_count}]
            }
        r = requests.post(url, verify = False, json=data)
        print("trap status :", trap_status, "\nalarm count", alarm_count)
        time.sleep(1)

# hieronder wordt de motordraai weergegeven.
def motordraai():
    while True:
        if is_triggered:
            control_pins = [22,27,5,25]
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
                [1,0,0,1]
                ]

                for i in range(80):
                    for halfstep in range(8):
                        for pin in range(4):
                            GPIO.output(control_pins[pin], halfstep_seq[halfstep][pin])
                        time.sleep(0.001)
        else:
            # Stop de motor door alle control pins uit te zetten.
            control_pins = [22,27,5,25]
            for pin in control_pins:
                GPIO.output(pin, 0)


#hieronder gebruik gemaakt van multithreading.
thread1 = threading.Thread(target=sensor)
thread2 = threading.Thread(target=lcd)
thread3 = threading.Thread(target=resetknop)
thread4 = threading.Thread(target=motordraai)
thread5 = threading.Thread(target=triggerknop)


thread1.start()
thread2.start()
thread3.start()
thread4.start()
thread5.start()
