import streamlit as st
import pandas as pd
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, timedelta
from streamlit_autorefresh import st_autorefresh

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Booking System", layout="centered")
st.title("Measurement Setup Booking System")

FIREBASE_DB = "https://book1-bc265-default-rtdb.asia-southeast1.firebasedatabase.app"

# ThingsBoard
TB_DEVICE_TOKEN = "Bj4z82RwfDPw3334Jkth"
TB_URL = f"https://thingsboard.cloud/api/v1/{TB_DEVICE_TOKEN}/telemetry"

# Email (SMTP)
SMTP_EMAIL = "surface7nis@gmail.com"
SMTP_PASSWORD = "lslcfalitzjzdctp "  # 16-character app password
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587  # TLS

# -----------------------------
# AUTO-REFRESH
# -----------------------------
st_autorefresh(interval=5000, key="live_refresh")

# -----------------------------
# EMAIL FUNCTION
# -----------------------------
def send_email(to_email, name, start, end):
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_EMAIL
        msg["To"] = to_email
        msg["Subject"] = "Booking Confirmation"

        body = f"""
Hello {name},

Your booking has been confirmed.

Start Date: {start}
End Date: {end}

Thank you.
"""
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Email failed: {e}")
        return False

# -----------------------------
# FIREBASE FUNCTIONS
# -----------------------------
def get_system_status():
    try:
        r = requests.get(f"{FIREBASE_DB}/system_status.json", timeout=5)
        return r.json()
    except:
        return "OFF"

def get_bookings():
    try:
        r = requests.get(f"{FIREBASE_DB}/bookings.json", timeout=5)
        data = r.json()
        if data:
            return [v for _, v in data.items()]
        return []
    except:
        return []

def save_booking(booking):
    try:
        r = requests.post(f"{FIREBASE_DB}/bookings.json", json=booking, timeout=5)
        return r.status_code == 200
    except:
        return False

# -----------------------------
# THINGSBOARD FUNCTION
# -----------------------------
def send_to_thingsboard(data):
    try:
        requests.post(TB_URL, json=data, timeout=5)
    except:
        pass

# -----------------------------
# SYSTEM STATUS
# -----------------------------
status = get_system_status()
st.header(f"System Status: {'ONLINE' if status == 'ON' else 'OFF'}")

send_to_thingsboard({"system_status": status})

# -----------------------------
# LOAD BOOKINGS
# -----------------------------
bookings = pd.DataFrame(get_bookings())

if not bookings.empty:
    bookings["Start Date"] = pd.to_datetime(bookings["Start Date"]).dt.date
    bookings["End Date"] = pd.to_datetime(bookings["End Date"]).dt.date
else:
    bookings = pd.DataFrame(columns=[
        "Name", "Email", "Start Date", "End Date", "Experiment Type"
    ])

# -----------------------------
# BOOKING FORM
# -----------------------------
st.header("Book a Measurement Slot")

with st.form("booking_form"):
    name = st.text_input("Name")
    email = st.text_input("Email")

    experiment = st.selectbox(
        "Experiment Type",
        ["Co-Polarization", "Cross-Polarization"]
    )

    today = date.today()
    start_date, end_date = st.date_input(
        "Booking Date Range",
        value=(today, today + timedelta(days=1)),
        min_value=today
    )

    submit = st.form_submit_button("Submit Booking")

# -----------------------------
# HANDLE SUBMISSION
# -----------------------------
if submit:
    if not name or not email:
        st.error("Please enter name and email.")
    else:
        conflict = any(start_date <= row["End Date"] and end_date >= row["Start Date"]
                       for _, row in bookings.iterrows())

        if conflict:
            st.warning("Selected dates are already booked.")
        else:
            booking_data = {
                "Name": name,
                "Email": email,
                "Start Date": str(start_date),
                "End Date": str(end_date),
                "Experiment Type": experiment
            }

            if save_booking(booking_data):
                st.success("Booking confirmed!")

                # Send confirmation email
                send_email(email, name, start_date, end_date)

                # Send booking to ThingsBoard
                send_to_thingsboard({
                    "new_booking": True,
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "experiment_type": experiment
                })

            else:
                st.error("Failed to save booking.")

# -----------------------------
# DISPLAY BOOKINGS
# -----------------------------
st.header("Current Bookings")

if bookings.empty:
    st.info("No bookings yet.")
else:
    bookings_display = bookings[
        ["Name", "Email", "Start Date", "End Date", "Experiment Type"]
    ].sort_values("Start Date")

    st.dataframe(
        bookings_display,
        use_container_width=True,
        hide_index=True
    )
