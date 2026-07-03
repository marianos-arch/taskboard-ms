import streamlit as st
import pandas as pd
import datetime
from google.oauth2.service_account import Credentials
import gspread

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Work & Project Dashboard", page_icon="📊", layout="wide")

# --- UI HELPER: COLOR-CODED PILLS ---
def create_pill_html(label, bg_color, text_color="#1f2937"):
    """Generates HTML for a stylized, color-coded pill badge."""
    return f"""
    <span style="
        background-color: {bg_color}; 
        color: {text_color}; 
        padding: 4px 10px; 
        border-radius: 12px; 
        font-size: 0.8em; 
        font-weight: 600; 
        display: inline-block; 
        margin-right: 4px; 
        margin-bottom: 4px;
        border: 1px solid rgba(0,0,0,0.05);
    ">{label}</span>
    """

# Color palettes for your specific categories
DEPT_COLORS = {
    "At-Promise": "#e0f2fe", # Light Blue
    "ECM": "#dcfce7",        # Light Green
    "Admin": "#fef08a",      # Light Yellow
    "Other": "#f3f4f6"       # Light Gray
}

TYPE_COLORS = {
    "Tool": "#c7d2fe",       # Indigo
    "Operations": "#fed7aa", # Orange
    "Forms": "#fbcfe8",      # Pink
    "Marketing": "#bfdbfe",  # Blue
    "Education": "#a7f3d0",  # Emerald
    "Research": "#e9d5ff",   # Purple
    "Idea": "#fde047"        # Yellow
}

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
        sheet = client.open_by_url(spreadsheet_url).sheet1
        
        data = sheet.get_all_records()
        return pd.DataFrame(data), sheet

    except Exception as e:
        st.error(f"Failed to connect to Google Sheets: {e}")
        return pd.DataFrame(), None

# --- FETCH & PREPARE DATA ---
df_projects, sheet_api_client = load_data()

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

# --- SECURITY & ADMIN LOGIN ---
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

# --- DATA SEPARATION ---
active_df = df_projects[df_projects["progress"] < 100] if not df_projects.empty else pd.DataFrame()
completed_df = df_projects[df_projects["progress"] == 100] if not df_projects.empty else pd.DataFrame()

# UPDATE THESE LISTS
DEPT_OPTIONS = ["At-Promise", "ECM", "Admin", "Other"]
TYPE_OPTIONS = ["Tool", "Operations", "Forms", "Marketing", "Education", "Research", "Idea"]

STATUS_OPTIONS = [
    "🔵 In-Progress", 
    "🟡 Delayed", 
    "🟠 In-Development (Idea Board)", 
    "🔴 Pending Further Instructions", 
    "🟢 Completed"
]
ACTIVE_STATUS_OPTIONS = [s for s in STATUS_OPTIONS if s != "🟢 Completed"]

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
if IS_ADMIN:
    # ADDED: New Kanban Tab
    tab1, tab_kanban, tab2, tab3, tab4 = st.tabs(["🎯 At a Glance", "📋 Kanban Board", "🚀 Active Projects", "✅ Completed Archive", "➕ Add New Project"])
else:
    tab1, tab_kanban, tab2, tab3 = st.tabs(["🎯 At a Glance", "📋 Kanban Board", "🚀 Active Projects", "✅ Completed Archive"])

# --- TAB 1: AT A GLANCE ---
with tab1:
    st.header("🎯 Current Priorities & Needs")

    st.subheader("⭐ This Week's Focus")
    if not active_df.empty:
        focus_df = active_df[active_df["weekly_focus"] == "TRUE"]
        if not focus_df.empty:
            for _, row in focus_df.iterrows():
                with st.container(border=True):
                    
                    # 🎨 IMPLEMENTATION: Apply color-coded pill tags
                    dept_color = DEPT_COLORS.get(row['department'], "#f3f4f6")
                    tags_html = create_pill_html(row['department'], dept_color)
                    
                    if 'project_type' in row and row['project_type']:
                        type_color = TYPE_COLORS.get(row['project_type'], "#f3f4f6")
                        tags_html += create_pill_html(row['project_type'], type_color)

                    st.markdown(f"**{row['title']}**<br>{tags_html}", unsafe_allow_html=True)
                    
                    target_date = row['deadline'].strftime('%b %d, %Y') if pd.notna(row['deadline']) else "N/A"
                    progress_val = max(0, min(100, int(row['progress']) if pd.notna(row['progress']) else 0)) 
                    
                    filled_blocks = progress_val // 10
                    empty_blocks = 10 - filled_blocks
                    text_bar = f"[{'■ ' * filled_blocks}{'□ ' * empty_blocks}]"
                    
                    st.caption(f"Progress: {progress_val}% {text_bar} | Target: {target_date}")
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
                    
                    progress_val = max(0, min(100, int(row['progress']) if pd.notna(row['progress']) else 0))
                    filled_blocks = progress_val // 10
                    empty_blocks = 10 - filled_blocks
                    text_bar = f"[{'■ ' * filled_blocks}{'□ ' * empty_blocks}]"
                    
                    st.caption(f"Stuck at: {progress_val}% {text_bar}")
        else:
            st.success("No items requiring instructions at this time.")
    else:
        st.success("Clear queue.")

# --- NEW TAB: KANBAN BOARD ---
with tab_kanban:
    st.header("📋 Visual Kanban Board")
    st.write("Drag-and-drop feeling layout for a quick overview of where everything stands.")
    
    if active_df.empty:
        st.info("No active projects to display on the board.")
    else:
        # Create a column for every active status
        kanban_cols = st.columns(len(ACTIVE_STATUS_OPTIONS))
        
        for idx, status_col_name in enumerate(ACTIVE_STATUS_OPTIONS):
            with kanban_cols[idx]:
                # Print column header
                st.markdown(f"**{status_col_name}**")
                
                # Filter data for this specific column
                col_df = active_df[active_df['status'] == status_col_name]
                
                if col_df.empty:
                    st.caption("Empty lane.")
                else:
                    for _, row in col_df.iterrows():
                        with st.container(border=True):
                            st.markdown(f"**{row['title']}**")
                            
                            # 🎨 Tags inside the Kanban cards
                            dept_color = DEPT_COLORS.get(row['department'], "#f3f4f6")
                            tags_html = create_pill_html(row['department'], dept_color)
                            
                            if 'project_type' in row and row['project_type']:
                                type_color = TYPE_COLORS.get(row['project_type'], "#f3f4f6")
                                tags_html += create_pill_html(row['project_type'], type_color)
                                
                            st.markdown(tags_html, unsafe_allow_html=True)
                            
                            target_date = row['deadline'].strftime('%b %d') if pd.notna(row['deadline']) else "N/A"
                            st.caption(f"📅 {target_date} | {int(row['progress'])}%")

# --- TAB 2: ACTIVE PROJECTS (Detailed view) ---
with tab2:
    st.header("🚀 Detailed Project Pipelines")
    
    if active_df.empty:
        st.info("No active projects found.")
    else:
        for idx, row in active_df.iterrows():
            
            # 🎨 Include HTML pills in expander titles (Streamlit allows light HTML in expanders now!)
            dept_color = DEPT_COLORS.get(row['department'], "#f3f4f6")
            type_color = TYPE_COLORS.get(row.get('project_type', ''), "#f3f4f6")
            tag_str = f"[{row['department']} | {row.get('project_type', '')}]"

            with st.expander(f"{row['status']} - {row['title']} — {tag_str}", expanded=False):
                c1, c2 = st.columns([2, 1])
                
                with c1:
                    st.markdown(f"**Description:** {row['description']}")
                    st.markdown(f"**Partners / Collaboration:** {row['partner'] if row['partner'] else 'Solo Item'}")
                    if row['notes']:
                        st.markdown(f"**Latest Updates / Notes:** {row['notes']}")
                
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
                        new_link = st.text_input("Attach Final Deliverable URL", value=row['link'], key=f"l_{idx}")
                        
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

# --- TAB 3: COMPLETED ARCHIVE ---
with tab3:
    st.header("📦 Corporate Portfolio Archive")
    
    if completed_df.empty:
        st.info("Archive is empty. Completed projects will automatically shift here.")
    else:
        for idx, row in completed_df.iterrows():
            with st.container(border=True):
                col_arch1, col_arch2 = st.columns([3, 1])
                with col_arch1:
                    
                    # 🎨 Add pills to archive view as well
                    dept_color = DEPT_COLORS.get(row['department'], "#f3f4f6")
                    type_color = TYPE_COLORS.get(row.get('project_type', ''), "#f3f4f6")
                    tags_html = create_pill_html(row['department'], dept_color)
                    if 'project_type' in row and row['project_type']:
                        tags_html += create_pill_html(row['project_type'], type_color)
                    
                    st.markdown(f"### ✅ {row['title']}")
                    st.markdown(tags_html, unsafe_allow_html=True)
                    
                    target_date = row['deadline'].strftime('%b %d, %Y') if pd.notna(row['deadline']) else "N/A"
                    st.markdown(f"**Target Deadline:** {target_date}")
                    st.markdown(f"*{row['description']}*")
                with col_arch2:
                    if pd.notna(row['link']) and str(row['link']).strip() != "":
                        st.link_button("📂 Access Deliverable", row['link'], use_container_width=True)
                    else:
                        st.caption("No public link attached.")

# --- TAB 4: ADMIN CREATION TAB ---
if IS_ADMIN:
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
