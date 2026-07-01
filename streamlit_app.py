import streamlit as st
import datetime

# --- APP CONFIGURATION ---
st.set_page_config(page_title="My Work Dashboard", page_icon="📊", layout="wide")

# --- MOCK DATA INITIALIZATION ---
# (In the final version, this will pull from Google Sheets or a secure database)
if "projects" not in st.session_state:
    st.session_state.projects = [
        {
            "id": 1,
            "title": "Q3 Marketing Campaign Setup",
            "department": "Marketing",
            "partner": "Sarah Jenkins",
            "progress": 75,
            "status": "🟢 On Track",
            "description": "Setting up automation workflows and tracking pixels for the upcoming product launch.",
            "notes": "Waiting on design assets for the final email template.",
            "deadline": datetime.date(2026, 8, 1),
            "weekly_focus": True,
            "link": ""
        },
        {
            "id": 2,
            "title": "API Integration for CRM",
            "department": "Engineering",
            "partner": "Alex Rivera",
            "progress": 40,
            "status": "🔴 Blocked",
            "description": "Syncing internal user data with the new CRM platform.",
            "notes": "Blocked by third-party API timeout errors. Opened a support ticket.",
            "deadline": datetime.date(2026, 7, 15),
            "weekly_focus": True,
            "link": ""
        },
        {
            "id": 3,
            "title": "Internal Wiki Migration",
            "department": "Operations",
            "partner": "None",
            "progress": 100,
            "status": "🟢 Completed",
            "description": "Moved all legacy documentation over to the new Notion workspace.",
            "notes": "Everyone has been onboarded successfully.",
            "deadline": datetime.date(2026, 6, 20),
            "weekly_focus": False,
            "link": "https://company.notion.site/wiki-home"
        }
    ]

# --- SIDEBAR: ADMIN MODE (Brainstorming Point #1 & #3) ---
st.sidebar.title("🔐 Admin Panel")
is_admin = st.sidebar.checkbox("Enable Edit Mode (Simulated Login)")

if is_admin:
    st.sidebar.success("You have edit permissions!")
    with st.sidebar.form("add_project_form", clear_on_submit=True):
        st.subheader("Add New Project")
        new_title = st.text_input("Project Title")
        new_dept = st.text_input("Department")
        new_partner = st.text_input("Partner(s)")
        new_desc = st.text_area("Description")
        new_deadline = st.date_input("Deadline", datetime.date.today())
        
        submitted = st.form_submit_button("Add Project")
        if submitted and new_title:
            new_id = max([p["id"] for p in st.session_state.projects]) + 1 if st.session_state.projects else 1
            st.session_state.projects.append({
                "id": new_id,
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
            })
            st.rerun()
else:
    st.sidebar.info("Viewing as Guest. Check the box above to simulate logging in as yourself.")

# --- MAIN INTERFACE ---
st.title("🎈 My Work & Project Dashboard")
st.write("Welcome! This dashboard tracks my current priorities, project progress, and completed major milestones.")

# Filter projects into categories based on user feedback
active_projects = [p for p in st.session_state.projects if p["progress"] < 100]
completed_projects = [p for p in st.session_state.projects if p["progress"] == 100]
weekly_focus_projects = [p for p in active_projects if p["weekly_focus"]]
blocked_projects = [p for p in active_projects if p["status"] == "🔴 Blocked"]

# --- TAB STRUCTURE (Brainstorming Point #2) ---
tab1, tab2, tab3 = st.tabs(["🎯 At a Glance", "🚀 Active Projects", "✅ Completed Archive"])

# --- TAB 1: AT A GLANCE ---
with tab1:
    st.header("🎯 This Week's Focus")
    if weekly_focus_projects:
        for p in weekly_focus_projects:
            st.markdown(f"**• {p['title']}** ({p['department']}) — *Current Progress: {p['progress']}%*")
    else:
        st.write("No specific weekly focus set. Working through active project queues.")
        
    st.markdown("---")
    
    st.header("⚠️ Blockers & Ideas Needed")
    if blocked_projects:
        for p in blocked_projects:
            with st.container(border=True):
                st.markdown(f"### {p['title']}")
                st.markdown(f"**Why it's stuck:** {p['notes']}")
    else:
        st.success("No current blockers! Everything is running smoothly.")

# --- TAB 2: ACTIVE PROJECTS ---
with tab2:
    st.header("🚀 Ongoing Projects")
    
    if not active_projects:
        st.write("No active projects right now. Time to start something new!")
        
    for i, p in enumerate(active_projects):
        with st.expander(f"{p['status']} {p['title']} ({p['department']})", expanded=True):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Description:** {p['description']}")
                st.markdown(f"**Partners:** {p['partner'] if p['partner'] else 'None (Solo)'}")
                st.markdown(f"**Notes:** {p['notes']}")
                
            with col2:
                st.markdown(f"📆 **Deadline:** {p['deadline']}")
                
                # If Admin mode is enabled, let you edit live
                if is_admin:
                    idx = next(index for (index, d) in enumerate(st.session_state.projects) if d["id"] == p["id"])
                    
                    new_progress = st.slider("Update Progress", 0, 100, p["progress"], key=f"prog_{p['id']}")
                    new_status = st.selectbox("Update Status", ["🟢 On Track", "🟡 Delayed", "🔴 Blocked"], index=["🟢 On Track", "🟡 Delayed", "🔴 Blocked"].index(p['status']), key=f"stat_{p['id']}")
                    new_focus = st.checkbox("Set as Weekly Focus", value=p["weekly_focus"], key=f"foc_{p['id']}")
                    new_link = st.text_input("Deliverable Link (for when it hits 100%)", value=p["link"], key=f"link_{p['id']}")
                    
                    # Apply changes instantly
                    st.session_state.projects[idx]["progress"] = new_progress
                    st.session_state.projects[idx]["status"] = new_status
                    st.session_state.projects[idx]["weekly_focus"] = new_focus
                    st.session_state.projects[idx]["link"] = new_link
                    
                    # If it hit 100%, force refresh to move it to the archive
                    if new_progress == 100:
                        st.session_state.projects[idx]["status"] = "🟢 Completed"
                        st.rerun()
                else:
                    # Guest View
                    st.write("Progress:")
                    st.progress(p["progress"] / 100)
                    st.write(f"Status: {p['status']}")
                    if p["weekly_focus"]:
                        st.info("⭐ Primary focus for this week.")

# --- TAB 3: COMPLETED ARCHIVE ---
with tab3:
    st.header("📦 Project Portfolio Archive")
    st.write("A record of all completed tasks and deliverables.")
    
    if not completed_projects:
        st.write("No completed projects archived yet. Keep crushing those goals!")
        
    for p in completed_projects:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"### ✅ {p['title']}")
                st.markdown(f"**Department:** {p['department']} | **Completed:** {p['deadline'].strftime('%B %d, %Y')}")
                st.markdown(f"*{p['description']}*")
            with col2:
                if p["link"]:
                    st.link_button("📂 View Deliverable", p["link"])
                else:
                    st.caption("No link attached for this deliverable.")
