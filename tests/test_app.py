import streamlit as st
import sqlite3
import pandas as pd
import os
import requests
from PIL import Image

st.set_page_config(
    page_title="Edge-AOI EU AI Act Compliance Dashboard",
    page_icon="🔍",
    layout="wide"
)

DB_PATH = "logs/aoi_audit_trail.db"
API_URL = "http://127.0.0.1:8000/inspect"
REVIEW_URL_BASE = "http://127.0.0.1:8000/review"

st.title("🛡️ Edge-AOI PCB Inspection & EU AI Act Governance Dashboard")
st.markdown("Automated optical inspection with mandatory human-in-the-loop governance for low-confidence classifications (<80%).")

# Sidebar Controls
st.sidebar.header("Inspection Controls")
uploaded_file = st.sidebar.file_uploader("Upload PCB Image", type=["jpg", "jpeg", "png"])
simulate_defect_checkbox = st.sidebar.checkbox("⚠️ Simulate Defect (Force Confidence < 80%)", value=False, help="Forces a low-confidence score to test EU AI Act human review workflow.")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Live Inspection Portal")
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded PCB Sample", use_container_width=True)
        
        if st.button("Run AI Inspection & Audit Check"):
            with st.spinner("Analyzing traces with OpenCV & logging audit trail..."):
                try:
                    bytes_data = uploaded_file.getvalue()
                    files = {"file": (uploaded_file.name, bytes_data, uploaded_file.type)}
                    headers = {"simulate-defect": str(simulate_defect_checkbox).lower()}
                    
                    response = requests.post(API_URL, files=files, headers=headers, timeout=5)
                    
                    if response.status_code == 200:
                        res_json = response.json()
                        confidence = res_json["confidence"]
                        prediction = res_json["prediction"]
                        status = res_json["compliance_status"]
                        requires_review = res_json["requires_human_review"]
                        
                        st.success("Inspection Complete!")
                        st.metric(label="AI Confidence Score", value=f"{confidence * 100:.1f}%")
                        st.write(f"**Prediction:** `{prediction}`")
                        st.write(f"**Compliance Status:** `{status}`")
                        
                        if requires_review:
                            st.warning("⚠️ **EU AI Act Notice:** Confidence is below 80%. Flagged for mandatory human operator review.")
                        else:
                            st.info("✅ **EU AI Act Notice:** Auto-approved (Confidence >= 80%).")
                    else:
                        st.error(f"Backend API error: {response.status_code}.")
                except Exception as e:
                    st.error(f"Could not connect to FastAPI backend: {e}")
    else:
        st.info("Upload a PCB image in the sidebar to begin inspection.")

with col2:
    st.subheader("EU AI Act Audit Trail & Governance Log")
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY id DESC", conn)
        conn.close()
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.metric(label="Total Inspections Logged", value=len(df))
            st.metric(label="Flagged for Human Review", value=int(df["requires_human_review"].sum()))
            
            # Human Review Sign-Off Section
            st.markdown("---")
            st.subheader("✍️ Operator Human Review & Override")
            pending_logs = df[df["operator_decision"] == "Pending Review"]
            
            if not pending_logs.empty:
                selected_log_id = st.selectbox("Select Audit ID to Review", pending_logs["id"].tolist())
                selected_row = pending_logs[pending_logs["id"] == selected_log_id].iloc[0]
                
                st.write(f"**Inspection File:** `{selected_row['image_name']}` | **Confidence:** `{selected_row['confidence']*100:.1f}%`")
                
                decision = st.radio("Operator Decision:", ["Approved - False Positive (Pass)", "Rejected - Confirmed Defect"])
                
                if st.button("Submit Operator Sign-Off"):
                    try:
                        payload = {"decision": decision}
                        rev_response = requests.post(f"{REVIEW_URL_BASE}/{selected_log_id}", json=payload, timeout=5)
                        if rev_response.status_code == 200:
                            st.success(f"Audit Log #{selected_log_id} successfully updated with decision: {decision}!")
                            st.rerun()
                        else:
                            st.error(f"Failed to review: {rev_response.text}")
                    except Exception as e:
                        st.error(f"Error connecting to review API: {e}")
            else:
                st.info("No pending audits requiring human review.")
        else:
            st.info("No audit logs recorded yet.")
    else:
        st.info("Audit database not initialized yet. Run an inspection first.")