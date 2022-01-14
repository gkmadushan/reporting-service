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


def send_email(to, subject, msg, html=False):
    receivers = ['gkmadushan@gmail.com']
    message = MIMEMultipart('alternative')
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = to
    message.attach(MIMEText(msg, 'plain'))
    if html != False:
        message.attach(MIMEText(html, 'html'))

    try:
        smtp_driver = SMTP(smtp_host, smtp_port)
        smtp_driver.starttls()
        smtp_driver.ehlo()
        smtp_driver.login(smtp_username, smtp_password)
        smtp_driver.sendmail(sender, receivers, message.as_string())
        smtp_driver.quit()
        return True
    except SMTPException as e:
        return e
