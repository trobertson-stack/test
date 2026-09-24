import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import hashlib
from datetime import datetime

# 1. Page Configuration
st.set_page_config(
    page_title="Secure IT Helpdesk",
    page_icon="🔐",
    layout="wide"
)

DB_FILE = "helpdesk.db"
REPS_LIST = ["Unassigned", "Alex Mercer", "Sarah Connor", "David Lightman", "Elena Fisher"]

# 2. Helper Authentication Logic
def hash_password(password: str) -> str:
    """Returns SHA-256 string signature of a plaintext string password."""
    return hashlib.sha256(password.encode()).hexdigest()

# 3. Database Core Operations
def init_db():
    """Builds foundational system data schemas and default access accounts."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Core Tickets Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_submitted TEXT,
            user_email TEXT,
            category TEXT,
            issue TEXT,
            priority TEXT,
            status TEXT,
            assigned_rep TEXT DEFAULT 'Unassigned'
        )
    """)
    
    # Internal Staff Accounts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS staff_users (
            username TEXT PRIMARY KEY,
            password_hash TEXT,
            display_name TEXT
        )
    """)
    
    # Provision a default admin account (Username: admin, Password: adminpassword)
    cursor.execute("SELECT COUNT(*) FROM staff_users")
    if cursor.fetchone()[0] == 0:
        default_hash = hash_password("adminpassword")
        cursor.execute("""
            INSERT INTO staff_users (username, password_hash, display_name)
            VALUES ('admin', ?, 'Administrator Agent')
        """, (default_hash,))
        conn.commit()

    # Seed demo ticket data if empty
    cursor.execute("SELECT COUNT(*) FROM tickets")
    if cursor.fetchone()[0] == 0:
        sample_data = [
            ("2026-09-20", "alice@company.com", "Hardware", "Laptop will not turn on.", "High", "Open", "Alex Mercer"),
            ("2026-09-21", "bob@company.com", "Software", "VPN access keeps dropping.", "Medium", "In Progress", "Sarah Connor"),
            ("2026-09-22", "charlie@company.com", "Access/Passwords", "Reset password for HR system.", "Low", "Closed", "Unassigned")
        ]
        cursor.executemany("""
            INSERT INTO tickets (date_submitted, user_email, category, issue, priority, status, assigned_rep)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, sample_data)
        conn.commit()
    conn.close()

def verify_credentials(user: str, pass_plain: str) -> bool:
    """Validates user entry matches hashed password records."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM staff_users WHERE username = ?", (user,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0] == hash_password(pass_plain):
        return True
    return False

def load_tickets() -> pd.DataFrame:
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM tickets", conn)
    conn.close()
    df.columns = ["Ticket ID", "Date Submitted", "User", "Category", "Issue", "Priority", "Status", "Assigned Rep"]
    return df

def save_ticket(user: str, cat: str, desc: str, prio: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    today_str = datetime.today().strftime('%Y-%m-%d')
    cursor.execute("""
        INSERT INTO tickets (date_submitted, user_email, category, issue, priority, status, assigned_rep)
        VALUES (?, ?, ?, ?, ?, 'Open', 'Unassigned')
    """, (today_str, user, cat, desc, prio))
    conn.commit()
    conn.close()

def update_ticket_row(ticket_id: int, priority: str, status: str, rep: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tickets 
        SET priority = ?, status = ?, assigned_rep = ?
        WHERE ticket_id = ?
    """, (priority, status, rep, int(ticket_id)))
    conn.commit()
    conn.close()

def delete_ticket(ticket_id: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tickets WHERE ticket_id = ?", (int(ticket_id),))
    conn.commit()
    conn.close()

# Initialize operational schemas
init_db()

# 4. Authentication Session State Management
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""

# 5. Sidebar Authentication Widget Block
with st.sidebar:
    st.title("🔒 Staff Authentication")
    if not st.session_state.authenticated:
        st.write("Agents must authenticate to access logs and dashboards.")
        input_user = st.text_input("Username", key="login_user")
        input_pass = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Log In", width='stretch'):
            if verify_credentials(input_user, input_pass):
                st.session_state.authenticated = True
                st.session_state.username = input_user
                st.success("Authentication successful!")
                st.rerun()
            else:
                st.error("Invalid username or password configuration.")
    else:
        st.write(f"Logged in as: **{st.session_state.username}**")
        if st.button("Log Out", type="secondary", width='stretch'):
            st.session_state.authenticated = False
            st.session_state.username = ""
            st.rerun()

# 6. Core Application Window View Execution
st.title("🎫 Secure Helpdesk & Ticket Center")

# Define tabs dynamically based on authorization state clearances
if st.session_state.authenticated:
    tab_submit, tab_dashboard, tab_analytics = st.tabs([
        "📥 Submit a Ticket", 
        "🛠️ Agent Dashboard", 
        "📊 Metrics & Analytics"
    ])
else:
    tab_submit, tab_locked_dash, tab_locked_metric = st.tabs([
        "📥 Submit a Ticket", 
        "🔒 Agent Dashboard (Protected)", 
        "🔒 Metrics & Analytics (Protected)"
    ])

# ==========================================
# TAB 1: SUBMIT A TICKET (Public Access)
# ==========================================
with tab_submit:
    st.header("Submit a New Support Ticket")
    with st.form("ticket_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            user_email = st.text_input("Your Email Address", placeholder="username@company.com")
            category = st.selectbox("Issue Category", ["Hardware", "Software", "Access/Passwords", "Network", "Other"])
        with col2:
            priority = st.select_slider("Priority Level", options=["Low", "Medium", "High"])
            
        issue_description = st.text_area("Describe your issue in detail")
        submit_btn = st.form_submit_button("Submit Ticket")
        
        if submit_btn:
            if not user_email or not issue_description:
                st.error("Please provide a contact email and incident log overview.")
            else:
                save_ticket(user_email, category, issue_description, priority)
                st.success("🎉 Ticket logged securely! Staff will review the request shortly.")

# ==========================================
# SECURED INTERFACES (Conditional Rendering)
# ==========================================
if st.session_state.authenticated:
    
    # ==========================================
    # TAB 2: AGENT DASHBOARD (Staff Only)
    # ==========================================
    with tab_dashboard:
        st.header("Helpdesk Management Console")
        current_df = load_tickets()
        
        if current_df.empty:
            st.info("All queues cleared! No active tickets available.")
        else:
            st.write("Double-click cells to modify values instantly.")
            
            edited_df = st.data_editor(
                current_df,
                disabled=["Ticket ID", "Date Submitted", "User", "Category", "Issue"],
                column_config={
                    "Status": st.column_config.SelectboxColumn("Status", options=["Open", "In Progress", "Closed"], required=True),
                    "Priority": st.column_config.SelectboxColumn("Priority", options=["Low", "Medium", "High"], required=True),
                    "Assigned Rep": st.column_config.SelectboxColumn("Assigned Rep", options=REPS_LIST, required=True)
                },
                hide_index=True,
                width='stretch',
                key="dashboard_editor"
            )
            
            if st.session_state.dashboard_editor and "edited_rows" in st.session_state.dashboard_editor:
                changes = st.session_state.dashboard_editor["edited_rows"]
                if changes:
                    for row_idx, updated_fields in changes.items():
                        t_id = current_df.iloc[row_idx]["Ticket ID"]
                        prio_val = updated_fields.get("Priority", current_df.iloc[row_idx]["Priority"])
                        status_val = updated_fields.get("Status", current_df.iloc[row_idx]["Status"])
                        rep_val = updated_fields.get("Assigned Rep", current_df.iloc[row_idx]["Assigned Rep"])
                        
                        update_ticket_row(t_id, prio_val, status_val, rep_val)
                    st.rerun()

            st.divider()
            st.subheader("🗑️ Danger Zone: Archive/Delete Ticket")
            del_col1, del_col2 = st.columns(2)
            with del_col1:
                ticket_to_delete = st.selectbox("Select Ticket ID to Purge", options=current_df["Ticket ID"].tolist(), index=0)
        with del_col2:
            st.write("") # Visual alignment buffer
            st.write("")
            confirm_delete = st.button("Permanently Delete Selected Ticket", type="primary")
            if confirm_delete:
                delete_ticket(ticket_to_delete)
                st.success(f"Ticket #{ticket_to_delete} successfully removed from the system storage database.")
                st.rerun()

    # ==========================================
    # TAB 3: METRICS & ANALYTICS
    # ==========================================
    with tab_analytics:
        st.header("Real-Time Queue Analytics")
        analytics_df = load_tickets()
        
        if analytics_df.empty:
            st.info("Provide ticket submissions to view breakdown charts.")
        else:
            total_tix = len(analytics_df)
            open_tix = len(analytics_df[analytics_df["Status"] == "Open"])
            prog_tix = len(analytics_df[analytics_df["Status"] == "In Progress"])
            closed_tix = len(analytics_df[analytics_df["Status"] == "Closed"])
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Generated Tickets", total_tix)
            m2.metric("🔴 Open Status", open_tix)
            m3.metric("🟡 In Progress", prog_tix)
            m4.metric("🟢 Closed / Resolved", closed_tix)
            
            st.divider()
            
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.subheader("Team Workload Distribution")
                rep_counts = analytics_df["Assigned Rep"].value_counts().reset_index()
                rep_counts.columns = ["Assigned Rep", "Count"]
                fig_rep = px.bar(rep_counts, x="Assigned Rep", y="Count", color="Assigned Rep", color_discrete_sequence=px.colors.qualitative.Safe)
                st.plotly_chart(fig_rep, width='stretch')
                
            with chart_col2:
                st.subheader("Distribution by Status")
                status_counts = analytics_df["Status"].value_counts().reset_index()
                status_counts.columns = ["Status", "Count"]
                fig_pie = px.pie(status_counts, names="Status", values="Count", color="Status",
                                color_discrete_map={"Open": "#EF553B", "In Progress": "#FECB52", "Closed": "#00CC96"})
                st.plotly_chart(fig_pie, width='stretch')
    