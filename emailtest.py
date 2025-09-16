import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_email(to_email, subject, body):
    # Create MIMEText email
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = SMTP_USERNAME
    msg["To"] = to_email

    try:
        # Connect to Gmail SMTP
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)

        # Send email
        server.sendmail(SMTP_USERNAME, to_email, msg.as_string())
        print("✅ Email sent successfully!")

    except Exception as e:
        print("❌ Error sending email:", e)
    finally:
        server.quit()


if __name__ == "__main__":
    send_email(
        "saimchisti@gmail.com",
        "Test Email from Python Script",
        "Hello Saim, this is a test email sent using Python and Gmail SMTP!"
    )
