import time
import RPi.GPIO as GPIO
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
import requests
import json
import netifaces
import BlynkLib
from BlynkTimer import BlynkTimer

# GPIO Pin Setup
TRIG = 17
ECHO = 27
LED_LOW = 16
LED_MID = 20
LED_HIGH = 21
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.setup(LED_LOW, GPIO.OUT)
GPIO.setup(LED_MID, GPIO.OUT)
GPIO.setup(LED_HIGH, GPIO.OUT)

# MQTT Configuration
MQTT_PORT = 1883
MQTT_SERVER = "192.168.66.221"
PUBLISH_TOPIC = "/water_level"
SUBSCRIBE_TOPIC = "/feedback"
SUBSCRIBE_TOPIC_VALUE = "/TestValue"

# Blynk Configuration
BLYNK_AUTH_TOKEN = 'k-WrbdYgDqZTP1vPsOK5l1hTYV2hIPbh'
blynk = BlynkLib.Blynk(BLYNK_AUTH_TOKEN)

# Line API Configuration
LINE_TOKEN = 'dEgASdz4z3jv1SvXFjOPSPjlPNFqe/95jWorRdcC+j2u+l2bCVVApcqJIEn4uyeZoJr7rby4fJo7pmJuoGpnJYLscAp4uNh9F5wx8SpbXOVHA19HT1Z17vGpKCLNbhxZAotvxlNOLCNL7w4unv1rRgdB04t89/1O/w1cDnyilFU='
LINE_USER_ID = 'Ua180ca3b6aa661049847c5fb1af63ff0'

# Function to send messages via Line API
def send_line_message(token, user_id, message):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    payload = {
        "to": user_id,
        "messages": [
            {
                "type": "text",
                "text": message
            },
            {
                "type": "sticker",
                "packageId": "11537",
                "stickerId": "52002767"
            }
        ]
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        print("Message and sticker sent successfully.")
    else:
        print(f"Failed to send message and sticker. Status code: {response.status_code}")

# Function to get IP Address of wlan0
def get_ip_address(interface='wlan0'):
    try:
        ip_address = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]['addr']
        return ip_address
    except (KeyError, IndexError, ValueError):
        return "Unknown"

# Function to get distance from Ultrasonic Sensor
def get_distance():
    GPIO.output(TRIG, GPIO.LOW)
    time.sleep(0.001)
    GPIO.output(TRIG, GPIO.HIGH)
    time.sleep(0.0001)
    GPIO.output(TRIG, GPIO.LOW)

    pulse_start = pulse_end = time.time()
    timeout_start = time.time()
    while GPIO.input(ECHO) == GPIO.LOW:
        pulse_start = time.time()
        if pulse_start - timeout_start > 1:
            return None

    timeout_start = time.time()
    while GPIO.input(ECHO) == GPIO.HIGH:
        pulse_end = time.time()
        if pulse_end - timeout_start > 1:
            return None

    pulse_duration = pulse_end - pulse_start
    distance = (pulse_duration * 34300) / 2 + 2 
    return round(distance, 2)

# MQTT Callback Functions
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT Server with result code " + str(rc))
    client.subscribe(SUBSCRIBE_TOPIC)
    client.subscribe(SUBSCRIBE_TOPIC_VALUE)

def on_message(client, userdata, msg):
    if msg.topic == SUBSCRIBE_TOPIC:
        if msg.payload == b'true':
            print("Action enabled.")
        elif msg.payload == b'false':
            print("Action disabled.")
    elif msg.topic == SUBSCRIBE_TOPIC_VALUE:
        try:
            value = int(msg.payload.decode('utf-8'))
            print(f"Received value from feedback: {value}")
        except ValueError:
            print("Invalid feedback value received.")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_SERVER, MQTT_PORT)
client.loop_start()

# Initialize list to store water level readings
water_level_readings = []

# Function to calculate the average of the last 10 readings
def calculate_average(readings, max_length=5):
    if len(readings) == 0:
        return None
    if len(readings) > max_length:
        readings.pop(0)  # Remove the oldest reading to maintain max length
    return sum(readings) / len(readings)

# Main Loop
try:
    while True:
        water_level = get_distance()
        if water_level is not None:
            water_level_readings.append(water_level)  # Add new reading to the list
            average_water_level = calculate_average(water_level_readings)

            if average_water_level is not None:
                print(f"Water Level (Average): {average_water_level:.2f} cm")  # Display average level

                # Publish average water level to MQTT
                publish.single(PUBLISH_TOPIC, f"Average Water Level: {average_water_level:.2f} cm", hostname=MQTT_SERVER)

                # Send average water level to Blynk
                blynk.virtual_write(0, int(average_water_level))  # Integer to V0
                blynk.virtual_write(3, average_water_level)  # Float to V3

                # Determine status based on average water level
                if average_water_level > 50:
                    status = "Normal"
                    GPIO.output(LED_LOW, GPIO.HIGH)
                    GPIO.output(LED_MID, GPIO.LOW)
                    GPIO.output(LED_HIGH, GPIO.LOW)
                elif 35 < average_water_level <= 50:
                    status = "Warning"
                    GPIO.output(LED_LOW, GPIO.LOW)
                    GPIO.output(LED_MID, GPIO.HIGH)
                    GPIO.output(LED_HIGH, GPIO.LOW)
                else:
                    status = "Dangerous"
                    GPIO.output(LED_LOW, GPIO.LOW)
                    GPIO.output(LED_MID, GPIO.LOW)
                    GPIO.output(LED_HIGH, GPIO.HIGH)

                    # Send alert via LINE API
                    raspberry_pi_ip = get_ip_address('wlan0')
                    alert_message = (
                        f"The water level has surpassed the limit.\n"
                        f"Average Water Level: {average_water_level:.2f} cm\n"
                        f"Raspberry Pi IP: {raspberry_pi_ip}\n"
                        f"Please check the safety of the water level!"
                    )
                    send_line_message(LINE_TOKEN, LINE_USER_ID, alert_message)

                    event_message = (
                        f"The water level has surpassed the limit.\n"
                        f"Average Water Level: {average_water_level:.2f} cm\n"
                        f"Raspberry Pi IP: {raspberry_pi_ip}\n"
                        f"Please check the safety of the water level!"
                    )
                    blynk.log_event("water_level_high", event_message)

                # Send status to Blynk
                blynk.virtual_write(2, status)

        # Run Blynk and sleep for 2 seconds
        blynk.run()
        time.sleep(2)

except KeyboardInterrupt:
    print("Program stopped by user.")

finally:
    GPIO.cleanup()
    client.loop_stop()

