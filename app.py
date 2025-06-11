
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import hashlib
import altair as alt
from PIL import Image
from io import BytesIO
import os

# ---------------------
# Setup
# ---------------------
st.set_page_config(page_title="🌶 Chili Tracker", layout="wide")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username, password):
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hash_password(password)))
    return c.fetchone()

def get_user_id(username):
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    return result[0] if result else None

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

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.user_id = None
    st.session_state.role = ""

# ---------------------
# Auth UI
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
            st.success("Login successful!")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")

    st.markdown("---")
    st.subheader("Create New Account")
    new_user = st.text_input("New Username")
    new_pass = st.text_input("New Password", type="password")
    role = st.selectbox("Role", ["user", "admin"])
    if st.button("Create Account"):
        try:
            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                      (new_user, hash_password(new_pass), role))
            conn.commit()
            st.success("Account created.")
        except sqlite3.IntegrityError:
            st.error("Username already exists.")

# ---------------------
# Helper Functions
# ---------------------
def load_data():
    return pd.read_sql("SELECT * FROM chilies WHERE user_id = ? ORDER BY planting_date DESC",
                       conn, params=(st.session_state.user_id,))

def log_action(action):
    c.execute("INSERT INTO activity_log (user_id, action) VALUES (?, ?)", (st.session_state.user_id, action))
    conn.commit()

def save_image(photo):
    folder = "uploads"
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, photo.name)
    with open(path, "wb") as f:
        f.write(photo.getbuffer())
    return path

# ---------------------
# UI Pages
# ---------------------
def show_dashboard():
    df = load_data()
    st.title("🌶 Dashboard")
    if df.empty:
        st.info("No records yet.")
        return
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Varieties", df["variety"].nunique())
    col2.metric("Seeds Planted", df["seeds_planted"].sum())
    col3.metric("Avg. Germination Rate (%)", round((df["germinated_seeds"] / df["seeds_planted"]).mean() * 100, 1))

def show_add_form():
    st.title("➕ Add Chili Planting")
    with st.form("form_add"):
        variety = st.text_input("Chili Variety")
        planting_date = st.date_input("Planting Date", datetime.today())
        seeds_planted = st.number_input("Seeds Planted", min_value=1)
        germinated_seeds = st.number_input("Germinated Seeds", min_value=0)
        germination_date = st.date_input("Germination Date", datetime.today())
        harvest_yield = st.number_input("Harvest Yield", min_value=0)
        notes = st.text_area("Notes")
        photo = st.file_uploader("Upload Photo", type=["jpg", "png", "jpeg"])

        if st.form_submit_button("Add"):
            photo_path = save_image(photo) if photo else None
            c.execute('''INSERT INTO chilies (user_id, variety, planting_date, seeds_planted,
                         germinated_seeds, germination_date, harvest_yield, notes, photo_path)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (st.session_state.user_id, variety, planting_date, seeds_planted,
                       germinated_seeds, germination_date, harvest_yield, notes, photo_path))
            conn.commit()
            log_action(f"Added chili variety {variety}")
            st.success(f"{variety} added!")

def show_gallery():
    st.title("📸 Chili Photo Gallery")
    df = load_data()
    if df.empty or df["photo_path"].isnull().all():
        st.info("No photos uploaded.")
        return
    for _, row in df[df["photo_path"].notnull()].iterrows():
        st.image(row["photo_path"], caption=f"{row['variety']} - {row['planting_date']}")

def show_table():
    st.title("📋 My Chili Records")
    df = load_data()
    st.dataframe(df)

    if st.checkbox("Enable editing"):
        record_id = st.selectbox("Select Record ID to Edit", df["id"])
        selected = df[df["id"] == record_id].iloc[0]
        with st.form("edit_form"):
            variety = st.text_input("Chili Variety", selected["variety"])
            planting_date = st.date_input("Planting Date", pd.to_datetime(selected["planting_date"]))
            seeds_planted = st.number_input("Seeds Planted", min_value=1, value=selected["seeds_planted"])
            germinated_seeds = st.number_input("Germinated Seeds", min_value=0, value=selected["germinated_seeds"] or 0)
            germination_date = st.date_input("Germination Date", pd.to_datetime(selected["germination_date"]) if selected["germination_date"] else datetime.today())
            harvest_yield = st.number_input("Harvest Yield", min_value=0, value=selected["harvest_yield"] or 0)
            notes = st.text_area("Notes", selected["notes"])
            if st.form_submit_button("Update"):
                c.execute('''UPDATE chilies SET variety=?, planting_date=?, seeds_planted=?, germinated_seeds=?,
                             germination_date=?, harvest_yield=?, notes=? WHERE id=?''',
                          (variety, planting_date, seeds_planted, germinated_seeds, germination_date, harvest_yield, notes, record_id))
                conn.commit()
                log_action(f"Updated chili record {record_id}")
                st.success("Updated successfully.")
                st.experimental_rerun()

        if st.button("Delete Record"):
            c.execute("DELETE FROM chilies WHERE id = ?", (record_id,))
            conn.commit()
            log_action(f"Deleted chili record {record_id}")
            st.warning("Record deleted.")
            st.experimental_rerun()

def show_upload_csv():
    st.title("📤 Batch Upload via CSV")
    sample = pd.DataFrame({
        "variety": ["Jalapeño", "Cayenne"],
        "planting_date": ["2024-03-01", "2024-03-15"],
        "seeds_planted": [10, 20],
        "germinated_seeds": [8, 15],
        "germination_date": ["2024-03-10", "2024-03-20"],
        "harvest_yield": [50, 80],
        "notes": ["Test A", "Test B"]
    })
    st.markdown("**CSV Format:**")
    st.dataframe(sample)

    csv_file = st.file_uploader("Upload your CSV", type="csv")
    if csv_file:
        df_csv = pd.read_csv(csv_file)
        for _, row in df_csv.iterrows():
            c.execute('''INSERT INTO chilies (user_id, variety, planting_date, seeds_planted,
                         germinated_seeds, germination_date, harvest_yield, notes)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                      (st.session_state.user_id, row["variety"], row["planting_date"], row["seeds_planted"],
                       row["germinated_seeds"], row["germination_date"], row["harvest_yield"], row["notes"]))
        conn.commit()
        log_action("Uploaded chili data from CSV")
        st.success("CSV records added!")

def show_activity_log():
    st.title("🕒 Activity Log")
    df = pd.read_sql("SELECT * FROM activity_log WHERE user_id = ? ORDER BY timestamp DESC",
                     conn, params=(st.session_state.user_id,))
    st.dataframe(df)

# ---------------------
# Start App
# ---------------------
if not st.session_state.logged_in:
    login_ui()
    st.stop()

st.sidebar.title("🌶 Chili Tracker")
st.sidebar.markdown(f"Logged in as: **{st.session_state.username}**")
nav = st.sidebar.radio("Navigate", ["Dashboard", "Add Planting", "Gallery", "My Records", "Upload CSV", "Activity Log", "Logout"])

if nav == "Dashboard":
    show_dashboard()
elif nav == "Add Planting":
    show_add_form()
elif nav == "Gallery":
    show_gallery()
elif nav == "My Records":
    show_table()
elif nav == "Upload CSV":
    show_upload_csv()
elif nav == "Activity Log":
    show_activity_log()
elif nav == "Logout":
    st.session_state.logged_in = False
    st.experimental_rerun()
