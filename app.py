import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

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
    germination_date DATE,
    harvest_yield INTEGER,
    notes TEXT
)
''')
conn.commit()

# Define chili varieties
chili_varieties = [
    "Ghost Pepper",
    "Jalapeño",
    "Carolina Reaper",
    "Bhut Jolokia",
    "Cayenne",
    "Habanero",
    "Kıl Biber",
    "Cherry Pepper",
    "Peynir Biberi",
    "Kırmızı Kıl Biberi"
]

# Streamlit UI
st.title('🌶 Chili Planting Tracker')

# Form for adding chili planting
st.header("➕ Add Chili Planting")

with st.form("add_chili"):
    variety = st.selectbox("Select Chili Variety", chili_varieties)
    planting_date = st.date_input("Planting Date", datetime.today())
    seeds_planted = st.number_input("Number of Seeds Planted", min_value=1, step=1)

    germination_date = st.date_input("Germination Date (optional)", datetime.today())
    harvest_yield = st.number_input("Harvest Yield (optional, number of chilies)", min_value=0, step=1)
    notes = st.text_area("Notes (optional)")

    submitted = st.form_submit_button("Add to Tracker")

    if submitted:
        c.execute('''
            INSERT INTO chilies (variety, planting_date, seeds_planted, germination_date, harvest_yield, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (variety, planting_date, seeds_planted, germination_date, harvest_yield or None, notes))
        conn.commit()
        st.success(f"🌱 Successfully added {variety}!")

# Display records
st.header("📋 Planting Records")

df = pd.read_sql("SELECT * FROM chilies ORDER BY planting_date DESC", conn)
st.dataframe(df, use_container_width=True)

# Export data
st.header("📥 Export Data")

if st.button("Download as CSV"):
    csv = df.to_csv(index=False)
    st.download_button(label="📂 Download CSV",
                       data=csv,
                       file_name='chili_data.csv',
                       mime='text/csv')
