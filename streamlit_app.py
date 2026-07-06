import streamlit as st
import pandas as pd
import datetime
from google.oauth2.service_account import Credentials
import gspread

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Work & Project Dashboard", page_icon="📊", layout="wide")

# --- DATABASE CONNECTION (Google Sheets via Dynamic Secrets & gspread) ---
@st.cache_data(ttl=0)  # Setting to 0 for instant testing updates!
def load_data():
    try:
        # 1. Pull the raw private key string directly from Streamlit Secrets
        raw_key = st.secrets["connections"]["gsheets"]["private_key"]
        
        # 2. Automatically repair any double-escaped literal "\n" text into actual line breaks
        private_key = raw_key.replace("\\n", "\n")
        
        # 3. Ensure the key block has perfectly clean single newlines
        while "\n\n" in private_key:
            private_key = private_key.replace("\n\n", "\n")

        # 4. Reconstruct the full Google Account JSON structure using your exact secrets
        info = {
            "type": "service_account",
            "project_id": st.secrets["connections"]["gsheets"]["project_id"],
            "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
            "private_key": private_key,
            "client_email": st.secrets["connections"]["gsheets"]["client_email"],
            "client_id": st.secrets["connections"]["gsheets"]["client_id"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": st.secrets["connections"]["gsheets"]["client_x509_cert_url"],
            "universe_domain": "googleapis.com"
        }

        # 5. Authenticate via Google OAuth
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)

        # 6. Access the Google Sheet document via its URL
        spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet = client.open_by_url(spreadsheet_url).sheet1
        
        data = sheet.get_all_records()
        return pd.DataFrame(data), sheet

    except Exception as e:
        st.error(f"Failed to connect to Google Sheets: {e}")
        return pd.DataFrame(), None

@st.cache_data(ttl=0)
def load_notes_data():
    """Fetches records from the secondary tab worksheet named 'Notes'"""
    try:
        raw_key = st.secrets["connections"]["gsheets"]["private_key"]
        private_key = raw_key.replace("\\n", "\n")
        while "\n\n" in private_key:
            private_key = private_key.replace("\n\n", "\n")

        info = {
            "type": "service_account",
            "project_id": st.secrets["connections"]["gsheets"]["project_id"],
            "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
            "private_key": private_key,
            "client_email": st.secrets["connections"]["gsheets"]["client_email"],
            "client_id": st.secrets["connections"]["gsheets"]["client_id"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": st.secrets["connections"]["gsheets"]["client_x509_cert_url"],
            "universe_domain": "googleapis.com"
        }

        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)

        spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        notes_sheet = client.open_by_url(spreadsheet_url).worksheet("Notes")
        
        data = notes_sheet.get_all_records()
        return pd.DataFrame(data), notes_sheet
    except Exception as e:
        return pd.DataFrame(), None


def save_notes_to_gsheet(df_notes_to_save, notes_api_client):
    """Saves updated case notes back down to the 'Notes' worksheet grid"""
    if notes_api_client is not None:
        try:
            notes_api_client.clear()
            notes_api_client.update([df_notes_to_save.columns.values.tolist()] + df_notes_to_save.values.tolist())
            return True
        except Exception as e:
            st.error(f"Error saving down history log records: {e}")
            return False
    return False


def parse_relative_date(date_val):
    """Parses dynamic text tags [TODAY] or [YESTERDAY] for the activity stream"""
    try:
        target_dt = pd.to_datetime(date_val).date()
        today_dt = datetime.date.today()
        if target_dt == today_dt:
            return "[TODAY]"
        elif target_dt == today_dt - datetime.timedelta(days=1):
            return "[YESTERDAY]"
        else:
            return f"[{target_dt.strftime('%b %d')}]"
    except Exception:
        return "📝 [LOG]"

# --- FETCH & PREPARE DATA ---
df_projects, sheet_api_client = load_data()
df_notes, sheet_notes_client = load_notes_data()


# Clean and normalize columns
if not df_projects.empty:
    if 'deadline' in df_projects.columns:
        df_projects['deadline'] = pd.to_datetime(df_projects['deadline'], errors='coerce')
    
    if 'weekly_focus' in df_projects.columns:
        df_projects['weekly_focus'] = df_projects['weekly_focus'].astype(str).str.strip().str.upper()

# --- HELPER FUNCTION: NATIVE WRITE BACK VIA GSPREAD ---
def save_dataframe_to_gsheet(df_to_save):
    if sheet_api_client is not None:
        try:
            df_copy = df_to_save.copy()
            if 'deadline' in df_copy.columns:
                df_copy['deadline'] = df_copy['deadline'].dt.strftime('%Y-%m-%d')
            
            sheet_api_client.clear()
            sheet_api_client.update([df_copy.columns.values.tolist()] + df_copy.values.tolist())
            return True
        except Exception as e:
            st.error(f"Error saving down data rows: {e}")
            return False
    return False

# --- SECURITY & AUTHENTICATION PORTAL ---
st.sidebar.title("🔐 Authentication Portal")
admin_password = st.sidebar.text_input("Enter Admin Password", type="password")
supervisor_password = st.sidebar.text_input("Enter Supervisor Password", type="password")

IS_ADMIN = False
IS_SUPERVISOR = False

# Evaluate Admin Credentials
if admin_password:
    try:
        if admin_password == st.secrets["ADMIN_PASSWORD"]:
            IS_ADMIN = True
            st.sidebar.success("👑 Admin Mode Active")
        else:
            st.sidebar.error("Incorrect Admin password.")
    except KeyError:
        if admin_password == "testpass":
            IS_ADMIN = True
            st.sidebar.success("Local Test Auth Successful!")

# Evaluate Supervisor Credentials
if supervisor_password:
    try:
        if supervisor_password == st.secrets["SUPERVISOR_PASSWORD"]:
            IS_SUPERVISOR = True
            st.sidebar.success("📋 Supervisor Mode Active")
        else:
            st.sidebar.error("Incorrect Supervisor password.")
    except KeyError:
        if supervisor_password == "superpass":
            IS_SUPERVISOR = True
            st.sidebar.success("Local Test Supervisor Active!")

# Determine if user has any form editing permissions
HAS_EDIT_ACCESS = IS_ADMIN or IS_SUPERVISOR

# --- OPTIONS LISTS ---
DEPT_OPTIONS = ["At-Promise", "ECM", "Admin", "Other"]
TYPE_OPTIONS = ["Tool", "Operations", "Forms", "Marketing", "Education", "Research", "Idea"]

STATUS_OPTIONS = [
    "🔵 In-Progress", 
    "🟡 In-Progress (Delayed)", 
    "🟠 In-Development (Idea Board)", 
    "🔴 Pending Further Instructions", 
    "🟢 Completed"
]
ACTIVE_STATUS_OPTIONS = [s for s in STATUS_OPTIONS if s != "🟢 Completed"]

# --- HELPER FUNCTION: COLOR-CODED PILLS ---
def get_pill_html(text, segment_type="dept"):
    colors = {
        "At-Promise": {"bg": "#dcfce7", "text": "#15803d"},    # Pastel Green
        "ECM": {"bg": "#fef9c3", "text": "#854d0e"},           # Pastel Yellow
        "Admin": {"bg": "#fee2e2", "text": "#991b1b"},         # Light Red
        "Other": {"bg": "#e0f2fe", "text": "#0369a1"},         # Pastel Blue
        
        "🔵 In-Progress": {"bg": "#dbeafe", "text": "#1e40af"},
        "🟡 Delayed": {"bg": "#fee2e2", "text": "#991b1b"},
        "🟡 In-Progress (Delayed)": {"bg": "#fee2e2", "text": "#991b1b"},
        "🟠 In-Development (Idea Board)": {"bg": "#ffedd5", "text": "#9a3412"},
        "🔴 Pending Further Instructions": {"bg": "#fef2f2", "text": "#b91c1c"},
        "🟢 Completed": {"bg": "#dcfce7", "text": "#166534"},

        # Product / Project Types
        "Tool": {"bg": "#e0f2fe", "text": "#0369a1"},          # Light Blue
        "Operations": {"bg": "#f3f4f6", "text": "#374151"},    # Light Grey
        "Forms": {"bg": "#ffedd5", "text": "#c2410c"},         # Pastel Orange
        "Marketing": {"bg": "#fee2e2", "text": "#991b1b"},     # Red
        "Education": {"bg": "#dcfce7", "text": "#15803d"},     # Light Green
        "Idea": {"bg": "#f3e8ff", "text": "#6b21a8"},          # Light Purple
        "Research": {"bg": "#ecfeff", "text": "#0e7490"}       # Cyan
    }
    
    cfg = colors.get(text, {"bg": "#f0fdf4", "text": "#15803d"} if segment_type == "type" else {"bg": "#e2e8f0", "text": "#1e293b"})
    return f'<span style="background-color: {cfg["bg"]}; color: {cfg["text"]}; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; margin-right: 4px; display: inline-block;">{text}</span>'

# --- DATA SEPARATION ---
active_df = df_projects[df_projects["progress"] < 100] if not df_projects.empty else pd.DataFrame()
completed_df = df_projects[df_projects["progress"] == 100] if not df_projects.empty else pd.DataFrame()

# --- MAIN INTERFACE ---
st.title("My Task Dashboard")
st.write("Hello! This is my dashboard that tracks my active projects, collaborations, ideas, and general tasks given to me.")

# --- METRICS SECTION ---
st.markdown("### Quick Summary")
col1, col2, col3 = st.columns(3)

if not df_projects.empty:
    total_active = len(active_df)
    total_blocked = len(df_projects[df_projects["status"] == "🔴 Pending Further Instructions"])
    total_completed = len(completed_df)
else:
    total_active, total_blocked, total_completed = 0, 0, 0

col1.metric(label="Active Projects", value=total_active)
col2.metric(
    label="Current Blockers", 
    value=total_blocked, 
    delta="- Clear" if total_blocked == 0 else f"{total_blocked} Attention Needed",
    delta_color="inverse" if total_blocked > 0 else "normal"
)
col3.metric(label="Shipped Portfolios", value=total_completed)

st.markdown("---")

# --- TAB DEFINITIONS ---
tabs_list = ["🎯 At a Glance", "📋 Kanban Board", "🚀 Active Projects", "✅ Completed"]
if IS_ADMIN:
    tabs_list.append("➕ Add New Project")

tabs = st.tabs(tabs_list)
tab1, tab_kanban = tabs[0], tabs[1]
tab2, tab3 = tabs[2], tabs[3]
tab4 = tabs[4] if IS_ADMIN else None

# --- TAB 1: AT A GLANCE ---
with tab1:
    st.header("Current Priorities & Changes")

    st.subheader("This Week's Focus")
    if not active_df.empty:
        focus_df = active_df[active_df["weekly_focus"] == "TRUE"]
        if not focus_df.empty:
            for _, row in focus_df.iterrows():
                with st.container(border=True):
                    # 1. Title and HTML Colored Pills
                    dept_pill = get_pill_html(row['department'], "dept")
                    type_pill = get_pill_html(row['project_type'], "type") if 'project_type' in row and row['project_type'] else ""
                    
                    st.markdown(f"### {row['title']}")
                    st.markdown(f"{dept_pill}{type_pill}", unsafe_allow_html=True)
                    
                    # 2. Progress Metric and Target Deadlines
                    target_date = row['deadline'].strftime('%b %d, %Y') if pd.notna(row['deadline']) else "N/A"
                    progress_val = int(row['progress']) if pd.notna(row['progress']) else 0
                    progress_val = max(0, min(100, progress_val)) 

                    filled_blocks = progress_val // 10
                    empty_blocks = 10 - filled_blocks
                    text_bar = f"[{'■ ' * filled_blocks}{'□ ' * empty_blocks}]"

                    st.markdown(f"**Progress:** {progress_val}% &nbsp;&nbsp; ` {text_bar} ` &nbsp;&nbsp; | &nbsp;&nbsp; **Target Date:** {target_date}")
                    
                    # 3. Dynamic Injection of the Latest Note for this Project
                    if not df_notes.empty and 'id' in row:
                        specific_notes = df_notes[df_notes["project_id"] == row["id"]]
                        if not specific_notes.empty:
                            # Pull the absolute most recent entry
                            latest_project_note = specific_notes.sort_values(by="note_id", ascending=False).iloc[0]
                            time_badge = parse_relative_date(latest_project_note['date'])
                            role_label = f" ({latest_project_note['author_role']})" if 'author_role' in latest_project_note and latest_project_note['author_role'] else ""
                            
                            st.markdown("""<div style='margin-top: 10px; margin-bottom: 2px; font-size: 13px; font-weight: 600; color: #555;'>📌 Latest Progress Note:</div>""", unsafe_allow_html=True)
                            st.info(f"*{time_badge}* — **{latest_project_note['author']}{role_label}:** {latest_project_note['case_note']}")
                        else:
                            st.caption("_No explicit case timeline updates logged for this asset yet._")
                    else:
                        st.caption("_No explicit case timeline updates logged for this asset yet._")
        else:
            st.info("Routine maintenance and backlog tasks.")
    else:
        st.info("No active projects set.")

    st.markdown(" ")
    st.markdown("---")
    st.markdown(" ")

    # --- NEW: OPTION A (GLOBAL TIMELINE FEED) ---
    st.subheader("Recent Activity Feed")
    if not df_notes.empty:
        # Sort values with newest notes at the very top, grab top 5 entries
        latest_notes = df_notes.sort_values(by="note_id", ascending=False).head(5)
        for _, n_row in latest_notes.iterrows():
            time_badge = parse_relative_date(n_row['date'])
            role_label = f" ({n_row['author_role']})" if 'author_role' in n_row and n_row['author_role'] else ""
            
            with st.container(border=True):
                st.markdown(f"**{n_row['project_name']}** — *{time_badge}*")
                st.caption(f"**{n_row['author']}{role_label} logged:** {n_row['case_note']}")
    else:
        st.info("No timeline case logs recorded in database registry yet.")
        
    st.markdown(" ")
    st.markdown("---")
    st.markdown(" ") 

    st.subheader("⚠️ Pending Instructions & Decisions")
    if not active_df.empty:
        blocked_df = active_df[active_df["status"] == "🔴 Pending Further Instructions"]
        if not blocked_df.empty:
            for _, row in blocked_df.iterrows():
                with st.container(border=True):
                    st.markdown(f"🔴 **{row['title']}**")
                    st.markdown(f"**Current Impediment:** {row['notes']}")
                    progress_val = int(row['progress']) if pd.notna(row['progress']) else 0
                    progress_val = max(0, min(100, progress_val))
                    filled_blocks = progress_val // 10
                    empty_blocks = 10 - filled_blocks
                    text_bar = f"[{'■ ' * filled_blocks}{'□ ' * empty_blocks}]"

                    st.caption(f"Stuck at: {progress_val}% {text_bar}")
        else:
            st.success("No items requiring instructions at this time.")
    else:
        st.success("Clear queue.")


# --- TAB: KANBAN BOARD ---
with tab_kanban:
    st.header("Visual Workflow Kanban Board")
    st.write("Dynamic columns grouped automatically by task status definitions.")
    
    kanban_cols = st.columns(4)
    
    kanban_statuses = [
        ("🔵 In-Progress", kanban_cols[0]),
        ("🟡 In-Progress (Delayed)", kanban_cols[1]),
        ("🟠 In-Development (Idea Board)", kanban_cols[2]),
        ("🔴 Pending Further Instructions", kanban_cols[3])
    ]
    
    for status_name, col_obj in kanban_statuses:
        with col_obj:
            st.markdown(f"### {status_name.split(' ')[0]} {status_name.split(' ')[1]}")
            st.markdown("---")
            
            if not df_projects.empty:
                filtered_kb = df_projects[df_projects["status"] == status_name]
                if filtered_kb.empty:
                    st.caption("_No items in this status stage_")
                else:
                    for _, row in filtered_kb.iterrows():
                        with st.container(border=True):
                            st.markdown(f"**{row['title']}**")
                            dept_pill = get_pill_html(row['department'], "dept")
                            st.markdown(dept_pill, unsafe_allow_html=True)
                            
                            p_val = int(row['progress']) if pd.notna(row['progress']) else 0
                            st.caption(f"Progress: {p_val}%")
            else:
                st.caption("_Empty Dataset_")


# --- TAB 2: ACTIVE PROJECTS (WITH FILTER ENGINE) ---
with tab2:
    st.header(" Ongoing Project ")
    
    if active_df.empty:
        st.info("No active projects found.")
    else:
        # Subtle inline filter toolbar
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1:
            sel_dept = st.selectbox("Dept Filter", ["All"] + DEPT_OPTIONS, key="act_f_dept")
        with f_col2:
            sel_type = st.selectbox("Type Filter", ["All"] + TYPE_OPTIONS, key="act_f_type")
        with f_col3:
            sel_status = st.selectbox("Status Filter", ["All"] + ACTIVE_STATUS_OPTIONS, key="act_f_stat")
        with f_col4:
            sort_by = st.selectbox("Sort By", ["Deadline (Earliest)", "Deadline (Latest)", "Progress (Lowest)", "Progress (Highest)"], key="act_sort")
        
        # Apply logic filtering
        filtered_active = active_df.copy()
        if sel_dept != "All":
            filtered_active = filtered_active[filtered_active["department"] == sel_dept]
        if sel_type != "All":
            filtered_active = filtered_active[filtered_active["project_type"] == sel_type]
        if sel_status != "All":
            filtered_active = filtered_active[filtered_active["status"] == sel_status]
            
        # Apply sorting logic
        if sort_by == "Deadline (Earliest)":
            filtered_active = filtered_active.sort_values(by="deadline", ascending=True, na_position="last")
        elif sort_by == "Deadline (Latest)":
            filtered_active = filtered_active.sort_values(by="deadline", ascending=False, na_position="last")
        elif sort_by == "Progress (Lowest)":
            filtered_active = filtered_active.sort_values(by="progress", ascending=True)
        elif sort_by == "Progress (Highest)":
            filtered_active = filtered_active.sort_values(by="progress", ascending=False)

        st.markdown("---")

        if filtered_active.empty:
            st.caption("No active items matching your selection filters.")
        else:
            for idx, row in filtered_active.iterrows():
                type_label = f" — {row['project_type']}" if 'project_type' in row and row['project_type'] else ""
                with st.expander(f"{row['status']} - {row['title']} — [{row['department']}{type_label}]", expanded=True):
                    c1, c2 = st.columns([2, 1])
                    
                    with c1:
                        st.markdown(f"**Description:** {row['description']}")
                        st.markdown(f"**Partners / Collaboration:** {row['partner'] if row['partner'] else 'Solo Item'}")
                        if row['notes']:
                            st.markdown(f"**Latest Updates / Notes:** {row['notes']}")
                    
                    with c2:
                        target_date = row['deadline'].strftime('%b %d, %Y') if pd.notna(row['deadline']) else "N/A"
                        st.markdown(f"📆 **Deadline:** {target_date}")
                        
                        if HAS_EDIT_ACCESS:
                            new_progress = st.slider("Update Progress", 0, 100, int(row['progress']), key=f"p_{idx}")
                            curr_status = row['status'] if row['status'] in ACTIVE_STATUS_OPTIONS else ACTIVE_STATUS_OPTIONS[0]
                            new_status = st.selectbox("Update Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(curr_status), key=f"s_{idx}")
                            
                            curr_type = row['project_type'] if ('project_type' in row and row['project_type'] in TYPE_OPTIONS) else TYPE_OPTIONS[0]
                            new_type = st.selectbox("Update Project Type", TYPE_OPTIONS, index=TYPE_OPTIONS.index(curr_type), key=f"t_{idx}")

                            is_focused_now = "TRUE" if row['weekly_focus'] == "TRUE" else "FALSE"
                            new_focus_selection = st.selectbox("Set Weekly Focus", options=["FALSE", "TRUE"], index=["FALSE", "TRUE"].index(is_focused_now), key=f"f_{idx}")
                            
                            new_notes = st.text_area("Edit Update Notes", value=row['notes'], key=f"n_{idx}")
                            new_link = st.text_input("Attach Final Deliverable URL", value=row['link'], key=f"l_{idx}")
                            st.markdown("#### 📝 Project Case Notes Manager")

                            # A. Display Context History Linked by Unique relational ID
                            if not df_notes.empty and 'id' in row:
                                proj_notes = df_notes[df_notes["project_id"] == row["id"]].sort_values(by="note_id", ascending=False)
                                if not proj_notes.empty:
                                    st.write("Current Logs History:")
                                    for n_idx, n_row in proj_notes.iterrows():
                                        cn_col1, cn_col2 = st.columns([5, 1])
                                        with cn_col1:
                                            # Differentiate regular admin entries from Supervisor Directives
                                            note_style = f"ℹ️ **Supervisor Directive:** {n_row['case_note']}" if n_row.get('author_role') == "Supervisor" else f"{n_row['case_note']}"
                                            st.caption(f"**{n_row['date']}** by *{n_row['author']}*: {note_style}")
                                        with cn_col2:
                                            # Option A: Quick delete option
                                            if st.button("Delete", key=f"del_note_{n_row['note_id']}_{idx}"):
                                                df_notes_updated = df_notes[df_notes["note_id"] != n_row["note_id"]]
                                                if save_notes_to_gsheet(df_notes_updated, sheet_notes_client):
                                                    st.cache_data.clear()
                                                    st.success("Note row dropped!")
                                                    st.rerun()
                                            
                            # B. Add a New Case Note Record form
                            with st.form(key=f"add_note_form_{idx}", clear_on_submit=True):
                                new_case_txt = st.text_area("Write progress or case timeline commentary note:")
                                
                                # Dynamic drop-down construction depending on who authenticated
                                available_roles = []
                                if IS_ADMIN:
                                    available_roles.append("Admin")
                                if IS_SUPERVISOR:
                                    available_roles.append("Supervisor")
                                    
                                as_role = st.selectbox("Log Note Identity Role As:", available_roles, key=f"role_choice_{idx}")
                                submit_note = st.form_submit_button("Append Note to History")
                                
                                if submit_note and new_case_txt:
                                    next_note_id = int(df_notes['note_id'].max() + 1) if not df_notes.empty else 1
                                    new_note_row = {
                                        "note_id": next_note_id,
                                        "project_id": row['id'],
                                        "project_name": row['title'], # Keeps title mirror backup clean
                                        "date": datetime.date.today().strftime('%Y-%m-%d'),
                                        "author": "Supervisor Name" if as_role == "Supervisor" else "Admin Dashboard",
                                        "author_role": as_role,
                                        "case_note": new_case_txt if as_role == "Supervisor" else new_case_txt
                                    }
                                    
                                    if df_notes.empty:
                                        updated_notes_df = pd.DataFrame([new_note_row])
                                    else:
                                        updated_notes_df = pd.concat([df_notes, pd.DataFrame([new_note_row])], ignore_index=True)
                                        
                                    if save_notes_to_gsheet(updated_notes_df, sheet_notes_client):
                                        st.cache_data.clear()
                                        st.success("History tracking note captured successfully!")
                                        st.rerun()
                                                        
                            if st.button("Save Changes", key=f"btn_{idx}"):
                                if new_status == "🟢 Completed":
                                    df_projects.at[idx, 'progress'] = 100
                                else:
                                    df_projects.at[idx, 'progress'] = new_progress
                                    
                                df_projects.at[idx, 'status'] = "🟢 Completed" if new_progress == 100 else new_status
                                df_projects.at[idx, 'project_type'] = new_type
                                df_projects.at[idx, 'weekly_focus'] = new_focus_selection
                                df_projects.at[idx, 'notes'] = new_notes
                                df_projects.at[idx, 'link'] = new_link
                                
                                if save_dataframe_to_gsheet(df_projects):
                                    st.cache_data.clear()
                                    st.success("Database rows synchronized successfully!")
                                    st.rerun()
                        else:
                            st.write("Progress Meter:")
                            st.progress(int(row['progress']) / 100)
                            st.write(f"Current Status: **{row['status']}**")
                            if row['weekly_focus'] == "TRUE":
                                st.warning("🎯 Marked as a high priority for this week.")


# --- TAB 3: COMPLETED ARCHIVE (WITH FILTER ENGINE) ---
with tab3:
    st.header("Project Archive")
    
    if completed_df.empty:
        st.info("Archive is empty. Completed projects will automatically shift here.")
    else:
        # Subtle inline filter toolbar
        arch_col1, arch_col2, arch_col3 = st.columns([1, 1, 2])
        with arch_col1:
            arch_dept = st.selectbox("Dept Filter", ["All"] + DEPT_OPTIONS, key="arch_f_dept")
        with arch_col2:
            arch_type = st.selectbox("Type Filter", ["All"] + TYPE_OPTIONS, key="arch_f_type")
        with arch_col3:
            arch_sort = st.selectbox("Sort By", ["Deadline (Latest)", "Deadline (Earliest)"], key="arch_sort")

        # Apply logic filtering
        filtered_arch = completed_df.copy()
        if arch_dept != "All":
            filtered_arch = filtered_arch[filtered_arch["department"] == arch_dept]
        if arch_type != "All":
            filtered_arch = filtered_arch[filtered_arch["project_type"] == arch_type]

        # Apply sorting logic
        if arch_sort == "Deadline (Latest)":
            filtered_arch = filtered_arch.sort_values(by="deadline", ascending=False, na_position="last")
        elif arch_sort == "Deadline (Earliest)":
            filtered_arch = filtered_arch.sort_values(by="deadline", ascending=True, na_position="last")

        st.markdown("---")

        if filtered_arch.empty:
            st.caption("No archived items matching your selection filters.")
        else:
            for idx, row in filtered_arch.iterrows():
                with st.container(border=True):
                    col_arch1, col_arch2 = st.columns([3, 1])
                    with col_arch1:
                        st.markdown(f"### ✅ {row['title']}")
                        
                        tags_html = get_pill_html(row['department'], "dept")
                        if 'project_type' in row and row['project_type']:
                            tags_html += get_pill_html(row['project_type'], "type")
                        st.markdown(tags_html, unsafe_allow_html=True)
                        
                        target_date = row['deadline'].strftime('%b %d, %Y') if pd.notna(row['deadline']) else "N/A"
                        st.markdown(f"**Completed Date:** {target_date}")
                        
                        if 'image_url' in row and pd.notna(row['image_url']) and str(row['image_url']).strip() != "":
                            raw_url = str(row['image_url']).strip()
                            if "drive.google.com/file/d/" in raw_url:
                                try:
                                    file_id = raw_url.split("/file/d/")[1].split("/")[0]
                                    display_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"
                                except Exception:
                                    display_url = raw_url
                            else:
                                display_url = raw_url

                            img_col, spacer_col = st.columns([2, 3])
                            with img_col:
                                st.image(display_url, caption=f"Preview: {row['title']}", use_container_width=True)
                        else:
                            st.caption("📷 No preview image attached for this project.")
                        
                        st.markdown(f"*{row['description']}*")

                        if not df_notes.empty and 'id' in row:
                            archived_history_notes = df_notes[df_notes["project_id"] == row["id"]].sort_values(by="note_id", ascending=False)
                            if not archived_history_notes.empty:
                                with st.expander("👁️ View Complete Historical Audit Case Notes Trailing Log", expanded=False):
                                    for _, an_row in archived_history_notes.iterrows():
                                        role_tag = f" [{an_row['author_role']}]" if 'author_role' in an_row and an_row['author_role'] else ""
                                        st.markdown(f"• **{an_row['date']}** ({an_row['author']}{role_tag}): {an_row['case_note']}")        
                                                
                    with col_arch2:
                        if pd.notna(row['link']) and str(row['link']).strip() != "":
                            st.link_button("📂 Access Project", row['link'], use_container_width=True)
                        else:
                            st.caption("No link attached.")


# --- TAB 4: ADMIN CREATION TAB ---
if IS_ADMIN and tab4 is not None:
    with tab4:
        st.header("➕ Add New Project Entry")
        with st.form("creation_form_unique", clear_on_submit=True):
            new_title = st.text_input("Project / Assignment Title")
            new_dept = st.selectbox("Department / Segment Tag", options=DEPT_OPTIONS)
            new_type = st.selectbox("Project Type", options=TYPE_OPTIONS)
            new_partner = st.text_input("Partners (Separated by commas)")
            new_desc = st.text_area("Detailed Project Description")
            new_deadline = st.date_input("Target Completion Deadline", datetime.date.today())
            new_status = st.selectbox("Initial Status", options=STATUS_OPTIONS)
            new_focus_choice = st.selectbox("Set as Weekly Focus?", options=["FALSE", "TRUE"])
            
            st.form_submit_button("Append to Google Sheet Database")
            
            if submit_new and new_title:
                next_id = int(df_projects['id'].max() + 1) if not df_projects.empty else 1
                init_progress = 100 if new_status == "🟢 Completed" else 0
                
                new_row = {
                    "id": next_id,
                    "title": new_title,
                    "department": new_dept,
                    "project_type": new_type,
                    "partner": new_partner,
                    "progress": init_progress,
                    "status": new_status,
                    "description": new_desc,
                    "notes": "",
                    "deadline": pd.to_datetime(new_deadline),
                    "weekly_focus": new_focus_choice,
                    "link": ""
                }
                
                updated_df = pd.concat([df_projects, pd.DataFrame([new_row])], ignore_index=True)
                
                if save_dataframe_to_gsheet(updated_df):
                    st.cache_data.clear()
                    st.success(f"Successfully appended '{new_title}' to the cloud database!")
                    st.rerun()
