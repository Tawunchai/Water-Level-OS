import time
import RPi.GPIO as GPIO
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
import requests
import json
import netifaces

# การตั้งค่า GPIO สำหรับ Ultrasonic Sensor และ LED
TRIG = 17  # Pin Rx
ECHO = 27  # Pin Tx
LED_LOW = 16  # LED เมื่อ water_level < 20
LED_MID = 20  # LED เมื่อ water_level > 20 และ < 23
LED_HIGH = 21  # LED เมื่อ water_level > 23
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.setup(LED_LOW, GPIO.OUT)
GPIO.setup(LED_MID, GPIO.OUT)
GPIO.setup(LED_HIGH, GPIO.OUT)

# การตั้งค่า MQTT
port = 1883
Server_ip = "192.168.66.221"
Publish_Topic = "/water_level"
Subscribe_Topic = "/feedback"
Subscribe_TopicValue = "/TestValue"

# ฟังก์ชัน callback สำหรับ MQTT
def on_connect(client, userdata, flags, rc):
    print("เชื่อมต่อสำเร็จด้วยรหัสผลลัพธ์ " + str(rc))
    client.subscribe(Subscribe_Topic)
    client.subscribe(Subscribe_TopicValue)

def on_message(client, userdata, msg):
    if msg.topic == Subscribe_Topic:
        if msg.payload == b'true':
            print("การกระทำบางอย่างถูกเปิดใช้งาน")
        elif msg.payload == b'false':
            print("การกระทำบางอย่างถูกปิดใช้งาน")
    elif msg.topic == Subscribe_TopicValue:
        try:
            value = int(msg.payload.decode('utf-8'))
            print(f"ได้รับค่าจาก Feedback: {value}")
        except ValueError:
            print("ค่าที่ได้รับไม่ถูกต้อง")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(Server_ip, port)
client.loop_start()

# ฟังก์ชันดึง IP address ของ Raspberry Pi
def get_ip_address(interface="wlan0"):
    try:
        ip_address = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]['addr']
        return ip_address
    except (ValueError, KeyError):
        print("ไม่สามารถหาค่า IP address ของ interface นี้ได้")
        return None

# ฟังก์ชันสำหรับส่งข้อความและสติ๊กเกอร์ผ่าน Line API
def send_line_message(token, user_id, message):
    # ดึง IP address ของ Raspberry Pi
    ip_address = get_ip_address("wlan0")
    
    if ip_address:
        # เพิ่ม IP address ลงในข้อความ
        message_with_ip = f"{message}\nRaspberry Pi IP: {ip_address}\nPlease check the safety of the water level!"
    else:
        message_with_ip = f"{message}\nUnable to fetch IP address"
    
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
                "text": message_with_ip
            },
            {
                "type": "sticker",
                "packageId": "11537",  # ใส่ packageId ของสติ๊กเกอร์ที่ต้องการ
                "stickerId": "52002767"  # ใส่ stickerId ของสติ๊กเกอร์ที่ต้องการ
            }
        ],
        "notificationDisabled": False
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    
    if response.status_code == 200:
        print("Message and sticker sent successfully.")
    else:
        print(f"Failed to send message and sticker. Status code: {response.status_code}")


# ฟังก์ชันวัดระยะทางจาก Ultrasonic Sensor
def get_distance():
    # ส่งสัญญาณ LOW เพื่อให้แน่ใจว่าเซนเซอร์พร้อมทำงาน
    GPIO.output(TRIG, GPIO.LOW)
    time.sleep(0.05)  # หน่วงเวลา 50 ms
    
    # ส่งสัญญาณ HIGH เป็นเวลา 10 µs
    GPIO.output(TRIG, GPIO.HIGH)
    time.sleep(0.00001)  # 10 µs
    GPIO.output(TRIG, GPIO.LOW)
    
    # จับเวลาที่ ECHO เปลี่ยนจาก LOW เป็น HIGH (เริ่มรับสัญญาณสะท้อน)
    timeout_start = time.time()
    while GPIO.input(ECHO) == GPIO.LOW:
        pulse_start = time.time()
        if pulse_start - timeout_start > 1:  # ตั้ง timeout 1 วินาที
            print("Timeout: No echo signal received")
            return None
    
    # จับเวลาที่ ECHO เปลี่ยนจาก HIGH เป็น LOW (สิ้นสุดการรับสัญญาณสะท้อน)
    timeout_start = time.time()
    while GPIO.input(ECHO) == GPIO.HIGH:
        pulse_end = time.time()
        if pulse_end - timeout_start > 1:  # ตั้ง timeout 1 วินาที
            print("Timeout: Echo signal too long")
            return None
    
    # คำนวณระยะทาง
    pulse_duration = pulse_end - pulse_start  # เวลาที่คลื่นเดินทางไปกลับ
    distance = (pulse_duration * 34300) / 2  # ระยะทางใน cm (หาร 2 เพราะไป-กลับ)
    
    # คืนค่าเป็นเลขทศนิยม 2 ตำแหน่ง
    return round(distance, 2)


try:
    while True:
        water_level = get_distance()
        print(f"ระดับน้ำ: {water_level} cm")
        
        message = f"Water Level: {water_level} cm"
        publish.single(Publish_Topic, message, hostname=Server_ip)
        print(f"เผยแพร่ข้อความ: {message}")
        
        if water_level < 20:
            GPIO.output(LED_LOW, GPIO.HIGH)
            GPIO.output(LED_MID, GPIO.LOW)
            GPIO.output(LED_HIGH, GPIO.LOW)
        elif 20 <= water_level < 23:
            GPIO.output(LED_LOW, GPIO.LOW)
            GPIO.output(LED_MID, GPIO.HIGH)
            GPIO.output(LED_HIGH, GPIO.LOW)
        elif water_level >= 23:
            GPIO.output(LED_LOW, GPIO.LOW)
            GPIO.output(LED_MID, GPIO.LOW)
            while water_level >= 23:
                GPIO.output(LED_HIGH, GPIO.HIGH)
                time.sleep(0.5)
                GPIO.output(LED_HIGH, GPIO.LOW)
                time.sleep(0.5)
                
                token = 'fu2y79teeVFwE577ZCbwXOyHIYcYYK4rrubebwDEcMouX8PNzDZ4zCsnW+quBLQ9RxcaME5vQ3I1BW82d1/ZYezvWklVMUk+EGGfXRmI4jxXkFCtWQ+PRtJs9DsHDRjIqmrwKi6sd/Xovtb4QbodrwdB04t89/1O/w1cDnyilFU='
                user_id = 'U3af93a2f92b1048757172584d47571c8'
                message = f"The water level has surpassed the limit. Current water level: {water_level} cm"
                
                send_line_message(token, user_id, message)
            
                water_level = get_distance()
        
        time.sleep(2)

except KeyboardInterrupt:
    print("โปรแกรมถูกหยุดโดยผู้ใช้")

finally:
    GPIO.cleanup()
    client.loop_stop()

