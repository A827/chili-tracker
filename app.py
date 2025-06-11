import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import hashlib

# --- Functions ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password):
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hash_password(password)))
    return c.fetchone()

def get_user_id(username):
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    return result[0] if result else None

def init_user_table():
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )''')
    conn.commit()

def init_chili_table():
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
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    conn.commit()

# --- Database Setup ---
conn = sqlite3.connect('chili_tracker.db', check_same_thread=False)
c = conn.cursor()
init_user_table()
init_chili_table()

# --- Session State ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.user_id = None

# --- Authentication UI ---
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
            st.success(f"Welcome back, {username}!")
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
            st.success("✅ Account created. You can now log in.")
        except sqlite3.IntegrityError:
            st.error("❌ Username already exists.")

# --- Main App ---
if not st.session_state.logged_in:
    login_ui()
    st.stop()

# --- Logged-in App UI ---
st.sidebar.title("🌶 Welcome")
st.sidebar.markdown(f"Logged in as **{st.session_state.username}** ({st.session_state.role})")
if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.experimental_rerun()

st.title("🌱 My Chili Tracker")

# Add Chili Form
st.subheader("➕ Add Chili Record")

with st.form("add_chili"):
    variety = st.text_input("Chili Variety (e.g. Ghost Pepper)")
    planting_date = st.date_input("Planting Date", datetime.today())
    seeds_planted = st.number_input("Seeds Planted", min_value=1)
    germinated_seeds = st.number_input("Germinated Seeds", min_value=0)
    germination_date = st.date_input("Germination Date", datetime.today())
    harvest_yield = st.number_input("Harvest Yield", min_value=0)
    notes = st.text_area("Notes (optional)")
    submitted = st.form_submit_button("Add")

    if submitted:
        c.execute('''INSERT INTO chilies (user_id, variety, planting_date, seeds_planted, germinated_seeds,
                     germination_date, harvest_yield, notes)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (st.session_state.user_id, variety, planting_date, seeds_planted,
                   germinated_seeds, germination_date, harvest_yield, notes))
        conn.commit()
        st.success(f"🌶 Added {variety} chili planting.")

# View Chili Records
st.subheader("📋 My Chili Records")
df = pd.read_sql("SELECT * FROM chilies WHERE user_id = ? ORDER BY planting_date DESC", conn,
                 params=(st.session_state.user_id,))
st.dataframe(df, use_container_width=True)
