import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# ตั้งค่าข้อมูลอีเมล
from_email = "tawunchaien@gmail.com"  # อีเมลผู้ส่ง
password = "paqb ajjj mafd zsrr"  # รหัสผ่าน (หรือ App Password)
to_email = "b6534721@g.sut.ac.th"  # อีเมลผู้รับ

# สร้างข้อความอีเมล
msg = MIMEMultipart()
msg['From'] = from_email
msg['To'] = to_email
msg['Subject'] = "Water Level Exceedance Report"  # หัวข้ออีเมล

# เนื้อหาในอีเมล
email_body = """
This report focuses on the monitoring and analysis of water level exceedance.

Water level exceedance refers to a situation in which the water level in a particular area surpasses a predefined threshold, which could be due to various factors such as heavy rainfall, flooding, or other environmental changes.

The objective of this report is to identify the causes of water level exceedance and recommend appropriate actions to mitigate potential risks.
"""
msg.attach(MIMEText(email_body, 'plain'))

# แนบไฟล์ (ถ้ามี)
file_path = "/home/os/Project/DataLogger/data_water.csv"  # เปลี่ยนเป็นพาธของไฟล์ที่ต้องการแนบ
try:
    with open(file_path, "rb") as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename={file_path.split("/")[-1]}'  # ใช้ชื่อไฟล์ที่แนบ
        )
        msg.attach(part)
except FileNotFoundError:
    print(f"File not found: {file_path}, skipping attachment.")

# ตั้งค่าเซิร์ฟเวอร์ SMTP
try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(from_email, password)  # ล็อกอินอีเมล
    server.send_message(msg)  # ส่งอีเมล
    print("Email sent successfully!")
except Exception as e:
    print(f"Failed to send email: {e}")
finally:
    server.quit()
