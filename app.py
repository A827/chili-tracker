import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Database setup
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS chilies (
                id INTEGER PRIMARY KEY,
                name TEXT,
                planting_date DATE,
                seeds_planted INTEGER,
                germination_date DATE,
                yield INTEGER,
                notes TEXT
            )''')
conn.commit()

# Streamlit UI
st.title('🌶️ Chili Tracker')

# Form to input chili data
with st.form("Add Chili"):
    name = st.text_input("Chili Type")
    planting_date = st.date_input("Planting Date", datetime.today())
    seeds_planted = st.number_input("Seeds Planted", min_value=1, value=1)
    germination_date = st.date_input("Germination Date (optional)", value=None)
    chili_yield = st.number_input("Yield (optional)", min_value=0, value=0)
    notes = st.text_area("Notes", "")

    submit = st.form_submit_button("Add Chili")

if submit:
    c.execute('INSERT INTO chilies (name, planting_date, seeds_planted, germination_date, yield, notes) VALUES (?, ?, ?, ?, ?, ?)',
              (name, planting_date, seeds_planted,
               germination_date if germination_date else None,
               chili_yield, notes))
    conn.commit()
    st.success("Chili added!")

# Display data
st.header("📋 Chili Planting Log")
df = pd.read_sql("SELECT * FROM chilies", conn)
st.dataframe(df)

# Export option
if st.button("Export to CSV"):
    df.to_csv("chili_data.csv", index=False)
    st.download_button(label="Download CSV", data=df.to_csv(index=False).encode('utf-8'),
                       file_name="chili_data.csv", mime="text/csv")

