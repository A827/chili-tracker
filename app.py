import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import altair as alt
import qrcode
from io import BytesIO
from PIL import Image

# Database connection
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()

# Create table if not exists
c.execute('''
CREATE TABLE IF NOT EXISTS chilies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variety TEXT NOT NULL,
    planting_date DATE NOT NULL,
    seeds_planted INTEGER NOT NULL,
    germinated_seeds INTEGER,
    germination_date DATE,
    harvest_yield INTEGER,
    notes TEXT
)
''')
conn.commit()

# Chili varieties
chili_varieties = [
    "Ghost Pepper", "Jalapeño", "Carolina Reaper", "Bhut Jolokia",
    "Cayenne", "Habanero", "Kıl Biber", "Cherry Pepper",
    "Peynir Biberi", "Kırmızı Kıl Biberi"
]

# Title
st.title('🌶 Chili Planting Tracker')

# --- Form: Add New Chili Planting ---
st.header("➕ Add Chili Planting")

with st.form("add_chili"):
    dropdown_ok = st.radio("Can you use the dropdown?", ["Yes", "No"])
    if dropdown_ok == "Yes":
        variety = st.selectbox("Select Chili Variety", chili_varieties)
    else:
        variety = st.text_input("Enter Chili Variety manually")

    planting_date = st.date_input("Planting Date", datetime.today())
    seeds_planted = st.number_input("Number of Seeds Planted", min_value=1)
    germinated_seeds = st.number_input("Germinated Seeds (optional)", min_value=0)
    germination_date = st.date_input("Germination Date (optional)", datetime.today())
    harvest_yield = st.number_input("Harvest Yield (optional)", min_value=0)
    notes = st.text_area("Notes (optional)")

    submitted = st.form_submit_button("Add to Tracker")
    if submitted:
        c.execute('''
            INSERT INTO chilies (variety, planting_date, seeds_planted, germinated_seeds, germination_date, harvest_yield, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            variety, planting_date, seeds_planted,
            germinated_seeds if germinated_seeds else None,
            germination_date, harvest_yield if harvest_yield else None, notes
        ))
        conn.commit()
        st.success(f"🌱 Successfully added {variety}!")

# Load data
df = pd.read_sql("SELECT * FROM chilies ORDER BY planting_date DESC", conn)

# --- Filter Table ---
st.header("🔍 Search / Filter Records")
col1, col2 = st.columns(2)
with col1:
    filter_variety = st.selectbox("Filter by Variety", ["All"] + sorted(df["variety"].unique().tolist()))
with col2:
    filter_date = st.date_input("Filter by Planting Date (optional)")

filtered_df = df.copy()
if filter_variety != "All":
    filtered_df = filtered_df[filtered_df["variety"] == filter_variety]
if filter_date != datetime.today():
    filtered_df = filtered_df[filtered_df["planting_date"] == str(filter_date)]

st.dataframe(filtered_df, use_container_width=True)

# --- Export ---
st.header("📥 Export Data")
if st.button("Download as CSV"):
    csv = df.to_csv(index=False)
    st.download_button("📂 Download CSV", csv, "chili_data.csv", "text/csv")

# --- Yield Chart ---
st.header("📊 Yield by Chili Variety")
if not df.empty and "harvest_yield" in df.columns:
    yield_chart = alt.Chart(df[df["harvest_yield"].notnull()]).mark_bar().encode(
        x="variety:N",
        y="sum(harvest_yield):Q",
        tooltip=["variety", "sum(harvest_yield)"]
    ).properties(width=700, height=400)
    st.altair_chart(yield_chart, use_container_width=True)

# --- Germination Stats ---
st.header("🌱 Germination Success Rate")
if "germinated_seeds" in df.columns and not df["germinated_seeds"].isnull().all():
    df["germ_rate"] = (df["germinated_seeds"] / df["seeds_planted"]) * 100
    st.dataframe(df[["variety", "seeds_planted", "germinated_seeds", "germ_rate"]], use_container_width=True)
else:
    st.info("No germination data available yet.")

# --- Calendar / Timeline View ---
st.header("📅 Chili Timeline View")
timeline_df = df[["variety", "planting_date", "harvest_yield"]].copy()
timeline_df["planting_date"] = pd.to_datetime(timeline_df["planting_date"])
timeline_df["Harvested"] = timeline_df["harvest_yield"].notnull()
st.dataframe(timeline_df, use_container_width=True)

# --- ⏰ Reminders ---
st.header("🔔 Harvest Reminders")
today = datetime.today().date()
reminders_df = df[df["harvest_yield"].isnull()]
reminders_df["planting_date"] = pd.to_datetime(reminders_df["planting_date"])
reminders_df["days_since_planting"] = (today - reminders_df["planting_date"].dt.date).dt.days
needs_attention = reminders_df[reminders_df["days_since_planting"] > 90]

if not needs_attention.empty:
    st.warning("These plants may be overdue for harvesting or updating:")
    st.dataframe(needs_attention[["variety", "planting_date", "days_since_planting"]])
else:
    st.success("✅ All recent plantings are within the expected range.")

# --- QR Code Generator ---
st.header("🏷️ Generate QR Code for Chili ID")
chili_id_to_encode = st.selectbox("Select a Chili Record ID", df["id"].astype(str))
if st.button("Generate QR Code"):
    url = f"https://your-chili-tracker.com/record/{chili_id_to_encode}"  # You can customize this
    qr = qrcode.make(url)
    buf = BytesIO()
    qr.save(buf)
    buf.seek(0)
    image = Image.open(buf)
    st.image(image, caption=f"QR Code for Record ID {chili_id_to_encode}", use_column_width=False)
