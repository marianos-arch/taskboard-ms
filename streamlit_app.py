import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
from google.oauth2.service_account import Credentials
import gspread

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Work & Project Dashboard", page_icon="📊", layout="wide")

# --- DATABASE CONNECTION (Google Sheets via Raw Service Account) ---
@st.cache_data(ttl=0)  # Setting to 0 for instant testing updates!
def load_data():
    try:
        # 1. Stitch the private key together flawlessly in Python
        private_key = (
            "-----BEGIN PRIVATE KEY-----\n"
            "MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDlZXU5AT1OHRKz\n"
            "qRzNPBNoSzMnpkQ6VZgi6JcKd37edbLvqAIRMsCqFxs+dSeOjWDbecCSG7k6pHVT\n"
            "b7QSy7T6CY9smaoFj3ketUvZsiEv+DIWnr+0Uk/i6ERK5mRaXoCe92iedXfWggan\n"
            "3X7LELqlQ5whxlW7WpwWBY0FQodzK0tYy/ITx4z6G7bQWhC4n1etk0D5HEtN/bzd\n"
            "mzOHBtUoLDQJD80+OS5bt0QVjv8dWmG8Cyf71IzROU0FJkUrGr4MweTpiYcArckK\n"
            "AtchYyv3B82e9F7gtql1FHOrNMjHdT6mYwr4yTpyY36S/UYHaS/mEiPYkjQ+7rbu\n"
            "3TnlWQYhAgMBAAECggEAARSpCHd3xzguWB/WFaZwjfd6undXT3ILSTDQ01kMRTaH\n"
            "PQdM2TFkxHhe5byuDsceO3J3pIiSZxMSxW2bitIgXGQyo4eWzDdokes3PAORkfUI\n"
            "oWAmlY4kt7Qx7CtpMh7LWtReDw8NHTrYFq7ds820n2Yx5FvXmA4deaIVj76IPlPl\n"
            "2q+8Qjs30HOpSRLGjgmnQ84BHLd4Jx62BA1IxDMv9pctp42BdI93F9yw9S+ayt4F\n"
            "wszZhdhYpAG/ZwAFkSfBEWf3VoOZzDo89VeRO9rXPDHWk7XamCDNfMHvGr2iuHyI\n"
            "xTCmmOYDxoDKTqGBh7PcEQ6d79KuB+RgoqS0PyhEAQKBgQDzLUwon4MuInXodWLq\n"
            "U0CFiF4Lf/MQ5/UXPSdH5P0pI055K/qsPExfA/nFAHicgSQ3es7ZgFpuf9q/nMu3\n"
            "/utzWzZ3Tn5fB86IqmT7fU796kZ79c1guG4Q2WTlNKCYLHWwAsjFTNjDvGV5BQ3/\n"
            "Ev6BE02qZFR0xafS9Co7YgIWoQKBgQDxfiHuYQI1PnuHrt3BL+zE6ehfyLEcD4Aj\n"
            "npZfujE+ZjBuBde2HxG0zZgO1flZ0dc8+gjtquB0O5KLTQ+8e9MerkjdGPMdSZrRl\n"
            "aVZ8+aBwWjhItQZnRFpTvR/QPFbdYchpw2IQ+tKta4WJqXOZsmIrDrqHmXTM40be\n"
            "KG+Cdno/gQKBgAqs2WQLJJoY3y42QQJiZzm1c9NzaXs7g5HimF/amJZ+u0oseROo\n"
            "jf250fQpAiJ0tN9On9gCf3XMXRD+VB8erL1iqrBwHLIVSKbNPCOiK56P80orzzlI\n"
            "v2Qz9u7s8YPcp8nzRVcL+ZQWKCo445VoAw4th8JMJzz9FFH5cAUtV0QhAoGBALEs\niaRrU8VgjBzl7IgZ8yodOoFbqqUdsjN1AFzh0Fyk8GEw9g4PzNZS2BHGGQPkkyIX\n"
            "RiRr49XTZKp/QuaBTCTSZ38+hDYuZ9enSu7x7gXAC188gPAus96P+NE8E7bkULdX\nw5EVlI/rPNPc4JU4zNEuQyfNLGZNsOa43+blqZcBAoGBALM5gszM20oDDd3nS4b6\n"
            "Fwa+WO36lj/QAlXlb4YXwoTrFaB6gmbSWV4fS61ANoep7fUPw1DXKFMBe+Dqm3i6\npThrZPcxUsWxlCHiSEqvy8+i7GWs59Ddss3Ac/yxypDrn3jU4GRARJ8ZC5uoAXck\n"
            "ZcB7+NOAe+WTkHhfXcG4vKAk\n"
            "-----END PRIVATE KEY-----\n"
        )

        # 2. Reconstruct the full Google Account JSON mapping dynamically inside Python
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

        # 3. Setup scopes and authenticate natively
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)

        # 4. Pull the worksheet directly using your spreadsheet URL
        spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet = client.open_by_url(spreadsheet_url).sheet1
        
        # 5. Extract rows and return data as a Pandas DataFrame
        data = sheet.get_all_records()
        return pd.DataFrame(data)

    except Exception as e:
        st.error(f"Failed to connect to Google Sheets: {e}")
        return pd.DataFrame()

# Fetch data using the robust native connector
df = load_data()

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
col2.metric(
    label="Current Blockers", 
    value=total_blocked, 
    delta="- Clear" if total_blocked == 0 else f"{total_blocked} Attention Needed",
    delta_color="inverse" if total_blocked > 0 else "normal"
)
col3.metric(label="Shipped Portfolios", value=total_completed)

st.markdown("---")

# --- TAB DEFINITIONS ---
# If you are an Admin, we add a 4th tab dynamically!
if IS_ADMIN:
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 At a Glance", "🚀 Active Projects", "✅ Completed Archive", "➕ Add New Project"])
else:
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
                    
                    if IS_ADMIN:
                        new_progress = st.slider("Update Progress", 0, 100, int(row['progress']), key=f"p_{idx}")
                        new_status = st.selectbox("Update Status", ["🟢 On Track", "🟡 Delayed", "🔴 Blocked"], index=["🟢 On Track", "🟡 Delayed", "🔴 Blocked"].index(row['status']), key=f"s_{idx}")
                        new_focus = st.checkbox("Set Weekly Focus", value=bool(row['weekly_focus']), key=f"f_{idx}")
                        new_notes = st.text_area("Edit Update Notes", value=row['notes'], key=f"n_{idx}")
                        new_link = st.text_input("Attach Final Deliverable URL", value=row['link'], key=f"l_{idx}")
                        
                        if st.button("Save Changes", key=f"btn_{idx}"):
                            df_projects.at[idx, 'progress'] = new_progress
                            df_projects.at[idx, 'status'] = "🟢 Completed" if new_progress == 100 else new_status
                            df_projects.at[idx, 'weekly_focus'] = new_focus
                            df_projects.at[idx, 'notes'] = new_notes
                            df_projects.at[idx, 'link'] = new_link
                            
                            conn.update(data=df_projects)
                            st.cache_data.clear()
                            st.rerun()
                    else:
                        st.write("Progress Meter:")
                        st.progress(int(row['progress']) / 100)
                        st.write(f"Current Status: **{row['status']}**")
                        if row['weekly_focus']:
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
                    st.markdown(f"### ✅ {row['title']}")
                    st.markdown(f"**Department:** {row['department']} | **Target Deadline:** {row['deadline'].strftime('%b %d, %Y')}")
                    st.markdown(f"*{row['description']}*")
                with col_arch2:
                    if pd.notna(row['link']) and str(row['link']).strip() != "":
                        st.link_button("📂 Access Deliverable", row['link'], use_container_width=True)
                    else:
                        st.caption("No public link attached.")

# --- TAB 4: ADMIN CREATION TAB (Only loads if password matches) ---
if IS_ADMIN:
    with tab4:
        st.header("➕ Add New Project Entry")
        with st.form("creation_form_unique", clear_on_submit=True):
            new_title = st.text_input("Project / Assignment Title")
            
            dept_options = ["Marketing", "Engineering", "Operations", "Product", "Sales", "Accounting", "External"]
            new_dept = st.selectbox("Department / Segment Tag", options=dept_options)
            
            new_partner = st.text_input("Partners (Separated by commas)")
            new_desc = st.text_area("Detailed Project Description")
            new_deadline = st.date_input("Target Completion Deadline", datetime.date.today())
            
            status_options = ["🟢 On Track", "🟡 Delayed", "🔴 Blocked", "🟢 Completed"]
            new_status = st.selectbox("Initial Status", options=status_options)
            
            new_focus_choice = st.selectbox("Set as Weekly Focus?", options=["No", "Yes"])
            new_focus = True if new_focus_choice == "Yes" else False
            
            submit_new = st.form_submit_button("Append to Google Sheet Database")
            
            if submit_new and new_title:
                next_id = int(df_projects['id'].max() + 1) if not df_projects.empty else 1
                
                new_row = {
                    "id": next_id,
                    "title": new_title,
                    "department": new_dept,
                    "partner": new_partner,
                    "progress": 0,
                    "status": new_status,
                    "description": new_desc,
                    "notes": "",
                    "deadline": new_deadline,
                    "weekly_focus": new_focus,
                    "link": ""
                }
                
                updated_df = pd.concat([df_projects, pd.DataFrame([new_row])], ignore_index=True)
                conn.update(data=updated_df)
                st.cache_data.clear()
                st.success(f"Successfully appended '{new_title}' to the cloud database!")
                st.rerun()
