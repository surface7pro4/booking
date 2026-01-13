import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta, datetime
from streamlit_autorefresh import st_autorefresh
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Booking System", layout="centered")
st.title("Menlo Booking System")

FIREBASE_DB = "https://book1-bc265-default-rtdb.asia-southeast1.firebasedatabase.app"

# -----------------------------
# AUTO-REFRESH EVERY 5 SECONDS
# -----------------------------
st_autorefresh(interval=5000, key="live_refresh")  

# -----------------------------
# MENLO STATUS FUNCTIONS
# -----------------------------
def get_menlo_status():
    try:
        r = requests.get(f"{FIREBASE_DB}/menlo_status.json", timeout=5)
        return r.json()  # "ON" or "OFF"
    except:
        return "OFF"

def get_bookings():
    try:
        r = requests.get(f"{FIREBASE_DB}/bookings.json", timeout=5)
        data = r.json()
        if data:
            return [v for k, v in data.items()]
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
# EMAIL FUNCTION
# -----------------------------
def send_email(to_email, subject, body):
    # Gmail config (replace with your email and app password)
    sender_email = "your_email@gmail.com"
    sender_password = "your_app_password"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print("Email send failed:", e)
        return False

# -----------------------------
# DISPLAY MENLO STATUS
# -----------------------------
menlo_status = get_menlo_status()
st.header("Menlo Status: " + ("ON" if menlo_status=="ON" else "OFF"))

# -----------------------------
# LOAD BOOKINGS
# -----------------------------
bookings = pd.DataFrame(get_bookings())

if not bookings.empty:
    bookings["Start Date"] = pd.to_datetime(bookings["Start Date"]).dt.date
    bookings["End Date"] = pd.to_datetime(bookings["End Date"]).dt.date
else:
    bookings = pd.DataFrame(columns=["Name","Email","Experiment Type","Start Date","End Date"])

# -----------------------------
# BOOKING FORM
# -----------------------------
st.header("Book Measurement Slot")

with st.form("booking_form"):
    name = st.text_input("User Name")
    email = st.text_input("Email Address")
    experiment = st.selectbox(
        "Experiment Type",
        ["Co-Polarization", "Cross-Polarization"]
    )

    today = date.today()
    start_date, end_date = st.date_input(
        "Booking Date Range",
        value=(today, today + timedelta(days=1)),
        min_value=today,
    )

    submit = st.form_submit_button("Submit Booking")

# -----------------------------
# HANDLE FORM SUBMISSION
# -----------------------------
if submit:
    if not name or not email:
        st.error("Please enter your name and email.")
    elif not start_date or not end_date:
        st.error("Please select valid start and end dates.")
    elif start_date > end_date:
        st.error("End date must be the same or after start date.")
    else:
        conflict = False

        for _, row in bookings.iterrows():
            existing_start = row["Start Date"]
            existing_end = row["End Date"]
            if start_date <= existing_end and end_date >= existing_start:
                conflict = True
                break

        if conflict:
            st.warning("One or more days in the selected range are already booked.")
        else:
            booking_data = {
                "Name": name,
                "Email": email,
                "Experiment Type": experiment,
                "Start Date": str(start_date),
                "End Date": str(end_date)
            }

            if save_booking(booking_data):
                st.success("Booking confirmed!")

                # Send confirmation email
                send_email(
                    to_email=email,
                    subject="Menlo Booking Confirmation",
                    body=f"Hello {name},\n\nYour booking for {experiment} from {start_date} to {end_date} has been confirmed.\n\nThank you!"
                )

                # Reload bookings
                bookings = pd.DataFrame(get_bookings())
                if not bookings.empty:
                    bookings["Start Date"] = pd.to_datetime(bookings["Start Date"]).dt.date
                    bookings["End Date"] = pd.to_datetime(bookings["End Date"]).dt.date
            else:
                st.error("Failed to save booking!")

# -----------------------------
# REMINDER CHECK
# -----------------------------
today = date.today()
for _, row in bookings.iterrows():
    if row["Start Date"] == today + timedelta(days=1):
        # Send reminder email
        send_email(
            to_email=row["Email"],
            subject="Menlo Booking Reminder",
            body=f"Hello {row['Name']},\n\nThis is a reminder that your booking for {row['Experiment Type']} is tomorrow ({row['Start Date']})."
        )

# -----------------------------
# DISPLAY BOOKINGS
# -----------------------------
st.header("Current Bookings")

if bookings.empty:
    st.info("No bookings yet.")
else:
    display_cols = ["Name", "Email", "Start Date", "End Date", "Experiment Type"]
    bookings_display = bookings[display_cols].sort_values("Start Date")
    st.dataframe(bookings_display, use_container_width=True, hide_index=True)
