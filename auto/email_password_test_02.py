import smtplib
from email.message import EmailMessage

EMAIL_USER = "metcfo@gmail.com"
EMAIL_PASS = "ebmabmozrvioyezw"

msg = EmailMessage()
msg["Subject"] = "Test Email"
msg["From"] = EMAIL_USER
msg["To"] = "metcfo@gmail.com"
msg.set_content("Test email via STARTTLS")

try:
    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.set_debuglevel(1)  # Verbose debug
        smtp.ehlo()
        smtp.starttls()  # This begins the encryption
        smtp.ehlo()  # Re-identify after STARTTLS
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)
        print("✅ Email sent successfully!")
except Exception as e:
    print(f"❌ Failed to send email: {e}")

