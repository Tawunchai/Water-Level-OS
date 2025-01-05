import requests
import json

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
            }
        ],
        "notificationDisabled": False
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    
    if response.status_code == 200:
        print("Message sent successfully.")
    else:
        print(f"Failed to send message. Status code: {response.status_code}")

if __name__ == "__main__":
    token = 'fu2y79teeVFwE577ZCbwXOyHIYcYYK4rrubebwDEcMouX8PNzDZ4zCsnW+quBLQ9RxcaME5vQ3I1BW82d1/ZYezvWklVMUk+EGGfXRmI4jxXkFCtWQ+PRtJs9DsHDRjIqmrwKi6sd/Xovtb4QbodrwdB04t89/1O/w1cDnyilFU='
    user_id = 'U3af93a2f92b1048757172584d47571c8'
    message = 'test from rpi "water level'
    
    send_line_message(token, user_id, message)
