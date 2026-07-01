import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Work & Project Dashboard", page_icon="📊", layout="wide")

# --- DATABASE CONNECTION (Google Sheets) ---
# This creates a secure connection to your Google Sheet using Streamlit Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)  # Caches data for 1 minute to keep the app fast
def load_data():
    try:
        # Pulls the data and ensures data types are correct
        df = conn.read()
        df['deadline'] = pd.to_datetime(df['deadline']).dt.date
        df['progress'] = df['progress'].astype(int)
        df['weekly_focus'] = df['weekly_focus'].astype(bool)
        return df
    except Exception as e:
        # Fallback to empty structure if sheet is empty or not yet connected
        return pd.DataFrame(columns=[
            "id", "title", "department", "partner", "progress", 
            "status", "description", "notes", "deadline", "weekly_focus", "link"
        ])

df_projects = load_data()

# --- SECURITY & ADMIN LOGIN ---
st.sidebar.title("🔐 Admin Panel")
admin_password = st.sidebar.text_input("Enter Admin Password to Edit", type="password")

# Verify password against Streamlit Secrets (set this up in your Streamlit Cloud Dashboard)
# For local testing, you can use a fallback string like "admin123"
IS_ADMIN = False
if admin_password:
    try:
        if admin_password == st.secrets["ADMIN_PASSWORD"]:
            IS_ADMIN = True
            st.sidebar.success("Authenticated! Edit mode unlocked.")
        else:
            st.sidebar.error("Incorrect password.")
    except KeyError:
        # Fallback for local testing if secrets file doesn't exist yet
        if admin_password == "testpass":
            IS_ADMIN = True
            st.sidebar.success("Local Test Auth Successful!")

# --- DATA SEPARATION ---
active_df = df_projects[df_projects["progress"] < 100] if not df_projects.empty else pd.DataFrame()
completed_df = df_projects[df_projects["progress"] == 100] if not df_projects.empty else pd.DataFrame()

# --- MAIN INTERFACE ---
st.title("🎈 My Work & Project Dashboard")
st.write("Welcome! This dashboard tracks my active corporate projects, cross-departmental collaborations, and historical deliverables.")

# --- METRICS SECTION (Executive Summary) ---
st.markdown("### 📊 Executive Summary")
col1, col2, col3 = st.columns(3)

if not df_projects.empty:
    total_active = len(active_df)
    total_blocked = len(df_projects[df_projects["status"] == "🔴 Blocked"])
    total_completed = len(completed_df)
else:
    total_active, total_blocked, total_completed = 0, 0, 0

col1.metric(label="Active Projects", value=total_active)
# Displays a green indicator if blockers are 0, otherwise standard format
col2.metric(
    label="Current Blockers", 
    value=total_blocked, 
    delta="- Clear" if total_blocked == 0 else f"{total_blocked} Attention Needed",
    delta_color="inverse" if total_blocked > 0 else "normal"
)
col3.metric(label="Shipped Portfolios", value=total_completed)

st.markdown("---")

# --- TAB STRUCTURE ---
tab1, tab2, tab3 = st.tabs(["🎯 At a Glance", "🚀 Active Projects", "✅ Completed Archive"])

# --- TAB 1: AT A GLANCE ---
with tab1:
    st.header("🎯 Current Priorities & Needs")
    
    col_focus, col_block = st.columns(2)
    
    with col_focus:
        st.subheader("⭐ This Week's Focus")
        if not active_df.empty:
            focus_df = active_df[active_df["weekly_focus"] == True]
            if not focus_df.empty:
                for _, row in focus_df.iterrows():
                    with st.container(border=True):
                        st.markdown(f"**{row['title']}** ({row['department']})")
                        st.caption(f"Progress: {row['progress']}% | Target: {row['deadline'].strftime('%b %d, %Y')}")
            else:
                st.info("Routine maintenance and backlog tasks.")
        else:
            st.info("No active projects set.")

    with col_block:
        st.subheader("⚠️ Blockers & Ideas Needed")
        if not active_df.empty:
            blocked_df = active_df[active_df["status"] == "🔴 Blocked"]
            if not blocked_df.empty:
                for _, row in blocked_df.iterrows():
                    with st.container(border=True):
                        st.markdown(f"🔴 **{row['title']}**")
                        st.markdown(f"**Current Impediment:** {row['notes']}")
            else:
                st.success("No current blockages reported.")
        else:
            st.success("Clear queue.")

# --- TAB 2: ACTIVE PROJECTS ---
with tab2:
    st.header("🚀 Ongoing Project Pipelines")
    
    if active_df.empty:
        st.info("No active projects found.")
    else:
        for idx, row in active_df.iterrows():
            with st.expander(f"{row['status']} {row['title']} — [{row['department']}]", expanded=True):
                c1, c2 = st.columns([2, 1])
                
                with c1:
                    st.markdown(f"**Description:** {row['description']}")
                    st.markdown(f"**Partners / Collaboration:** {row['partner'] if row['partner'] else 'Solo Item'}")
                    if row['notes']:
                        st.markdown(f"**Latest Updates / Notes:** {row['notes']}")
                
                with c2:
                    st.markdown(f"📆 **Deadline:** {row['deadline'].strftime('%B %d, %Y')}")
                    
                    # IF ADMIN LOGGED IN: Render Controls to Change Sheet Live
                    # --- ADMIN VIEW: ADD NEW PROJECT FORM ---
                    if IS_ADMIN:
                        st.markdown("---")
                        st.header("➕ Add New Project Entry")
                        with st.form("creation_form_unique", clear_on_submit=True):
                            new_title = st.text_input("Project / Assignment Title")
                            
                            # 🏢 MATCHING YOUR GOOGLE SHEET DEPARTMENTS EXACTLY
                            dept_options = ["Marketing", "Engineering", "Operations", "Product", "Sales", "Accounting", "External"]
                            new_dept = st.selectbox("Department / Segment Tag", options=dept_options)
                            
                            new_partner = st.text_input("Partners (Separated by commas)")
                            new_desc = st.text_area("Detailed Project Description")
                            new_deadline = st.date_input("Target Completion Deadline", datetime.date.today())
                            
                            # 🚦 MATCHING YOUR GOOGLE SHEET STATUS EXACTLY
                            status_options = ["🟢 On Track", "🟡 Delayed", "🔴 Blocked", "🟢 Completed"]
                            new_status = st.selectbox("Initial Status", options=status_options)
                            
                            # 🎯 MATCHING YOUR GOOGLE SHEET WEEKLY FOCUS (BOOLEAN)
                            # Using a selectbox with Python True/False mapping
                            new_focus_choice = st.selectbox("Set as Weekly Focus?", options=["No", "Yes"])
                            new_focus = True if new_focus_choice == "Yes" else False
                            
                            submit_new = st.form_submit_button("Append to Google Sheet Database")
                            
                            if submit_new and new_title:
                                # Generate next numeric id
                                next_id = int(df_projects['id'].max() + 1) if not df_projects.empty else 1
                                
                                new_row = {
                                    "id": next_id,
                                    "title": new_title,
                                    "department": new_dept,     # Saved from dropdown
                                    "partner": new_partner,
                                    "progress": 0,
                                    "status": new_status,       # Saved from dropdown
                                    "description": new_desc,
                                    "notes": "",
                                    "deadline": new_deadline,
                                    "weekly_focus": new_focus,   # Saved from dropdown conversion
                                    "link": ""
                                }
                                
                                # Append new entry, update sheets database, and refresh
                                updated_df = pd.concat([df_projects, pd.DataFrame([new_row])], ignore_index=True)
                                conn.update(data=updated_df)
                                st.cache_data.clear()
                                st.success(f"Successfully appended '{new_title}' to the cloud database!")
                                st.rerun()

                        # Save Changes Button for this specific project
                        if st.button("Save Changes", key=f"btn_{idx}"):
                            df_projects.at[idx, 'progress'] = new_progress
                            df_projects.at[idx, 'status'] = "🟢 Completed" if new_progress == 100 else new_status
                            df_projects.at[idx, 'weekly_focus'] = new_focus
                            df_projects.at[idx, 'notes'] = new_notes
                            df_projects.at[idx, 'link'] = new_link
                            
                            # Push entire updated DataFrame back to Google Sheets
                            conn.update(data=df_projects)
                            st.cache_data.clear() # Wipe cache to show changes instantly
                            st.rerun()
                    else:
                        # GUEST VIEW (Read-Only Status Display)
                        st.write("Progress Meter:")
                        st.progress(int(row['progress']) / 100)
                        st.write(f"Current Status: **{row['status']}**")
                        if row['weekly_focus']:
                            st.warning("🎯 Marked as a high priority for this week.")

# --- TAB 3: COMPLETED ARCHIVE ---
with tab3:
    st.header("📦 Corporate Portfolio Archive")
    st.write("This archive houses finalized deliverables, transforming routine work history into an accessible asset portfolio.")
    
    if completed_df.empty:
        st.info("Archive is empty. Completed projects will automatically shift here.")
    else:
        for idx, row in completed_df.iterrows():
            with st.container(border=True):
                col_arch1, col_arch2 = st.columns([3, 1])
                with col_arch1:
                    st.markdown(f"### ✅ {row['title']}")
                    st.markdown(f"**Department:** {row['department']} | **Target Deadline:** {row['deadline'].strftime('%b %d, %Y')}")
                    st.markdown(f"*{row['description']}*")
                with col_arch2:
                    if pd.notna(row['link']) and str(row['link']).strip() != "":
                        st.link_button("📂 Access Deliverable", row['link'], use_container_width=True)
                    else:
                        st.caption("No public link attached.")

# --- ADMIN VIEW: ADD NEW PROJECT FORM ---
if IS_ADMIN:
    st.markdown("---")
    st.header("➕ Add New Project Entry")
    with st.form("new_project_form", clear_on_submit=True):
        new_title = st.text_input("Project / Assignment Title")
        new_dept = st.text_input("Department / Segment Tag")
        new_partner = st.text_input("Partners (Separated by commas)")
        new_desc = st.text_area("Detailed Project Description")
        new_deadline = st.date_input("Target Completion Deadline", datetime.date.today())
        
        submit_new = st.form_submit_button("Append to Google Sheet Database")
        
        if submit_new and new_title:
            # Generate next numeric id
            next_id = int(df_projects['id'].max() + 1) if not df_projects.empty else 1
            
            new_row = {
                "id": next_id,
                "title": new_title,
                "department": new_dept,
                "partner": new_partner,
                "progress": 0,
                "status": "🟢 On Track",
                "description": new_desc,
                "notes": "",
                "deadline": new_deadline,
                "weekly_focus": False,
                "link": ""
            }
            
            # Append new entry, update sheets database, and refresh
            updated_df = pd.concat([df_projects, pd.DataFrame([new_row])], ignore_index=True)
            conn.update(data=updated_df)
            st.cache_data.clear()
            st.success(f"Successfully appended '{new_title}' to the cloud database!")
            st.rerun()
