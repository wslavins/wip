import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Title
st.title("Cal Poly Pre-Award Workload Dashboard")

# Upload file
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file, engine="openpyxl")

    # Data Cleaning
    omit_statuses = ['Award Received', 'Post-award Intake', 'Declined', 'Turned Away', 'Withdrawn']
    df = df[~df['Record Status'].isin(omit_statuses)]
    df = df.dropna(subset=['PreAward Analyst', 'Deadline Date'])

    df['Deadline Date'] = pd.to_datetime(df['Deadline Date'])
    df['WeekStart'] = df['Deadline Date'] - pd.to_timedelta(df['Deadline Date'].dt.dayofweek, unit='d')

    # User Input for Deadline Date
    input_date = st.date_input("Select a Deadline Date:", datetime.today())
    input_week_start = input_date - timedelta(days=input_date.weekday())

    # Filter for the selected week
    week_data = df[df['WeekStart'] == input_week_start]
    
    if not week_data.empty:
        st.subheader(f"Rows per Analyst for the Week of {input_week_start.date()}")
        st.dataframe(week_data.groupby('PreAward Analyst')['Record Number'].count().reset_index())
        
        # Visualization
        fig = px.bar(week_data.groupby('PreAward Analyst')['Record Number'].count().reset_index(), 
                     x='PreAward Analyst', y='Record Number', title="Workload Per Analyst", text_auto=True)
        st.plotly_chart(fig)
    else:
        st.warning("No deadlines found for the selected week.")

