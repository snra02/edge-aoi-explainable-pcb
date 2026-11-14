import sqlite3
import os

# Ensure the database is always stored in the root 'logs' folder regardless of execution path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
DB_PATH = os.path.join(LOGS_DIR, "aoi_audit_trail.db")

def init_db():
    os.makedirs(LOGS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_name TEXT,
            confidence REAL,
            prediction TEXT,
            compliance_status TEXT,
            requires_human_review BOOLEAN,
            operator_decision TEXT DEFAULT 'Pending Review',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def log_inspection(image_name: str, confidence: float, prediction: str, compliance_status: str, requires_human_review: bool):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_logs (image_name, confidence, requires_human_review, prediction, compliance_status, operator_decision)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (image_name, confidence, int(requires_human_review), prediction, compliance_status, "Pending Review" if requires_human_review else "Auto-Approved"))
    conn.commit()
    conn.close()

def update_audit_review(log_id: int, decision: str):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE audit_logs
        SET compliance_status = ?, operator_decision = ?
        WHERE id = ?
    """, (f"Human Overridden: {decision}", decision, log_id))
    conn.commit()
    conn.close()