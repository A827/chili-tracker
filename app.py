import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import hashlib
import altair as alt
import qrcode
from io import BytesIO
from PIL import Image
import os

# ---------------------
# Helper Functions
# ---------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password):
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hash_password(password)))
    return c.fetchone()

def get_user_id(username):
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    return result[0] if result else None

# ---------------------
# DB Setup
# ---------------------
conn = sqlite3.connect("chili_tracker_with_user.db", check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)''')

c.execute('''CREATE TABLE IF NOT EXISTS chilies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    variety TEXT NOT NULL,
    planting_date DATE NOT NULL,
    seeds_planted INTEGER NOT NULL,
    germinated_seeds INTEGER,
    germination_date DATE,
    harvest_yield INTEGER,
    notes TEXT,
    photo_path TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
)''')

conn.commit()

# Create upload folder if not exists
if not os.path.exists("uploaded_photos"):
    os.makedirs("uploaded_photos")

# ---------------------
# Session State Init
# ---------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.user_id = None

# ---------------------
# Login UI
# ---------------------
def login_ui():
    st.title("🔐 Chili Tracker Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = check_login(username, password)
        if user:
            st.session_state.logged_in = True
            st.session_state.username = user[1]
            st.session_state.user_id = user[0]
            st.session_state.role = user[3]
            st.success(f"Welcome, {username}!")
            st.session_state._rerun = True
        else:
            st.error("❌ Incorrect username or password")

    st.markdown("---")
    st.subheader("Create Account")
    new_user = st.text_input("New Username")
    new_pass = st.text_input("New Password", type="password")
    role = st.selectbox("Role", ["user", "admin"])
    if st.button("Create Account"):
        try:
            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                      (new_user, hash_password(new_pass), role))
            conn.commit()
            st.success("✅ Account created. Please log in.")
        except sqlite3.IntegrityError:
            st.error("❌ Username already exists.")

# ---------------------
# Main App Pages
# ---------------------

def show_dashboard():
    st.subheader("🔔 Harvest Reminders")
    df = load_user_data()
    today = datetime.today().date()
    if not df.empty:
        df["planting_date"] = pd.to_datetime(df["planting_date"])
        df["days_since"] = (today - df["planting_date"].dt.date).dt.days
        overdue = df[df["harvest_yield"].isnull() & (df["days_since"] > 90)]
        if not overdue.empty:
            st.warning("Some chilies may need harvesting:")
            st.dataframe(overdue[["variety", "planting_date", "days_since"]])
        else:
            st.success("✅ No overdue plantings.")
    else:
        st.info("No chili records yet.")

def show_add_form():
    st.subheader("➕ Add New Chili Plant")
    with st.form("add_chili"):
        variety = st.text_input("Chili Variety")
        planting_date = st.date_input("Planting Date", datetime.today())
        seeds_planted = st.number_input("Seeds Planted", min_value=1)
        germinated_seeds = st.number_input("Germinated Seeds", min_value=0)
        germination_date = st.date_input("Germination Date", datetime.today())
        harvest_yield = st.number_input("Harvest Yield", min_value=0)
        notes = st.text_area("Notes")
        photo = st.file_uploader("Upload a photo (optional)", type=["jpg", "jpeg", "png"])

        photo_path = None
        if photo:
            photo_path = os.path.join("uploaded_photos", photo.name)
            with open(photo_path, "wb") as f:
                f.write(photo.getbuffer())

        if st.form_submit_button("Add Plant"):
            c.execute('''INSERT INTO chilies (user_id, variety, planting_date, seeds_planted, germinated_seeds,
                         germination_date, harvest_yield, notes, photo_path)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (st.session_state.user_id, variety, planting_date, seeds_planted,
                       germinated_seeds, germination_date, harvest_yield, notes, photo_path))
            conn.commit()
            st.success(f"🌱 Added {variety} successfully.")

def show_my_chilies():
    st.subheader("📋 My Chili Records")
    df = load_user_data()
    for _, row in df.iterrows():
        st.markdown(f"**{row['variety']}** planted on {row['planting_date']}")
        if row['photo_path']:
            st.image(row['photo_path'], width=200)
        st.text(f"Seeds: {row['seeds_planted']} | Germinated: {row['germinated_seeds']} | Yield: {row['harvest_yield']}")
        st.markdown("---")

def show_analytics():
    st.subheader("📊 Chili Analytics")
    df = load_user_data()
    if not df.empty:
        st.markdown("### Yield per Variety")
        chart = alt.Chart(df[df["harvest_yield"].notnull()]).mark_bar().encode(
            x="variety", y="sum(harvest_yield)", tooltip=["variety", "sum(harvest_yield)"]
        ).properties(width=700)
        st.altair_chart(chart, use_container_width=True)

        st.markdown("### Germination Success")
        df["germ_rate"] = (df["germinated_seeds"] / df["seeds_planted"] * 100).round(1)
        st.dataframe(df[["variety", "seeds_planted", "germinated_seeds", "germ_rate"]])

        st.markdown("### Monthly Yield")
        df["month"] = pd.to_datetime(df["planting_date"]).dt.to_period("M").astype(str)
        chart2 = alt.Chart(df[df["harvest_yield"].notnull()]).mark_bar().encode(
            x="month", y="sum(harvest_yield)", color="variety"
        ).properties(width=700)
        st.altair_chart(chart2, use_container_width=True)
    else:
        st.info("No data available.")

def show_calendar():
    st.subheader("📅 Planting Calendar")
    df = load_user_data()
    if not df.empty:
        df["planting_date"] = pd.to_datetime(df["planting_date"])
        df_sorted = df.sort_values("planting_date")
        st.dataframe(df_sorted[["variety", "planting_date", "harvest_yield"]])
    else:
        st.info("No planting records yet.")

def show_qr():
    st.subheader("🏷 Generate QR Code")
    df = load_user_data()
    if not df.empty:
        chili_id = st.selectbox("Select Record ID", df["id"].astype(str))
        url = f"https://your-chili-app/record/{chili_id}"
        qr = qrcode.make(url)
        buf = BytesIO()
        qr.save(buf)
        st.image(Image.open(buf), caption=f"QR Code for ID {chili_id}")
    else:
        st.info("No records to generate QR codes.")

def show_export():
    st.subheader("📥 Export My Data")
    df = load_user_data()
    if not df.empty:
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, file_name="my_chili_data.csv", mime="text/csv")
    else:
        st.info("No data to export.")

def load_user_data():
    return pd.read_sql("SELECT * FROM chilies WHERE user_id = ? ORDER BY planting_date DESC", conn,
                       params=(st.session_state.user_id,))

# ---------------------
# App Start
# ---------------------
if not st.session_state.logged_in:
    login_ui()
    if '_rerun' in st.session_state and st.session_state._rerun:
        st.session_state._rerun = False
        st.experimental_rerun()
    st.stop()

# Sidebar Navigation
st.sidebar.title("🌶 Chili Tracker")
st.sidebar.markdown(f"Logged in as: **{st.session_state.username}**")
page = st.sidebar.radio("Navigate", ["Dashboard", "Add Planting", "My Chilies", "Analytics", "Calendar", "QR Labels", "Export", "Logout"])

if page == "Dashboard":
    show_dashboard()
elif page == "Add Planting":
    show_add_form()
elif page == "My Chilies":
    show_my_chilies()
elif page == "Analytics":
    show_analytics()
elif page == "Calendar":
    show_calendar()
elif page == "QR Labels":
    show_qr()
elif page == "Export":
    show_export()
elif page == "Logout":
    st.session_state.logged_in = False
    st.experimental_rerun()
