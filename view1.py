import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta
import hashlib
import calendar

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
st.set_page_config(page_title="Menlo THz Booking Dashboard", layout="wide")
st.title("Menlo THz Booking Dashboard")

FIREBASE_DB = "https://book1-bc265-default-rtdb.asia-southeast1.firebasedatabase.app"

today = date.today()

# --------------------------------------------------
# AUTO REFRESH
# --------------------------------------------------
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=5000, key="refresh")  # Refresh every 5s

# --------------------------------------------------
# FIREBASE HELPERS
# --------------------------------------------------
@st.cache_data(ttl=5)
def get_menlo_status():
    try:
        return requests.get(f"{FIREBASE_DB}/menlo_status.json", timeout=5).json()
    except:
        return "OFF"

@st.cache_data(ttl=5)
def get_bookings():
    try:
        r = requests.get(f"{FIREBASE_DB}/bookings.json", timeout=5).json()
        if not r:
            return pd.DataFrame()
        df = pd.DataFrame(r.values())
        df["Start Date"] = pd.to_datetime(df["Start Date"]).dt.date
        df["End Date"] = pd.to_datetime(df["End Date"]).dt.date
        # Only keep active bookings
        df = df[df["End Date"] >= today]
        return df
    except:
        return pd.DataFrame()

# --------------------------------------------------
# COLOR ASSIGNMENT PER USER
# --------------------------------------------------
def name_color(name):
    h = hashlib.md5(name.encode()).hexdigest()
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return f"rgba({r},{g},{b},0.35)"

# --------------------------------------------------
# DASHBOARD CONTENT
# --------------------------------------------------
def dashboard():
    bookings = get_bookings()
    status = get_menlo_status()
    status_color = "green" if status == "ON" else "red"

    # Menlo status
    st.markdown(
        f"""
        <div style="font-size:20px;">
            Menlo Status:
            <span style="color:{status_color}; font-weight:700;">
                {status}
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    # Next available day
    def next_available_day():
        d = today
        while True:
            if d.weekday() < 5:  # weekdays only
                if bookings.empty or not any(
                    (d >= r["Start Date"] and d <= r["End Date"])
                    for _, r in bookings.iterrows()
                ):
                    return d
            d += timedelta(days=1)
    st.info(f"Next available working day: **{next_available_day().strftime('%A, %d %B %Y')}**")

    # --------------------------------------------------
    # Month selection
    # --------------------------------------------------
    if "month_offset" not in st.session_state:
        st.session_state.month_offset = 0  # 0 = current month

    col1, col2, col3 = st.columns([1,6,1])
    with col1:
        if st.button("◀ Previous Month"):
            st.session_state.month_offset -= 1
    with col3:
        if st.button("Next Month ▶"):
            st.session_state.month_offset += 1

    # Calculate the target month/year
    month = (today.month - 1 + st.session_state.month_offset) % 12 + 1
    year = today.year + ((today.month - 1 + st.session_state.month_offset) // 12)
    month_name = calendar.month_name[month]

    st.header(f"Booking Calendar: {month_name} {year}")

    # First and last day of the month
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    # start on Sunday
    start_day = first_day - timedelta(days=(first_day.weekday() + 1) % 7)
    end_day = last_day + timedelta(days=(6 - last_day.weekday()) % 7)

    days = pd.date_range(start_day, end_day)

    calendar_html = """
    <style>
    .grid { display:grid; grid-template-columns:repeat(7,1fr); gap:8px; }
    .cell {
        border:1px solid #333;
        border-radius:10px;
        min-height:100px;
        padding:6px;
    }
    .dayname { font-weight:600; opacity:0.7; }
    .booking {
        margin-top:4px;
        padding:4px;
        border-radius:6px;
        font-size:12px;
    }
    .weekend { background:#2a2a2a; opacity:0.4; }
    .today { border:2px solid #00f; }
    </style>
    """

    calendar_html += "<div class='grid'>"

    # Weekday headers
    for wd in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]:
        calendar_html += f"<div class='cell dayname'><b>{wd}</b></div>"

    for d in days:
        is_weekend = d.weekday() >= 5
        is_today = d.date() == today
        classes = []
        if is_weekend:
            classes.append("weekend")
        if is_today:
            classes.append("today")
        class_str = " ".join(classes)

        calendar_html += f"<div class='cell {class_str}'>"
        calendar_html += f"<div class='dayname'>{d.day}</div>"

        for _, r in bookings.iterrows():
            if r["Start Date"] <= d.date() <= r["End Date"]:
                calendar_html += (
                    f"<div class='booking' style='background:{name_color(r['Name'])};'>"
                    f"{r['Name']}</div>"
                )

        calendar_html += "</div>"

    calendar_html += "</div>"
    st.markdown(calendar_html, unsafe_allow_html=True)

    # Bookings table
    st.header("Current Bookings")
    if bookings.empty:
        st.info("No active bookings")
    else:
        bookings["Days Left"] = (bookings["Start Date"] - today).apply(lambda x: max(x.days, 0))
        table = bookings[[
            "Name",
            "Start Date",
            "End Date",
            "Experiment Type",
            "Days Left"
        ]].sort_values("Start Date")
        st.dataframe(table, hide_index=True, use_container_width=True)


# Run dashboard
dashboard()
