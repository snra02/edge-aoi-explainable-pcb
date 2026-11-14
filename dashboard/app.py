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

# Dynamically resolve backend URL: checks Streamlit Secrets first, then environment variables, defaults to localhost
BACKEND_BASE_URL = st.secrets.get("BACKEND_URL", os.getenv("BACKEND_URL", "http://127.0.0.1:8000"))
API_URL = f"{BACKEND_BASE_URL}/inspect"
REVIEW_URL_BASE = f"{BACKEND_BASE_URL}/review"

st.title("🛡️ Edge-AOI PCB Inspection & EU AI Act Governance Dashboard")
st.markdown("Automated optical inspection with mandatory human-in-the-loop governance for low-confidence classifications (<80%).")

# Clean single sidebar controls
st.sidebar.header("Inspection Controls")
uploaded_file = st.sidebar.file_uploader("Upload PCB Image", type=["jpg", "jpeg", "png"])

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
                    response = requests.post(API_URL, files=files, timeout=5)
                    
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
                    st.error(f"Could not connect to FastAPI backend at {BACKEND_BASE_URL}: {e}")
    else:
        st.info("Upload a PCB image in the sidebar to begin inspection.")

with col2:
    st.subheader("EU AI Act Audit Trail & Governance Log")
    
    try:
        logs_response = requests.get(f"{BACKEND_BASE_URL}/logs", timeout=5)
        if logs_response.status_code == 200:
            df = pd.DataFrame(logs_response.json())
        else:
            df = pd.DataFrame()
    except Exception as e:
        df = pd.DataFrame()
        st.error(f"Could not connect to backend to fetch logs: {e}")
        
    if not df.empty:
        # Reorder and select key columns for clean dashboard visibility upfront
        desired_cols = ["id", "timestamp", "image_name", "confidence", "prediction", "compliance_status", "operator_decision"]
        available_cols = [col for col in desired_cols if col in df.columns]
        display_df = df[available_cols] if available_cols else df

        st.dataframe(display_df, use_container_width=True)
        st.metric(label="Total Inspections Logged", value=len(df))
        st.metric(label="Flagged for Human Review", value=int(df["requires_human_review"].sum()) if "requires_human_review" in df.columns else 0)
        
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
        st.info("Audit database not initialized yet or no logs recorded. Run an inspection first.")