
import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from io import BytesIO
from PIL import Image
import hashlib
import altair as alt
import base64

# ---------------------
# Page Config & Setup
# ---------------------
st.set_page_config(page_title="🌶 Chili Tracker", layout="wide")

conn = sqlite3.connect("chili_tracker_with_user.db", check_same_thread=False)
c = conn.cursor()

# Ensure tables exist
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
)''')

c.execute('''CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

conn.commit()

# ---------------------
# Utility Functions
# ---------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password):
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hash_password(password)))
    return c.fetchone()

def save_photo(uploaded_file):
    photos_dir = "uploaded_photos"
    os.makedirs(photos_dir, exist_ok=True)
    photo_path = os.path.join(photos_dir, uploaded_file.name)
    with open(photo_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return photo_path

def log_action(user_id, action):
    c.execute("INSERT INTO activity_log (user_id, action) VALUES (?, ?)", (user_id, action))
    conn.commit()

def get_user_id(username):
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    return result[0] if result else None

def load_user_data(user_id):
    return pd.read_sql("SELECT * FROM chilies WHERE user_id = ? ORDER BY planting_date DESC", conn, params=(user_id,))

def display_photo(photo_path):
    if os.path.exists(photo_path):
        with open(photo_path, "rb") as file:
            encoded = base64.b64encode(file.read()).decode()
        st.markdown(f"<img src='data:image/jpeg;base64,{encoded}' width='200'>", unsafe_allow_html=True)

# ---------------------
# Session State
# ---------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.user_id = None
    st.session_state.role = ""



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
            log_action(user[0], "Login")
            st.experimental_rerun()
        else:
            st.error("❌ Incorrect username or password")

    st.markdown("Don't have an account?")
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
    st.header("📊 Dashboard Metrics")
    df = load_user_data(st.session_state.user_id)
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("🌱 Total Seeds", int(df["seeds_planted"].sum()))
        col2.metric("🌿 Avg Germination Rate",
                    f"{(df['germinated_seeds'].sum()/df['seeds_planted'].sum()*100):.1f}%" if df['seeds_planted'].sum() > 0 else "N/A")
        col3.metric("🌶 Total Harvest", int(df['harvest_yield'].fillna(0).sum()))
        st.bar_chart(df.groupby("variety")["harvest_yield"].sum())
    else:
        st.info("No records found yet.")

def show_add_form():
    st.header("➕ Add Chili Planting Record")
    with st.form("add_chili"):
        variety = st.text_input("Chili Variety")
        planting_date = st.date_input("Planting Date", datetime.today())
        seeds_planted = st.number_input("Seeds Planted", min_value=1)
        germinated_seeds = st.number_input("Germinated Seeds", min_value=0)
        germination_date = st.date_input("Germination Date")
        harvest_yield = st.number_input("Harvest Yield", min_value=0)
        notes = st.text_area("Notes")
        uploaded_file = st.file_uploader("Upload Photo", type=["png", "jpg", "jpeg"])
        submitted = st.form_submit_button("Submit")
        if submitted:
            photo_path = save_photo(uploaded_file) if uploaded_file else ""
            c.execute("INSERT INTO chilies (user_id, variety, planting_date, seeds_planted, germinated_seeds, germination_date, harvest_yield, notes, photo_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (st.session_state.user_id, variety, planting_date, seeds_planted, germinated_seeds,
                       germination_date, harvest_yield, notes, photo_path))
            conn.commit()
            log_action(st.session_state.user_id, f"Added chili: {variety}")
            st.success("Chili entry added!")

def show_my_chilies():
    st.header("📋 My Chili Records")
    df = load_user_data(st.session_state.user_id)
    for index, row in df.iterrows():
        with st.expander(f"{row['variety']} - {row['planting_date']}"):
            st.write(row)
            if row["photo_path"]:
                display_photo(row["photo_path"])
            if st.button(f"Delete {row['variety']}", key=f"del_{row['id']}"):
                c.execute("DELETE FROM chilies WHERE id = ?", (row["id"],))
                conn.commit()
                log_action(st.session_state.user_id, f"Deleted chili: {row['variety']}")
                st.experimental_rerun()

def show_export():
    st.header("📥 Export Data as CSV")
    df = load_user_data(st.session_state.user_id)
    if not df.empty:
        st.download_button("Download CSV", df.to_csv(index=False), file_name="my_chilies.csv", mime="text/csv")
    else:
        st.info("No data available.")

def show_activity_log():
    st.header("🕒 Activity Log")
    c.execute("SELECT username, action, timestamp FROM activity_log JOIN users ON users.id = activity_log.user_id ORDER BY timestamp DESC")
    logs = c.fetchall()
    if logs:
        df = pd.DataFrame(logs, columns=["User", "Action", "Timestamp"])
        st.dataframe(df)
    else:
        st.info("No activity recorded.")

# ---------------------
# App Start
# ---------------------
if not st.session_state.logged_in:
    login_ui()
    st.stop()

st.sidebar.title("🌶 Chili Tracker")
st.sidebar.markdown(f"👤 Logged in as: **{st.session_state.username}**")
page = st.sidebar.radio("Navigate", ["Dashboard", "Add Planting", "My Chilies", "Export", "Activity Log", "Logout"])

if page == "Dashboard":
    show_dashboard()
elif page == "Add Planting":
    show_add_form()
elif page == "My Chilies":
    show_my_chilies()
elif page == "Export":
    show_export()
elif page == "Activity Log":
    show_activity_log()
elif page == "Logout":
    st.session_state.logged_in = False
    st.experimental_rerun()
