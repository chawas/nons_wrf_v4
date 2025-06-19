import smtplib

EMAIL_USER = "metcfo@gmail.com"
EMAIL_PASS = "ebmabmozrvioyezw"

try:
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        print("✅ Login successful!")
except smtplib.SMTPAuthenticationError as e:
    print("❌ Authentication failed:", e)
except Exception as e:
    print("❌ Other error:", e)
