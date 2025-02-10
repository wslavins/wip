import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os, json

# =============================================================================
# APP TITLE & SETTINGS
# =============================================================================
st.title("Cal Poly Pre-Award Workload Dashboard")

# Password Protection
password = st.text_input("Enter password to access the dashboard:", type="password")
if password != "grants2025":
    st.error("Incorrect password. Please try again.")
    st.stop()

# Editable lists at the top:
omit_statuses = ['Award Received', 'Post-award Intake', 'Declined', 'Turned Away', 'Withdrawn']
analysts_list = [
    'Gartner, Susanne B',
    'Alvord, Tyler',
    'Dolengewicz, Julie F',
    'Vazquez-Lozada, Anxo',
    'Lijiam, Nazareth',
    'Simon, Kathy'
]

# Create a mapping from full name to first name for display purposes.
name_mapping = {full: full.split(',')[1].strip().split()[0] for full in analysts_list}

# -----------------------------------------------------------------------------
# Initialize custom workload storage in session state and load persisted data
# -----------------------------------------------------------------------------
if 'custom_workload' not in st.session_state:
    st.session_state.custom_workload = {}

filename = "custom_workload.json"
if os.path.exists(filename):
    with open(filename, "r") as f:
        persistent_data = json.load(f)
    for key_str, value in persistent_data.items():
        # The key is stored as "Analyst|WeekStart" (e.g., "Tyler|2025-01-06")
        analyst, week = key_str.split("|")
        st.session_state.custom_workload[(analyst, week)] = value

# -----------------------------------------------------------------------------
# Define Cal Poly holidays for 2025-2026 (used for notification deadline calculation)
# -----------------------------------------------------------------------------
calpoly_holidays = [
    datetime(2025, 1, 1).date(),    # New Year's Day
    datetime(2025, 1, 20).date(),   # Martin Luther King, Jr., holiday
    datetime(2025, 3, 31).date(),   # Cesar Chavez Day
    datetime(2025, 5, 26).date(),   # Memorial Day
    datetime(2025, 6, 19).date(),   # Juneteenth
    datetime(2025, 7, 4).date(),    # Independence Day
    datetime(2025, 9, 1).date(),    # Labor Day
    datetime(2025, 11, 11).date(),  # Veterans’ Day
    datetime(2025, 11, 27).date(),  # Thanksgiving Day
    datetime(2025, 11, 28).date(),  # Lincoln’s Birthday observed
    datetime(2025, 12, 25).date(),  # Christmas Day observed
    datetime(2025, 12, 26).date(),  # Washington’s Birthday observed
    datetime(2025, 12, 29).date(),  # California Admission Day observed
    datetime(2025, 12, 30).date(),  # Indigenous Peoples’ Day observed
    datetime(2025, 12, 31).date(),  # Campus closed (anticipated Governor/President holiday)
    datetime(2026, 1, 1).date(),    # New Year's Day
    datetime(2026, 1, 19).date()    # Martin Luther King, Jr., holiday
]

# =============================================================================
# SECTION 1: CUSTOM WORKLOAD INPUT (Hidden by default in an expander)
# =============================================================================
with st.expander("Set Custom Workload Level (Click to Expand)"):
    with st.form("workload_form"):
        selected_analyst = st.selectbox("Select your name:", list(name_mapping.values()))
        workload_week_date = st.date_input("Select a Week (any day in the week):", datetime.today())
        # Calculate the start of the week (Monday) for the selected date.
        workload_week_start = workload_week_date - timedelta(days=workload_week_date.weekday())
        workload_percent = st.slider("Select Workload Percentage (0-150%):", min_value=0, max_value=150, value=100)
        workload_reasoning = st.text_area("Reasoning for differing workload:", 
                                          help="Provide a brief explanation for the adjusted workload.")
        workload_submit = st.form_submit_button("Submit Workload Level")
        if workload_submit:
            key = (selected_analyst, str(workload_week_start))
            st.session_state.custom_workload[key] = {"percentage": workload_percent, "reasoning": workload_reasoning}
            # Persist the custom workload info to a JSON file.
            if os.path.exists(filename):
                with open(filename, "r") as f:
                    data = json.load(f)
            else:
                data = {}
            data_key = f"{selected_analyst}|{workload_week_start}"
            data[data_key] = {"percentage": workload_percent, "reasoning": workload_reasoning}
            with open(filename, "w") as f:
                json.dump(data, f)
            st.success(f"Set custom workload for {selected_analyst} for week starting {workload_week_start} to {workload_percent}% with reasoning: {workload_reasoning}")

# =============================================================================
# SECTION 2: EXCEL UPLOAD, WORKLOAD GRAPH & DEADLINE/NOTIFICATION DATE
# =============================================================================
st.header("Workload Overview")
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
if uploaded_file:
    # --------------------------
    # Read and Clean Data
    # --------------------------
    df = pd.read_excel(uploaded_file, engine="openpyxl")
    df = df[~df['Record Status'].isin(omit_statuses)]
    df = df.dropna(subset=['PreAward Analyst', 'Deadline Date'])
    df['Deadline Date'] = pd.to_datetime(df['Deadline Date'], errors='coerce')
    df = df.dropna(subset=['Deadline Date'])
    # Calculate the week start for each deadline (Monday)
    df['WeekStart'] = df['Deadline Date'] - pd.to_timedelta(df['Deadline Date'].dt.dayofweek, unit='d')
    df['WeekStart_date'] = df['WeekStart'].dt.date

    # --------------------------
    # Function to Subtract Working Days (skipping weekends and Cal Poly holidays)
    # --------------------------
    def subtract_working_days(end_date, working_days):
        current_date = end_date
        days_subtracted = 0
        while days_subtracted < working_days:
            current_date -= timedelta(days=1)
            if current_date.weekday() < 5 and current_date not in calpoly_holidays:
                days_subtracted += 1
        return current_date

    # --------------------------
    # Deadline Search Form
    # --------------------------
    with st.form("search_form"):
        input_date = st.date_input("Select a Deadline Date (to choose a week):", datetime.today(), key="deadline_date")
        search_submit = st.form_submit_button("Search")
    if search_submit:
        # Compute notification date (20 working days before deadline)
        notification_date = subtract_working_days(input_date, 20)
        today_date = datetime.today().date()
        if notification_date > today_date:
            notif_color = "green"
        elif notification_date == today_date:
            notif_color = "gold"
        else:
            notif_color = "red"
        st.markdown(f"<h4 style='color:{notif_color};'>Notification Date: {notification_date}</h4>", unsafe_allow_html=True)

        # Calculate the week start (Monday) for the selected deadline date.
        input_week_start = input_date - timedelta(days=input_date.weekday())
        st.write(f"Selected week start: {input_week_start}")
        # Filter data for the selected week.
        week_data = df[df['WeekStart_date'] == input_week_start]
        st.write(f"Rows found for selected week: {len(week_data)}")

        # --------------------------
        # Build Proposals Info for Hover Text
        # --------------------------
        proposals_info = {}
        for _, row in week_data.iterrows():
            full_name = row['PreAward Analyst']
            if full_name in name_mapping:
                first_name = name_mapping[full_name]
                proposal_str = f"{row['Record Number']}: {row['Record Owner']}"
                proposals_info.setdefault(first_name, []).append(proposal_str)

        # --------------------------
        # Group Data by Analyst
        # --------------------------
        if not week_data.empty:
            analyst_counts = week_data.groupby('PreAward Analyst')['Record Number'].count().reset_index()
            analyst_counts.rename(columns={'Record Number': 'Count'}, inplace=True)
        else:
            analyst_counts = pd.DataFrame(columns=['PreAward Analyst', 'Count'])
        analyst_counts = analyst_counts[analyst_counts['PreAward Analyst'].isin(name_mapping.keys())]
        analyst_counts['PreAward Analyst'] = analyst_counts['PreAward Analyst'].map(name_mapping)
        all_analysts_data = pd.DataFrame({
            'PreAward Analyst': list(name_mapping.values()),
            'Count': [0] * len(name_mapping)
        })
        final_data = pd.merge(all_analysts_data, analyst_counts, how='left', on='PreAward Analyst', suffixes=('_default', ''))
        final_data['Count'] = final_data['Count'].fillna(0).astype(int)

        # --------------------------
        # Determine Custom Maximum Workload per Analyst for this Week
        # --------------------------
        def get_custom_max(analyst, week):
            key = (analyst, str(week))
            if key in st.session_state.custom_workload:
                percent = st.session_state.custom_workload[key].get("percentage", 100)
                return round(4 * percent / 100)
            else:
                return 4
        final_data['custom_max'] = final_data['PreAward Analyst'].apply(lambda a: get_custom_max(a, input_week_start))

        # --------------------------
        # Add Color Column for the Bar Chart Based on Count:
        # --------------------------
        final_data['color'] = final_data['Count'].apply(lambda x: 'green' if x <= 2 else ('yellow' if x == 3 else 'red'))
        muted_colors = {'green': '#66c2a5', 'yellow': '#ffd92f', 'red': '#fc8d62'}

        final_data = final_data.sort_values(by='PreAward Analyst').reset_index(drop=True)
        final_data['y'] = list(range(len(final_data)))

        st.session_state['final_data'] = final_data
        st.session_state['input_week_start'] = input_week_start
        st.session_state['input_date'] = input_date

        # --------------------------
        # Create Custom Hover Text for Each Analyst Bar
        # --------------------------
        hovertexts = []
        for analyst in final_data['PreAward Analyst']:
            proposals = proposals_info.get(analyst, [])
            if proposals:
                hovertexts.append("<br>".join(proposals))
            else:
                hovertexts.append("No proposals")
        st.session_state['hovertexts'] = hovertexts

    # --------------------------
    # Display the Workload Chart (if available)
    # --------------------------
    if "final_data" in st.session_state:
        final_data = st.session_state["final_data"]
        hovertexts = st.session_state.get("hovertexts", ["No proposals"] * len(final_data))
        muted_colors = {'green': '#66c2a5', 'yellow': '#ffd92f', 'red': '#fc8d62'}
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=final_data['Count'],
            y=final_data['y'],
            orientation="h",
            marker_color=[muted_colors[c] for c in final_data['color']],
            text=final_data['Count'],
            textposition="auto",
            showlegend=False,
            hovertext=hovertexts,
            hovertemplate="%{hovertext}<extra></extra>"
        ))
        for idx, row in final_data.iterrows():
            delta = 0.05
            y_center = row['y']
            x_val = row['custom_max']
            fig.add_shape(
                type="rect",
                x0=x_val - delta,
                x1=x_val + delta,
                y0=y_center - 0.4,
                y1=y_center + 0.4,
                line=dict(color="black", width=2),
                fillcolor="black",
                layer="above"
            )
        # Add invisible scatter markers over the black boxes to display reasoning on hover.
        marker_x = []
        marker_y = []
        marker_text = []
        for idx, row in final_data.iterrows():
            key = (row['PreAward Analyst'], str(st.session_state['input_week_start']))
            reasoning = st.session_state.custom_workload.get(key, {}).get("reasoning", "No reasoning provided")
            marker_x.append(row['custom_max'])
            marker_y.append(row['y'])
            marker_text.append(reasoning)
        fig.add_trace(go.Scatter(
            x=marker_x,
            y=marker_y,
            mode='markers',
            marker=dict(size=20, opacity=0),
            hoverinfo='text',
            hovertext=marker_text,
            showlegend=False
        ))
        fig.update_yaxes(
            tickmode="array",
            tickvals=final_data['y'],
            ticktext=final_data['PreAward Analyst'],
            automargin=True
        )
        fig.update_layout(
            title="Workload Per Analyst",
            xaxis_title="Number of Proposals",
            yaxis_title="Analyst",
            font=dict(color="black"),
            showlegend=False
        )
        st.plotly_chart(fig)

        # =============================================================================
        # SECTION 3: ASSIGNMENTS & ASSIGNMENT RECOMMENDATION
        # =============================================================================
        st.header("Assignment Recommendation")
        assignments_data = pd.DataFrame({
            "Analyst": [
                "Anxo",
                "Julie",
                "Kathy",
                "Nazareth",
                "Susanne",
                "Tyler"
            ],
            "Departments Assigned": [
                "Orfalea College of Business, Biomedical Engineering, California Cybersecurity Institute, Dean's Office, Electrical Engineering, Materials Engineering, Mechanical Engineering, Multicultural Engineering Program, General Engineering, Information Technology Services",
                "College of Agriculture, Food & Environmental Sciences, Agricultural Education and Communication, Animal Science, BioResource and Agricultural Engineering, Cal Poly Strawberry Center, Dean's Office, Food Science & Nutrition, Military Science, Natural Resources Management & Environmental Sciences, Swanton Pacific Ranch, Wine and Viticulture",
                "Various Academic Affairs Administration & Finance, College of Architecture and Environmental Design, College of Liberal Arts Division of Research, Bailey College of Science & Mathematics, University Development and Alumni Engagement, ARI Campus PAF/award processing, McIntire-Stennis proposals and award processing; Architectural Engineering, Architecture, City and Regional Planning, Construction Management, Landscape Architecture, Art and Design, Communication Studies, English, Ethnic Studies, Graphic Communication, History, Interdisciplinary Studies, Journalism, Music, Philosophy, Political Science, Psychology, Social Sciences, Theatre & Dance, Women's, Gender & Queer Studies, World Languages, Mathematics, Development and Alumni Engagement",
                "Agribusiness, Experience Industry Management, Plant Sciences, Biological Sciences, Dean's Office, Liberal Studies, School of Education, Statistics, Student Academic Services, Student Affairs",
                "Irrigation Training and Research Center, Chemistry and Biochemistry, Kinesiology and Public Health, Physics, Campus Health & Wellbeing, Center for Service in Action, Dean of Students, Student Life & Leadership, Office of the President",
                "Aerospace Engineering, Civil & Environmental Engineering, Computer Engineering, Computer Science & Software Engineering, Industrial & Manufacturing Engineering, Cal Poly Corporation"
            ],
            "Primary Backup Analyst": [
                "Tyler",
                "Nazareth",
                "Julie",
                "Julie",
                "Nazareth",
                "Anxo"
            ]
        })

        def group_departments(dept_string):
            depts = [dept.strip() for dept in dept_string.split(",")]
            groups = {
                "Academic": [],
                "Engineering": [],
                "Science": [],
                "Center/Institute": [],
                "Administration": [],
                "Arts/Communication": [],
                "Other": []
            }
            for d in depts:
                d_lower = d.lower()
                if "college" in d_lower or "university" in d_lower or "education" in d_lower or "studies" in d_lower:
                    groups["Academic"].append(d)
                elif "engineering" in d_lower:
                    groups["Engineering"].append(d)
                elif ("science" in d_lower or "biology" in d_lower or "chemistry" in d_lower or "physics" in d_lower \
                      or "mathematics" in d_lower or "statistics" in d_lower) and "engineering" not in d_lower:
                    groups["Science"].append(d)
                elif "institute" in d_lower or "center" in d_lower:
                    groups["Center/Institute"].append(d)
                elif "office" in d_lower or "dean" in d_lower or "administration" in d_lower or "services" in d_lower:
                    groups["Administration"].append(d)
                elif "art" in d_lower or "design" in d_lower or "communication" in d_lower or "journalism" in d_lower \
                      or "music" in d_lower or "theatre" in d_lower:
                    groups["Arts/Communication"].append(d)
                else:
                    groups["Other"].append(d)
            output_lines = []
            order = ["Academic", "Engineering", "Science", "Center/Institute", "Administration", "Arts/Communication", "Other"]
            for key in order:
                if groups[key]:
                    output_lines.append(f"<strong>{key}:</strong> " + ", ".join(groups[key]))
            return "<br>".join(output_lines)

        if st.checkbox("Show Assignments", key="show_assignments_checkbox"):
            st.subheader("Analyst Assignments")
            display_assignments_data = assignments_data.copy()
            display_assignments_data["Departments Assigned"] = display_assignments_data["Departments Assigned"].apply(group_departments)
            css = """
            <style>
            table {width: 100%; border-collapse: collapse;}
            th, td {vertical-align: top; padding: 5px; border: 1px solid #ccc; text-align: left;}
            </style>
            """
            st.markdown(css, unsafe_allow_html=True)
            st.markdown(display_assignments_data.to_html(index=False, escape=False), unsafe_allow_html=True)

        departments_list = []
        for depts in assignments_data["Departments Assigned"]:
            for dept in depts.split(","):
                dept = dept.strip()
                if dept and dept not in departments_list:
                    departments_list.append(dept)
        departments_list.sort()

        selected_department = st.selectbox("Select Department for Proposal Assignment", departments_list, key="dept_select")
        if st.button("Recommend Assignment", key="recommend_assignment"):
            row_found = None
            for idx, row in assignments_data.iterrows():
                if selected_department.lower() in row["Departments Assigned"].lower():
                    row_found = row
                    break
            if row_found is None:
                st.error("No matching analyst found for the selected department.")
            else:
                primary_analyst = row_found["Analyst"]
                backup_analyst = row_found["Primary Backup Analyst"]
                final_data = st.session_state["final_data"]
                primary_row = final_data[final_data["PreAward Analyst"] == primary_analyst]
                backup_row = final_data[final_data["PreAward Analyst"] == backup_analyst]
                primary_count = int(primary_row["Count"].iloc[0]) if not primary_row.empty else 0
                primary_max = int(primary_row["custom_max"].iloc[0]) if not primary_row.empty else 4
                backup_count = int(backup_row["Count"].iloc[0]) if not backup_row.empty else 0
                backup_max = int(backup_row["custom_max"].iloc[0]) if not backup_row.empty else 4

                if primary_count < primary_max:
                    st.success(f"Assign the proposal to **{primary_analyst}** (Primary Analyst). Current workload: {primary_count}/{primary_max}.")
                elif backup_count < backup_max:
                    st.warning(f"Primary analyst **{primary_analyst}** is at capacity ({primary_count}/{primary_max}). Recommend assigning to backup analyst **{backup_analyst}**. Current workload: {backup_count}/{backup_max}.")
                else:
                    st.error(f"Both primary analyst **{primary_analyst}** and backup analyst **{backup_analyst}** are at capacity. No assignment possible at this time.")
