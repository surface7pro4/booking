import streamlit as st
import pandas as pd
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, timedelta, datetime, timezone

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
SMTP_PASSWORD = "lslcfalitzjzdctp "  # the 16-character app password
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587  # or 465 for SSL

# -----------------------------
# AUTO-REFRESH
# -----------------------------
st_autorefresh(interval=5000, key="live_refresh")

# -----------------------------
# EMAIL FUNCTION (UNCHANGED)
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
    except:
        return False

# -----------------------------
# FIREBASE HELPERS
# -----------------------------
def get_system_status():
    try:
        r = requests.get(f"{FIREBASE_DB}/system_status.json", timeout=5)
        return r.json()
    except:
        return "OFF"

def get_bookings():
    """
    Return a list of booking dicts (each booking as stored in Firebase).
    """
    try:
        r = requests.get(f"{FIREBASE_DB}/bookings.json", timeout=5)
        data = r.json()
        if data:
            # data is a dict of keys -> booking dicts
            return [v for _, v in data.items()]
        return []
    except:
        return []

def save_booking(booking):
    """
    POST booking to Firebase. Returns True on success.
    """
    try:
        r = requests.post(f"{FIREBASE_DB}/bookings.json", json=booking, timeout=8)
        return r.ok
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
# SYSTEM STATUS (display)
# -----------------------------
status = get_system_status()
st.header(f"System Status: {'ONLINE' if status == 'ON' else 'OFF'}")
send_to_thingsboard({"system_status": status})

# -----------------------------
# LOAD BOOKINGS (initial)
# -----------------------------
raw_bookings = get_bookings()
bookings = pd.DataFrame(raw_bookings)

# Ensure columns exist so selection won't KeyError (backwards-compatible)
expected_cols = ["Name", "Email", "Start Date", "End Date", "Experiment Type", "Date and Time Booked"]
for col in expected_cols:
    if col not in bookings.columns:
        bookings[col] = ""

# Convert Start/End to date objects if possible
if not bookings.empty:
    # Some entries might have empty strings; coerce errors
    bookings["Start Date"] = pd.to_datetime(bookings["Start Date"], errors="coerce").dt.date
    bookings["End Date"] = pd.to_datetime(bookings["End Date"], errors="coerce").dt.date

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
        # Reload bookings to ensure we check against the latest data
        raw_bookings = get_bookings()
        bookings = pd.DataFrame(raw_bookings)
        for col in expected_cols:
            if col not in bookings.columns:
                bookings[col] = ""
        if not bookings.empty:
            bookings["Start Date"] = pd.to_datetime(bookings["Start Date"], errors="coerce").dt.date
            bookings["End Date"] = pd.to_datetime(bookings["End Date"], errors="coerce").dt.date

        # Conflict check
        conflict = False
        if not bookings.empty:
            for _, row in bookings.iterrows():
                # if any existing booking overlaps the requested range
                try:
                    existing_start = row["Start Date"]
                    existing_end = row["End Date"]
                    if pd.isna(existing_start) or pd.isna(existing_end):
                        continue
                    if start_date <= existing_end and end_date >= existing_start:
                        conflict = True
                        break
                except Exception:
                    continue

        if conflict:
            st.warning("Selected dates are already booked.")
        else:
            # Timestamp in Singapore time (UTC+8) with comma + space format
            SGT = timezone(timedelta(hours=8))
            timestamp = datetime.now(SGT).strftime("%Y-%m-%d, %H:%M:%S")

            booking_data = {
                "Name": name,
                "Email": email,
                "Start Date": str(start_date),
                "End Date": str(end_date),
                "Experiment Type": experiment,
                "Date and Time Booked": timestamp
            }

            saved = save_booking(booking_data)
            st.write("Save status:", saved)  # temporary debug line — remove if you don't want this visible
            if saved:
                st.success("Booking confirmed!")

                # Send email (function unchanged)
                email_ok = send_email(email, name, start_date, end_date)
                if not email_ok:
                    st.warning("Booking saved, but sending email failed.")

                # Send booking to ThingsBoard
                send_to_thingsboard({
                    "new_booking": True,
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "experiment_type": experiment
                })

                # Reload bookings for display
                raw_bookings = get_bookings()
                bookings = pd.DataFrame(raw_bookings)
                for col in expected_cols:
                    if col not in bookings.columns:
                        bookings[col] = ""
                if not bookings.empty:
                    bookings["Start Date"] = pd.to_datetime(bookings["Start Date"], errors="coerce").dt.date
                    bookings["End Date"] = pd.to_datetime(bookings["End Date"], errors="coerce").dt.date
            else:
                st.error("Failed to save booking. Check network / Firebase rules.")

# -----------------------------
# DISPLAY BOOKINGS
# -----------------------------
st.header("Current Bookings")

# Ensure bookings DataFrame exists and has expected columns
try:
    if bookings.empty:
        st.info("No bookings yet.")
    else:
        # ensure column exists, then show in table
        for col in expected_cols:
            if col not in bookings.columns:
                bookings[col] = ""
        # present table with neat ordering
        display_cols = ["Name", "Email", "Start Date", "End Date", "Experiment Type", "Date and Time Booked"]
        # safe selection
        bookings_display = bookings.loc[:, display_cols].sort_values("Start Date", na_position="last")
        st.dataframe(bookings_display, use_container_width=True, hide_index=True)
except Exception as e:
    st.error(f"Failed to display bookings: {e}")
