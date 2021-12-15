import os
from dotenv import load_dotenv
from smtplib import SMTP, SMTPException
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

sender = os.getenv('EMAIL_SENDER')
smtp_host = os.getenv('EMAIL_HOST')
smtp_port = os.getenv('EMAIL_PORT')
smtp_username = os.getenv('EMAIL_USERNAME')
smtp_password = os.getenv('EMAIL_PASSWORD')

def send_email(to, subject, msg, html = False):
    receivers = ['gkmadushan@gmail.com']
    message = MIMEMultipart('alternative')
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = to
    message.attach(MIMEText(msg, 'plain'))
    if html!=False:
        message.attach(MIMEText(html, 'html'))

    try:
        smtpObj = SMTP(smtp_host, smtp_port)
        smtpObj.starttls()
        smtpObj.ehlo()
        smtpObj.login(smtp_username, smtp_password) 
        smtpObj.sendmail(sender, receivers, message.as_string())      
        smtpObj.quit();   
        return True
    except SMTPException as e:
        return e