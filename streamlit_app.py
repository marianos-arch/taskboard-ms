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
        spreadsheet = client.open_by_url(spreadsheet_url)
        
        # Open or dynamically verify sheet structures
        sheet_projects = spreadsheet.sheet1
        data_p = sheet_projects.get_all_records()
        df_p = pd.DataFrame(data_p)
        
        # Load or catch secondary Relational Notes page
        try:
            sheet_notes = spreadsheet.worksheet("Notes")
            data_n = sheet_notes.get_all_records()
            df_n = pd.DataFrame(data_n)
        except gspread.exceptions.WorksheetNotFound:
            # Creation safety valve if tab missing
            sheet_notes = spreadsheet.add_worksheet(title="Notes", rows="100", cols="20")
            headers = ["note_id", "project_id", "project_name", "date", "author_role", "case_note"]
            sheet_notes.append_row(headers)
            df_n = pd.DataFrame(columns=headers)

        return df_p, sheet_projects, df_n, sheet_notes

    except Exception as e:
        st.error(f"Failed to connect to Google Sheets Cloud: {e}")
        return pd.DataFrame(), None, pd.DataFrame(), None

# --- FETCH & PREPARE DATA ---
df_projects, sheet_api_client, df_notes, sheet_notes_client = load_data()

# Clean and normalize datasets
if not df_projects.empty:
    if 'deadline' in df_projects.columns:
        df_projects['deadline'] = pd.to_datetime(df_projects['deadline'], errors='coerce')
    if 'weekly_focus' in df_projects.columns:
        df_projects['weekly_focus'] = df_projects['weekly_focus'].astype(str).str.strip().str.upper()

if not df_notes.empty:
    if 'date' in df_notes.columns:
        df_notes['date'] = pd.to_datetime(df_notes['date'], errors='coerce')

# --- WRITE BACK UTILITIES ---
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
            st.error(f"Error saving projects layer: {e}")
    return False

def save_notes_to_gsheet(df_to_save):
    if sheet_notes_client is not None:
        try:
            df_copy = df_to_save.copy()
            if 'date' in df_copy.columns:
                df_copy['date'] = df_copy['date'].dt.strftime('%Y-%m-%d')
            sheet_notes_client.clear()
            sheet_notes_client.update([df_copy.columns.values.tolist()] + df_copy.values.tolist())
            return True
        except Exception as e:
            st.error(f"Error synchronizing case notes table: {e}")
    return False

# --- SECURITY & AUTHENTICATION ---
st.sidebar.title("🔐 Admin Panel")
admin_password = st.sidebar.text_input("Enter Admin Password to Edit", type="password")

IS_ADMIN = False
if admin_password:
    try:
        if admin_password == st.secrets["ADMIN_PASSWORD"]:
            IS_ADMIN = True
            st.sidebar.success("Authenticated!")
        else:
            st.sidebar.error("Incorrect password.")
    except KeyError:
        if admin_password == "testpass":
            IS_ADMIN = True
            st.sidebar.success("Local Test Auth Successful!")

# --- OPTIONS LISTS ---
DEPT_OPTIONS = ["At-Promise", "ECM", "Admin", "Other"]
TYPE_OPTIONS = ["Tool", "Operations", "Forms", "Marketing", "Education", "Research", "Idea"]
STATUS_OPTIONS = ["🔵 In-Progress", "🟡 In-Progress (Delayed)", "🟠 In-Development (Idea Board)", "🔴 Pending Further Instructions", "🟢 Completed"]
ACTIVE_STATUS_OPTIONS = [s for s in STATUS_OPTIONS if s != "🟢 Completed"]

# --- HELPER: COLOR PILLS ---
def get_pill_html(text, segment_type="dept"):
    colors = {
        "At-Promise": {"bg": "#dcfce7", "text": "#15803d"},
        "ECM": {"bg": "#fef9c3", "text": "#854d0e"},
        "Admin": {"bg": "#fee2e2", "text": "#991b1b"},
        "Other": {"bg": "#e0f2fe", "text": "#0369a1"},
        "🔵 In-Progress": {"bg": "#dbeafe", "text": "#1e40af"},
        "🟡 In-Progress (Delayed)": {"bg": "#fee2e2", "text": "#991b1b"},
        "🟠 In-Development (Idea Board)": {"bg": "#ffedd5", "text": "#9a3412"},
        "🔴 Pending Further Instructions": {"bg": "#fef2f2", "text": "#b91c1c"},
        "🟢 Completed": {"bg": "#dcfce7", "text": "#166534"},
        "Tool": {"bg": "#e0f2fe", "text": "#0369a1"},
        "Operations": {"bg": "#f3f4f6", "text": "#374151"}
    }
    cfg = colors.get(text, {"bg": "#f3e8ff", "text": "#6b21a8"} if segment_type == "type" else {"bg": "#e2e8f0", "text": "#1e293b"})
    return f'<span style="background-color: {cfg["bg"]}; color: {cfg["text"]}; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; margin-right: 4px; display: inline-block;">{text}</span>'

# --- SMART TIME badge CALCULATOR ---
def get_time_badge(target_datetime):
    if pd.isna(target_datetime):
        return "N/A"
    today = datetime.date.today()
    target_date = target_datetime.date()
    delta = today - target_date
    if delta.days == 0:
        return "⏱️ [TODAY]"
    elif delta.days == 1:
        return "⏳ [YESTERDAY]"
    else:
        return f"📅 [{target_date.strftime('%b %d')}]"

# --- DATA SEGREGATION ---
active_df = df_projects[df_projects["progress"] < 100] if not df_projects.empty else pd.DataFrame()
completed_df = df_projects[df_projects["progress"] == 100] if not df_projects.empty else pd.DataFrame()

# --- MAIN DASHBOARD INTERFACE ---
st.title("My Task Dashboard")
st.write("Tracks active projects, collaborations, updates, and chronological case log streams.")

# --- METRICS LAYER ---
st.markdown("### Quick Summary")
col1, col2, col3 = st.columns(3)
if not df_projects.empty:
    total_active = len(active_df)
    total_blocked = len(df_projects[df_projects["status"] == "🔴 Pending Further Instructions"])
    total_completed = len(completed_df)
else:
    total_active, total_blocked, total_completed = 0, 0, 0

col1.metric(label="Active Pipelines", value=total_active)
col2.metric(label="Current Blockers", value=total_blocked, delta="- Clear" if total_blocked == 0 else f"{total_blocked} Urgent", delta_color="inverse" if total_blocked > 0 else "normal")
col3.metric(label="Shipped Tasks", value=total_completed)
st.markdown("---")

# --- TABS LAYOUT ---
tabs_list = ["🎯 At a Glance", "📋 Kanban Board", "🚀 Active Projects", "✅ Completed Archive"]
if IS_ADMIN:
    tabs_list.append("➕ Add New Project")
    tabs_list.append("⚙️ Notes Management")

tabs = st.tabs(tabs_list)
tab1, tab_kanban = tabs[0], tabs[1]
tab2, tab3 = tabs[2], tabs[3]
tab4 = tabs[4] if IS_ADMIN else None
tab_manage = tabs[5] if IS_ADMIN else None

# --- TAB 1: AT A GLANCE (WITH CHRONOLOGICAL FEEDS) ---
with tab1:
    st.header("🎯 At a Glance Context Grid")
    
    # --- OPTION A: GLOBAL ACTIVITY FEED ---
    st.subheader("⏱️ Recent Activity Feed (Last 5 Updates Across All Projects)")
    if not df_notes.empty:
        sorted_notes = df_notes.sort_values(by="date", ascending=False).head(5)
        if sorted_notes.empty:
            st.caption("_No notes logged in history workbook sheets._")
        else:
            for _, n_row in sorted_notes.iterrows():
                time_badge = get_time_badge(n_row['date'])
                author_lbl = f"({n_row['author_role']})" if 'author_role' in n_row else ""
                
                with st.container(border=True):
                    st.markdown(f"**{n_row['project_name']}** — {time_badge} {author_lbl}")
                    st.markdown(f"_{n_row['case_note']}_")
    else:
        st.info("No case records table active.")
        
    st.markdown("---")
    
    # --- OPTION B: PROJECT FOCUS CONTAINERS ---
    st.subheader("⭐ This Week's Focus")
    if not active_df.empty:
        focus_df = active_df[active_df["weekly_focus"] == "TRUE"]
        if not focus_df.empty:
            for _, row in focus_df.iterrows():
                with st.container(border=True):
                    st.markdown(f"**{row['title']}** ({row['department']})")
                    p_val = int(row['progress']) if pd.notna(row['progress']) else 0
                    st.caption(f"Progress Level: {p_val}% | Target: {row['deadline'].strftime('%b %d, %Y') if pd.notna(row['deadline']) else 'N/A'}")
                    
                    # Nested Option B Micro-Ledger
                    if not df_notes.empty:
                        p_notes = df_notes[df_notes["project_id"] == row["id"]].sort_values(by="date", ascending=False)
                        with st.expander("📄 Click to expand local log micro-history", expanded=False):
                            if p_notes.empty:
                                st.caption("No entry milestones yet.")
                            else:
                                for _, pn in p_notes.iterrows():
                                    st.markdown(f"• **{pn['date'].strftime('%Y-%m-%d') if pd.notna(pn['date']) else 'N/A'}** ({pn['author_role']}): {pn['case_note']}")
        else:
            st.info("Routine structural operations ongoing.")
    else:
        st.info("No active configurations found.")

# --- TAB: KANBAN BOARD ---
with tab_kanban:
    st.header("📋 Visual Workflow Kanban Board")
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
                            st.markdown(get_pill_html(row['department'], "dept"), unsafe_allow_html=True)
                            st.caption(f"Progress: {int(row['progress'])}%")

# --- TAB 2: ACTIVE PROJECTS (WITH ENGINE LOGGER) ---
with tab2:
    st.header("🚀 Ongoing Project Pipelines")
    if active_df.empty:
        st.info("Clear workflow scope pipeline.")
    else:
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1: sel_dept = st.selectbox("Department", ["All"] + DEPT_OPTIONS, key="a_dept")
        with f_col2: sel_type = st.selectbox("Project Type", ["All"] + TYPE_OPTIONS, key="a_type")
        with f_col3: sel_status = st.selectbox("Status Option", ["All"] + ACTIVE_STATUS_OPTIONS, key="a_stat")
        with f_col4: sort_by = st.selectbox("Sort Order", ["Deadline (Earliest)", "Deadline (Latest)", "Progress (Highest)"], key="a_sort")

        filtered_active = active_df.copy()
        if sel_dept != "All": filtered_active = filtered_active[filtered_active["department"] == sel_dept]
        if sel_type != "All": filtered_active = filtered_active[filtered_active["project_type"] == sel_type]
        if sel_status != "All": filtered_active = filtered_active[filtered_active["status"] == sel_status]
        
        if "Highest" in sort_by: filtered_active = filtered_active.sort_values(by="progress", ascending=False)
        elif "Latest" in sort_by: filtered_active = filtered_active.sort_values(by="deadline", ascending=False, na_position="last")
        else: filtered_active = filtered_active.sort_values(by="deadline", ascending=True, na_position="last")

        st.markdown("---")
        for idx, row in filtered_active.iterrows():
            type_label = f" — {row['project_type']}" if 'project_type' in row and row['project_type'] else ""
            with st.expander(f"{row['status']} - {row['title']} — [{row['department']}{type_label}]", expanded=False):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.markdown(f"**Description:** {row['description']}")
                    st.markdown(f"**Partners / Collaboration:** {row['partner'] if row['partner'] else 'Solo Item'}")
                    if row['notes']: st.markdown(f"**Latest Updates:** {row['notes']}")
                    
                    # --- COMPREHENSIVE CASE NOTES SUB-SECTION ---
                    st.markdown("#### 📝 Historical Case Logs")
                    if not df_notes.empty:
                        p_notes = df_notes[df_notes["project_id"] == row["id"]].sort_values(by="date", ascending=False)
                        if p_notes.empty:
                            st.caption("No registered history logs for this assignment.")
                        else:
                            for n_idx, n_row in p_notes.iterrows():
                                if n_row['author_role'] == "Supervisor Directives":
                                    st.markdown(f"⚠️ **[SUPERVISOR DIRECTIVE]** ({n_row['date'].strftime('%Y-%m-%d') if pd.notna(n_row['date']) else 'N/A'}): `{n_row['case_note']}`")
                                else:
                                    # Inline Trash Removal Mechanic for Admin Management
                                    if IS_ADMIN:
                                        t_c1, t_c2 = st.columns([6, 1])
                                        t_c1.write(f"• **{n_row['date'].strftime('%Y-%m-%d') if pd.notna(n_row['date']) else 'N/A'}** [{n_row['author_role']}]: {n_row['case_note']}")
                                        if t_c2.button("🗑️ Delete", key=f"del_inline_{n_row['note_id']}"):
                                            df_notes = df_notes[df_notes["note_id"] != n_row["note_id"]]
                                            if save_notes_to_gsheet(df_notes):
                                                st.cache_data.clear()
                                                st.success("Log item expunged!")
                                                st.rerun()
                                    else:
                                        st.write(f"• **{n_row['date'].strftime('%Y-%m-%d') if pd.notna(n_row['date']) else 'N/A'}** [{n_row['author_role']}]: {n_row['case_note']}")

                    # --- ADD NEW LOG FORM INTERFACE (ADMIN LOG INTERFACE) ---
                    if IS_ADMIN:
                        st.markdown("##### ➕ Record New Case Entry")
                        with st.form(key=f"case_form_{row['id']}", clear_on_submit=True):
                            note_txt = st.text_area("Progress Ledger Notes Context")
                            role_choice = st.selectbox("Log Context Type", ["Admin", "Supervisor Directives"], key=f"role_{row['id']}")
                            sub_note = st.form_submit_button("Append Case Note")
                            
                            if sub_note and note_txt.strip():
                                next_n_id = int(df_notes['note_id'].max() + 1) if not df_notes.empty else 1
                                new_n_row = {
                                    "note_id": next_n_id,
                                    "project_id": row['id'],
                                    "project_name": row['title'],
                                    "date": pd.to_datetime(datetime.date.today()),
                                    "author_role": role_choice,
                                    "case_note": note_txt.strip()
                                }
                                df_notes = pd.concat([df_notes, pd.DataFrame([new_n_row])], ignore_index=True)
                                if save_notes_to_gsheet(df_notes):
                                    st.cache_data.clear()
                                    st.success("Case history line successfully broadcast to storage layers!")
                                    st.rerun()

                with c2:
                    st.markdown(f"📆 **Deadline Target:** {row['deadline'].strftime('%b %d, %Y') if pd.notna(row['deadline']) else 'N/A'}")
                    if IS_ADMIN:
                        new_progress = st.slider("Progress %", 0, 100, int(row['progress']), key=f"p_{idx}")
                        new_status = st.selectbox("Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(row['status'] if row['status'] in STATUS_OPTIONS else STATUS_OPTIONS[0]), key=f"s_{idx}")
                        new_type = st.selectbox("Type", TYPE_OPTIONS, index=TYPE_OPTIONS.index(row['project_type'] if ('project_type' in row and row['project_type'] in TYPE_OPTIONS) else TYPE_OPTIONS[0]), key=f"t_{idx}")
                        new_focus = st.selectbox("Weekly Focus", ["FALSE", "TRUE"], index=["FALSE", "TRUE"].index(row['weekly_focus'] if row['weekly_focus'] in ["FALSE", "TRUE"] else "FALSE"), key=f"f_{idx}")
                        new_notes = st.text_area("Notes", value=row['notes'], key=f"n_{idx}")
                        new_link = st.text_input("Deliverable URL", value=row['link'], key=f"l_{idx}")
                        
                        if st.button("Save Row State Changes", key=f"btn_{idx}"):
                            df_projects.at[idx, 'progress'] = 100 if new_status == "🟢 Completed" else new_progress
                            df_projects.at[idx, 'status'] = "🟢 Completed" if new_progress == 100 else new_status
                            df_projects.at[idx, 'project_type'] = new_type
                            df_projects.at[idx, 'weekly_focus'] = new_focus
                            df_projects.at[idx, 'notes'] = new_notes
                            df_projects.at[idx, 'link'] = new_link
                            
                            if save_dataframe_to_gsheet(df_projects):
                                st.cache_data.clear()
                                st.success("Cloud Synchronized!")
                                st.rerun()
                    else:
                        st.progress(int(row['progress']) / 100)
                        st.write(f"Current Status: **{row['status']}**")

# --- TAB 3: COMPLETED ARCHIVE (SUPERVISOR COLLAPSIBLE LEDGER COMPATIBLE) ---
with tab3:
    st.header("Project Archive")
    if completed_df.empty:
        st.info("Archive database layers are unpopulated.")
    else:
        for idx, row in completed_df.iterrows():
            with st.container(border=True):
                col_arch1, col_arch2 = st.columns([3, 1])
                with col_arch1:
                    st.markdown(f"### ✅ {row['title']}")
                    st.markdown(get_pill_html(row['department'], "dept") + get_pill_html(row['project_type'], "type"), unsafe_allow_html=True)
                    st.markdown(f"*{row['description']}*")
                    
                    # Collapsible Supervisor/Auditor Ledger Tracker
                    st.markdown(" ")
                    with st.expander("👁️ View Complete Historical Case Notes Records", expanded=False):
                        if not df_notes.empty:
                            archived_logs = df_notes[df_notes["project_id"] == row["id"]].sort_values(by="date", ascending=False)
                            if archived_logs.empty:
                                st.caption("No case log strings associated with this historic project id.")
                            else:
                                for _, an_row in archived_logs.iterrows():
                                    st.write(f"• **{an_row['date'].strftime('%Y-%m-%d') if pd.notna(an_row['date']) else 'N/A'}** [{an_row['author_role']}]: {an_row['case_note']}")
                        else:
                            st.caption("No notes table connection array.")
                with col_arch2:
                    if pd.notna(row['link']) and str(row['link']).strip():
                        st.link_button("📂 Access Deliverable", row['link'], use_container_width=True)

# --- TAB 4: ADMIN STRUCTURAL CREATION ---
if IS_ADMIN and tab4 is not None:
    with tab4:
        st.header("➕ Add New Project Entry")
        with st.form("creation_form_unique", clear_on_submit=True):
            new_title = st.text_input("Project Title")
            new_dept = st.selectbox("Department Tag", options=DEPT_OPTIONS)
            new_type = st.selectbox("Project Type", options=TYPE_OPTIONS)
            new_partner = st.text_input("Partners")
            new_desc = st.text_area("Detailed Project Description")
            new_deadline = st.date_input("Target Completion Deadline", datetime.date.today())
            new_status = st.selectbox("Initial Status", options=STATUS_OPTIONS)
            new_focus_choice = st.selectbox("Set as Weekly Focus?", options=["FALSE", "TRUE"])
            
            if st.form_submit_button("Append to Google Sheet Database") and new_title:
                next_id = int(df_projects['id'].max() + 1) if not df_projects.empty else 1
                new_row = {
                    "id": next_id, "title": new_title, "department": new_dept, "project_type": new_type,
                    "partner": new_partner, "progress": 100 if new_status == "🟢 Completed" else 0,
                    "status": new_status, "description": new_desc, "notes": "",
                    "deadline": pd.to_datetime(new_deadline), "weekly_focus": new_focus_choice, "link": ""
                }
                updated_df = pd.concat([df_projects, pd.DataFrame([new_row])], ignore_index=True)
                if save_dataframe_to_gsheet(updated_df):
                    st.cache_data.clear()
                    st.success("Appended Successfully!")
                    st.rerun()

# --- TAB 5: ADMIN CASE NOTES DATA EDITOR TOOL ---
if IS_ADMIN and tab_manage is not None:
    with tab_manage:
        st.header("⚙️ Centralized Case Logs Advanced Management Panel")
        st.write("Clean text formatting or structural adjustments directly across the `Notes` document layout spreadsheet rows:")
        
        if not df_notes.empty:
            df_editable_notes = df_notes.copy()
            # Convert timestamp data blocks safely to clean strings for user UI edits
            if 'date' in df_editable_notes.columns:
                df_editable_notes['date'] = df_editable_notes['date'].dt.strftime('%Y-%m-%d')
                
            edited_notes_df = st.data_editor(df_editable_notes, num_rows="dynamic", use_container_width=True, key="bulk_notes_editor")
            
            if st.button("Save Bulk Grid Modifications"):
                if 'date' in edited_notes_df.columns:
                    edited_notes_df['date'] = pd.to_datetime(edited_notes_df['date'], errors='coerce')
                if save_notes_to_gsheet(edited_notes_df):
                    st.cache_data.clear()
                    st.success("Notes worksheet successfully written back to Google Sheet structure maps!")
                    st.rerun()
        else:
            st.info("Notes ledger dataset holds no structural lines to edit.")
