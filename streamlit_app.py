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
        workbook = client.open_by_url(spreadsheet_url)
        
        # Access or dynamically initialize the main projects sheet
        sheet1 = workbook.sheet1
        data_projects = sheet1.get_all_records()
        df_proj = pd.DataFrame(data_projects)
        
        # Access or dynamically initialize the relational notes sheet
        try:
            notes_sheet = workbook.worksheet("Notes")
        except gspread.exceptions.WorksheetNotFound:
            # Fallback initialization structure if sheet tab is missing entirely
            notes_sheet = workbook.add_worksheet(title="Notes", rows="100", cols="7")
            notes_sheet.append_row(["note_id", "project_id", "project_name", "date", "author_role", "case_note"])
            
        data_notes = notes_sheet.get_all_records()
        df_nt = pd.DataFrame(data_notes)
        
        return df_proj, sheet1, df_nt, notes_sheet

    except Exception as e:
        st.error(f"Failed to connect to Google Sheets Database: {e}")
        return pd.DataFrame(), None, pd.DataFrame(), None

# --- FETCH & PREPARE DATA ---
df_projects, sheet_api_client, df_notes, notes_api_client = load_data()

# Clean and normalize columns safely
if not df_projects.empty:
    if 'id' in df_projects.columns:
        df_projects['id'] = pd.to_numeric(df_projects['id'], errors='coerce')
    if 'deadline' in df_projects.columns:
        df_projects['deadline'] = pd.to_datetime(df_projects['deadline'], errors='coerce')
    if 'weekly_focus' in df_projects.columns:
        df_projects['weekly_focus'] = df_projects['weekly_focus'].astype(str).str.strip().str.upper()

if not df_notes.empty:
    if 'note_id' in df_notes.columns:
        df_notes['note_id'] = pd.to_numeric(df_notes['note_id'], errors='coerce')
    if 'project_id' in df_notes.columns:
        df_notes['project_id'] = pd.to_numeric(df_notes['project_id'], errors='coerce')
    if 'date' in df_notes.columns:
        df_notes['date'] = pd.to_datetime(df_notes['date'], errors='coerce').dt.date

# --- NATIVE WRITE BACK UTILITIES ---
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
            st.error(f"Error updating projects database: {e}")
            return False
    return False

def save_notes_to_gsheet(df_notes_to_save):
    if notes_api_client is not None:
        try:
            df_copy = df_notes_to_save.copy()
            if 'date' in df_copy.columns:
                df_copy['date'] = df_copy['date'].astype(str)
            notes_api_client.clear()
            notes_api_client.update([df_copy.columns.values.tolist()] + df_copy.values.tolist())
            return True
        except Exception as e:
            st.error(f"Error updating historical log tracking database: {e}")
            return False
    return False

# --- SECURITY & ADMIN / SUPERVISOR LOGIN ---
st.sidebar.title("🔐 Authentication Hub")
access_password = st.sidebar.text_input("Enter Access Token Profile", type="password")

IS_ADMIN = False
IS_SUPERVISOR = False

if access_password:
    try:
        if access_password == st.secrets["ADMIN_PASSWORD"]:
            IS_ADMIN = True
            st.sidebar.success("Logged in as Admin!")
        elif access_password == st.secrets.get("SUPERVISOR_PASSWORD", "superpass"):
            IS_SUPERVISOR = True
            st.sidebar.info("Logged in as Supervisor!")
        else:
            st.sidebar.error("Invalid token entry credential.")
    except KeyError:
        if access_password == "testpass":
            IS_ADMIN = True
            st.sidebar.success("Local Test Admin Access Granted!")
        elif access_password == "superpass":
            IS_SUPERVISOR = True
            st.sidebar.info("Local Test Supervisor Access Granted!")

# --- OPTIONS & GLOBAL STRUCTS ---
DEPT_OPTIONS = ["At-Promise", "ECM", "Admin", "Other"]
TYPE_OPTIONS = ["Tool", "Operations", "Forms", "Marketing", "Education", "Research", "Idea"]
STATUS_OPTIONS = ["🔵 In-Progress", "🟡 In-Progress (Delayed)", "🟠 In-Development (Idea Board)", "🔴 Pending Further Instructions", "🟢 Completed"]
ACTIVE_STATUS_OPTIONS = [s for s in STATUS_OPTIONS if s != "🟢 Completed"]

# --- DYNAMIC TEXT BADGES ---
def get_smart_date_label(target_date):
    if pd.isna(target_date):
        return ""
    if isinstance(target_date, pd.Timestamp):
        target_date = target_date.date()
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    if target_date == today:
        return "⏱️ [TODAY]"
    elif target_date == yesterday:
        return "⏳ [YESTERDAY]"
    else:
        return f"📅 [{target_date.strftime('%b %d')}]"

def get_pill_html(text, segment_type="dept"):
    colors = {
        "At-Promise": {"bg": "#dcfce7", "text": "#15803d"},
        "ECM": {"bg": "#fef9c3", "text": "#854d0e"},
        "Admin": {"bg": "#fee2e2", "text": "#991b1b"},
        "Other": {"bg": "#e0f2fe", "text": "#0369a1"},
        "🔵 In-Progress": {"bg": "#dbeafe", "text": "#1e40af"},
        "🟡 Delayed": {"bg": "#fee2e2", "text": "#991b1b"},
        "🟡 In-Progress (Delayed)": {"bg": "#fee2e2", "text": "#991b1b"},
        "🟠 In-Development (Idea Board)": {"bg": "#ffedd5", "text": "#9a3412"},
        "🔴 Pending Further Instructions": {"bg": "#fef2f2", "text": "#b91c1c"},
        "🟢 Completed": {"bg": "#dcfce7", "text": "#166534"},
        "Tool": {"bg": "#e0f2fe", "text": "#0369a1"},
        "Operations": {"bg": "#f3f4f6", "text": "#374151"},
        "Forms": {"bg": "#ffedd5", "text": "#c2410c"},
        "Marketing": {"bg": "#fee2e2", "text": "#991b1b"},
        "Education": {"bg": "#dcfce7", "text": "#15803d"},
        "Idea": {"bg": "#f3e8ff", "text": "#6b21a8"},
        "Research": {"bg": "#ecfeff", "text": "#0e7490"},
        "Admin Note": {"bg": "#f1f5f9", "text": "#475569"},
        "Supervisor Directive": {"bg": "#fef2f2", "text": "#991b1b"}
    }
    cfg = colors.get(text, {"bg": "#e2e8f0", "text": "#1e293b"})
    return f'<span style="background-color: {cfg["bg"]}; color: {cfg["text"]}; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; margin-right: 4px; display: inline-block;">{text}</span>'

# --- DATA SEPARATION ---
active_df = df_projects[df_projects["progress"] < 100] if not df_projects.empty else pd.DataFrame()
completed_df = df_projects[df_projects["progress"] == 100] if not df_projects.empty else pd.DataFrame()

# --- MAIN INTERFACE ---
st.title("My Task Dashboard")
st.write("Tracks active deliverables, dynamic timelines, supervisor instructions, and historical case note trails.")

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
col2.metric(label="Current Blockers", value=total_blocked, delta="- Clear" if total_blocked == 0 else f"{total_blocked} Attention Needed", delta_color="inverse" if total_blocked > 0 else "normal")
col3.metric(label="Shipped Portfolios", value=total_completed)

st.markdown("---")

# --- TAB DEFINITIONS ---
tabs_list = ["🎯 At a Glance", "📋 Kanban Board", "🚀 Active Projects", "✅ Completed Archive"]
if IS_ADMIN:
    tabs_list.append("➕ Add New Project")

tabs = st.tabs(tabs_list)
tab1, tab_kanban = tabs[0], tabs[1]
tab2, tab3 = tabs[2], tabs[3]
tab4 = tabs[4] if IS_ADMIN else None

# --- TAB 1: AT A GLANCE (WITH OPTION A GLOBAL FEED & OPTION B BULLET LOGS) ---
with tab1:
    st.header("🎯 Current Priorities & Activity Stream")
    
    # 📢 OPTION A: GLOBAL ACTIVITY FEED (LAST 5 TIMELINE ENTRIES)
    st.subheader("📢 Recent Case Notes & Activity Feed")
    if not df_notes.empty:
        sorted_global_notes = df_notes.sort_values(by=["date", "note_id"], ascending=[False, False]).head(5)
        for _, n_row in sorted_global_notes.iterrows():
            smart_date = get_smart_date_label(n_row["date"])
            role_label = "Supervisor Directive" if n_row["author_role"] == "Supervisor" else "Admin Note"
            badge_html = get_pill_html(role_label)
            
            with st.container(border=True):
                st.markdown(f"**{n_row['project_name']}** — {smart_date} {badge_html}", unsafe_allow_html=True)
                st.markdown(f"🖋️ {n_row['case_note']}")
    else:
        st.info("No logs added to the activity feed yet.")
    
    st.markdown("---")
    
    st.subheader("⭐ This Week's Focus")
    if not active_df.empty:
        focus_df = active_df[active_df["weekly_focus"] == "TRUE"]
        if not focus_df.empty:
            for _, row in focus_df.iterrows():
                with st.container(border=True):
                    proj_type_tag = f" | {row['project_type']}" if 'project_type' in row and row['project_type'] else ""
                    st.markdown(f"**{row['title']}** ({row['department']}{proj_type_tag})")
                    target_date = row['deadline'].strftime('%b %d, %Y') if pd.notna(row['deadline']) else "N/A"
                    progress_val = int(row['progress']) if pd.notna(row['progress']) else 0
                    
                    filled_blocks = max(0, min(100, progress_val)) // 10
                    text_bar = f"[{'■ ' * filled_blocks}{'□ ' * (10 - filled_blocks)}]"
                    st.caption(f"Progress: {progress_val}% {text_bar} | Target: {target_date}")
                    
                    # 🔍 OPTION B: PROJECT SPECIFIC CASE HISTORIES CONTEXTUALLY EMBEDDED
                    if not df_notes.empty:
                        matched_notes = df_notes[df_notes["project_id"] == row["id"]].sort_values(by="date", ascending=False)
                        if not matched_notes.empty:
                            with st.expander("📄 View Microhistory Logs for this Task", expanded=False):
                                for _, m_note in matched_notes.iterrows():
                                    lbl = "🔴 Supervisor Directive:" if m_note["author_role"] == "Supervisor" else "📝 Admin Note:"
                                    st.markdown(f"**{get_smart_date_label(m_note['date'])}** {lbl} {m_note['case_note']}")
        else:
            st.info("Routine maintenance and backlog tasks.")
    else:
        st.info("No active projects set.")

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
                    
                    # Embed local project history dropdown context
                    if not df_notes.empty:
                        matched_notes = df_notes[df_notes["project_id"] == row["id"]].sort_values(by="date", ascending=False)
                        if not matched_notes.empty:
                            with st.expander("📄 View Historical Log History", expanded=False):
                                for _, m_note in matched_notes.iterrows():
                                    lbl = "🔴 Supervisor Directive:" if m_note["author_role"] == "Supervisor" else "Admin Log:"
                                    st.markdown(f"**{get_smart_date_label(m_note['date'])}** {lbl} {m_note['case_note']}")
        else:
            st.success("No items requiring instructions at this time.")

# --- TAB: KANBAN BOARD ---
with tab_kanban:
    st.header("📋 Visual Workflow Kanban Board")
    kanban_cols = st.columns(4)
    kanban_statuses = [("🔵 In-Progress", kanban_cols[0]), ("🟡 In-Progress (Delayed)", kanban_cols[1]), ("🟠 In-Development (Idea Board)", kanban_cols[2]), ("🔴 Pending Further Instructions", kanban_cols[3])]
    
    for status_name, col_obj in kanban_statuses:
        with col_obj:
            st.markdown(f"### {status_name.split(' ')[1]}")
            st.markdown("---")
            if not df_projects.empty:
                filtered_kb = df_projects[df_projects["status"] == status_name]
                if filtered_kb.empty:
                    st.caption("_No items in stage_")
                else:
                    for _, row in filtered_kb.iterrows():
                        with st.container(border=True):
                            st.markdown(f"**{row['title']}**")
                            st.markdown(get_pill_html(row['department'], "dept"), unsafe_allow_html=True)
                            st.caption(f"Progress: {int(row['progress'])}%")

# --- TAB 2: ACTIVE PROJECTS (WITH ENGINE & DISCRETE DELETIONS) ---
with tab2:
    st.header("🚀 Ongoing Project Pipelines")
    if active_df.empty:
        st.info("No active projects found.")
    else:
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1: sel_dept = st.selectbox("Dept Filter", ["All"] + DEPT_OPTIONS, key="act_f_dept")
        with f_col2: sel_type = st.selectbox("Type Filter", ["All"] + TYPE_OPTIONS, key="act_f_type")
        with f_col3: sel_status = st.selectbox("Status Filter", ["All"] + ACTIVE_STATUS_OPTIONS, key="act_f_stat")
        with f_col4: sort_by = st.selectbox("Sort By", ["Deadline (Earliest)", "Deadline (Latest)", "Progress (Lowest)", "Progress (Highest)"], key="act_sort")
        
        filtered_active = active_df.copy()
        if sel_dept != "All": filtered_active = filtered_active[filtered_active["department"] == sel_dept]
        if sel_type != "All": filtered_active = filtered_active[filtered_active["project_type"] == sel_type]
        if sel_status != "All": filtered_active = filtered_active[filtered_active["status"] == sel_status]
        
        if sort_by == "Deadline (Earliest)": filtered_active = filtered_active.sort_values(by="deadline", ascending=True, na_position="last")
        elif sort_by == "Deadline (Latest)": filtered_active = filtered_active.sort_values(by="deadline", ascending=False, na_position="last")
        elif sort_by == "Progress (Lowest)": filtered_active = filtered_active.sort_values(by="progress", ascending=True)
        elif sort_by == "Progress (Highest)": filtered_active = filtered_active.sort_values(by="progress", ascending=False)

        st.markdown("---")

        for idx, row in filtered_active.iterrows():
            type_label = f" — {row['project_type']}" if 'project_type' in row and row['project_type'] else ""
            with st.expander(f"{row['status']} - {row['title']} — [{row['department']}{type_label}]", expanded=False):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown(f"**Description:** {row['description']}")
                    st.markdown(f"**Partners / Collaboration:** {row['partner'] if row['partner'] else 'Solo Item'}")
                    if row['notes']: st.markdown(f"**Latest Updates / Notes:** {row['notes']}")
                    
                    # Display Supervisor and Case Notes clearly inside active expander
                    st.markdown("#### 📄 Case Logs History")
                    if not df_notes.empty:
                        p_notes = df_notes[df_notes["project_id"] == row["id"]].sort_values(by=["date", "note_id"], ascending=[False, False])
                        if p_notes.empty:
                            st.caption("No historical notes logged for this assignment.")
                        else:
                            for n_idx, n_row in p_notes.iterrows():
                                is_super = (n_row["author_role"] == "Supervisor")
                                block_color = "🔴 **Supervisor Directive**:" if is_super else "📝 **Admin Note**:"
                                
                                # Inline Option A deletion wrapper tool for admin users
                                if IS_ADMIN:
                                    del_col1, del_col2 = st.columns([9, 1])
                                    with del_col1:
                                        st.markdown(f"{get_smart_date_label(n_row['date'])} {block_color} {n_row['case_note']}")
                                    with del_col2:
                                        if st.button("🗑️", key=f"del_{n_row['note_id']}"):
                                            df_notes = df_notes[df_notes["note_id"] != n_row["note_id"]]
                                            if save_notes_to_gsheet(df_notes):
                                                st.cache_data.clear()
                                                st.success("Log item expunged.")
                                                st.rerun()
                                else:
                                    st.markdown(f"{get_smart_date_label(n_row['date'])} {block_color} {n_row['case_note']}")
                    
                    # 📝 LOGGING LOG ENGINE FORM BLOCK SECTION
                    if IS_ADMIN or IS_SUPERVISOR:
                        st.markdown("---")
                        role_tag = "Supervisor" if IS_SUPERVISOR else "Admin"
                        st.markdown(f"##### ✍️ Append New {role_tag} Entry Log")
                        
                        with st.form(key=f"form_note_{row['id']}", clear_on_submit=True):
                            input_note = st.text_area("Log Narrative Entry / Directive Content", placeholder="Type notes here...")
                            submit_note = st.form_submit_button("Commit Case Entry Row")
                            
                            if submit_note and input_note:
                                next_n_id = int(df_notes['note_id'].max() + 1) if not df_notes.empty else 1
                                new_note_row = {
                                    "note_id": next_n_id,
                                    "project_id": int(row["id"]),
                                    "project_name": str(row["title"]),
                                    "date": datetime.date.today(),
                                    "author_role": role_tag,
                                    "case_note": str(input_note)
                                }
                                df_notes = pd.concat([df_notes, pd.DataFrame([new_note_row])], ignore_index=True)
                                if save_notes_to_gsheet(df_notes):
                                    st.cache_data.clear()
                                    st.success("Case history entry saved securely!")
                                    st.rerun()

                with c2:
                    target_date = row['deadline'].strftime('%b %d, %Y') if pd.notna(row['deadline']) else "N/A"
                    st.markdown(f"📆 **Deadline:** {target_date}")
                    
                    if IS_ADMIN:
                        new_progress = st.slider("Update Progress", 0, 100, int(row['progress']), key=f"p_{idx}")
                        curr_status = row['status'] if row['status'] in ACTIVE_STATUS_OPTIONS else ACTIVE_STATUS_OPTIONS[0]
                        new_status = st.selectbox("Update Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(curr_status), key=f"s_{idx}")
                        curr_type = row['project_type'] if ('project_type' in row and row['project_type'] in TYPE_OPTIONS) else TYPE_OPTIONS[0]
                        new_type = st.selectbox("Update Project Type", TYPE_OPTIONS, index=TYPE_OPTIONS.index(curr_type), key=f"t_{idx}")
                        is_focused_now = "TRUE" if row['weekly_focus'] == "TRUE" else "FALSE"
                        new_focus_selection = st.selectbox("Set Weekly Focus", options=["FALSE", "TRUE"], index=["FALSE", "TRUE"].index(is_focused_now), key=f"f_{idx}")
                        new_notes = st.text_area("Edit Update Notes", value=row['notes'], key=f"n_{idx}")
                        new_link = st.text_input("Attach Deliverable URL", value=row['link'], key=f"l_{idx}")
                        
                        if st.button("Save Changes", key=f"btn_{idx}"):
                            df_projects.at[idx, 'progress'] = 100 if new_status == "🟢 Completed" else new_progress
                            df_projects.at[idx, 'status'] = "🟢 Completed" if new_progress == 100 else new_status
                            df_projects.at[idx, 'project_type'] = new_type
                            df_projects.at[idx, 'weekly_focus'] = new_focus_selection
                            df_projects.at[idx, 'notes'] = new_notes
                            df_projects.at[idx, 'link'] = new_link
                            
                            if save_dataframe_to_gsheet(df_projects):
                                st.cache_data.clear()
                                st.success("Database sync successful!")
                                st.rerun()
                    else:
                        st.progress(int(row['progress']) / 100)
                        st.write(f"Status: **{row['status']}**")

        # 🎛️ OPTION B MANAGEMENT: RAW INTERACTIVE GRID AT BASAL ZONE
        if IS_ADMIN and not df_notes.empty:
            st.markdown("---")
            with st.expander("🛠️ Advanced Database Grid Editor (Notes Sheet)", expanded=False):
                st.write("Modify history, fix cell text typos, or prune bulk rows instantly:")
                edited_notes_df = st.data_editor(df_notes, num_rows="dynamic", key="bulk_notes_editor")
                if st.button("Commit Grid Overwrites"):
                    if save_notes_to_gsheet(edited_notes_df):
                        st.cache_data.clear()
                        st.success("Notes worksheet updated successfully!")
                        st.rerun()

# --- TAB 3: COMPLETED ARCHIVE (SUPERVISOR ACCESSIBLE MICRO-HISTORY) ---
with tab3:
    st.header("📦 Corporate Portfolio Archive")
    if completed_df.empty:
        st.info("Archive is empty.")
    else:
        arch_col1, arch_col2, arch_col3 = st.columns([1, 1, 2])
        with arch_col1: arch_dept = st.selectbox("Dept Filter", ["All"] + DEPT_OPTIONS, key="arch_f_dept")
        with arch_col2: arch_type = st.selectbox("Type Filter", ["All"] + TYPE_OPTIONS, key="arch_f_type")
        with arch_col3: arch_sort = st.selectbox("Sort By", ["Deadline (Latest)", "Deadline (Earliest)"], key="arch_sort")

        filtered_arch = completed_df.copy()
        if arch_dept != "All": filtered_arch = filtered_arch[filtered_arch["department"] == arch_dept]
        if arch_type != "All": filtered_arch = filtered_arch[filtered_arch["project_type"] == arch_type]
        filtered_arch = filtered_arch.sort_values(by="deadline", ascending=(arch_sort == "Deadline (Earliest)"), na_position="last")

        st.markdown("---")

        for idx, row in filtered_arch.iterrows():
            with st.container(border=True):
                col_arch1, col_arch2 = st.columns([3, 1])
                with col_arch1:
                    st.markdown(f"### ✅ {row['title']}")
                    tags_html = get_pill_html(row['department'], "dept")
                    if 'project_type' in row and row['project_type']:
                        tags_html += get_pill_html(row['project_type'], "type")
                    st.markdown(tags_html, unsafe_allow_html=True)
                    st.markdown(f"**Target Deadline Context:** {row['deadline'].strftime('%b %d, %Y') if pd.notna(row['deadline']) else 'N/A'}")
                    st.markdown(f"*{row['description']}*")
                    
                    # NATIVE COLLAPSED HISTORICAL TRAIL LEDGER FOR FUTURE SUPERVISORS
                    if not df_notes.empty:
                        arched_history = df_notes[df_notes["project_id"] == row["id"]].sort_values(by="date", ascending=False)
                        if not arched_history.empty:
                            with st.expander("👁️ View Complete Historical Case Notes Ledger", expanded=False):
                                for _, a_note in arched_history.iterrows():
                                    lbl_type = "🔴 Supervisor Directive:" if a_note["author_role"] == "Supervisor" else "📝 Admin Note:"
                                    st.markdown(f"**{a_note['date']}** — *{lbl_type}* {a_note['case_note']}")
                        else:
                            st.caption("No lifecycle progress logs were stored for this asset portfolio.")
                
                with col_arch2:
                    if pd.notna(row['link']) and str(row['link']).strip() != "":
                        st.link_button("📂 Access Deliverable", row['link'], use_container_width=True)

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
            submit_new = st.form_submit_button("Append to Google Sheet Database")
            
            if submit_new and new_title:
                next_id = int(df_projects['id'].max() + 1) if not df_projects.empty else 1
                new_row = {
                    "id": next_id, "title": new_title, "department": new_dept, "project_type": new_type,
                    "partner": new_partner, "progress": 100 if new_status == "🟢 Completed" else 0,
                    "status": new_status, "description": new_desc, "notes": "", "deadline": pd.to_datetime(new_deadline),
                    "weekly_focus": new_focus_choice, "link": ""
                }
                updated_df = pd.concat([df_projects, pd.DataFrame([new_row])], ignore_index=True)
                if save_dataframe_to_gsheet(updated_df):
                    st.cache_data.clear()
                    st.success(f"Successfully appended '{new_title}'!")
                    st.rerun()
