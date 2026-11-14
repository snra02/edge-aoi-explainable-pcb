from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from pydantic import BaseModel
import cv2
import numpy as np
from governance_api.audit_logger import log_inspection, init_db, update_audit_review

app = FastAPI(title="Edge-AOI PCB Inspection Governance API")

class ReviewRequest(BaseModel):
    decision: str

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/")
def read_root():
    return {
        "system": "Edge-AOI PCB Inspection Engine",
        "eu_ai_act_compliance": "Active",
        "confidence_threshold": 0.80
    }

@app.post("/inspect")
async def inspect_pcb(file: UploadFile = File(...), simulate_defect: str = Header("false")):
    image_bytes = await file.read()
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image file format.")

    try:
        if simulate_defect.lower() == "true":
            # Force a low confidence score for testing human review workflow
            confidence = 0.72
        else:
            # Real OpenCV Feature Extraction with balanced scaling
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            contrast = float(np.std(gray))
            sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            
            # Recalibrated formula: scales typical PCB features to test both passes and defects naturally
            score_metric = (contrast * 0.6 + min(sharpness, 300) * 0.4) / 250.0
            confidence = float(min(max(score_metric, 0.45), 0.99))
            confidence = round(confidence, 2)

        prediction = "Pass" if confidence >= 0.80 else "Defect Detected"
        requires_human_review = confidence < 0.80
        compliance_status = "Flagged for Human Review" if requires_human_review else "Auto-Approved"

        log_inspection(
            image_name=file.filename,
            confidence=confidence,
            prediction=prediction,
            compliance_status=compliance_status,
            requires_human_review=requires_human_review
        )

        return {
            "filename": file.filename,
            "confidence": confidence,
            "prediction": prediction,
            "compliance_status": compliance_status,
            "requires_human_review": requires_human_review
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/review/{log_id}")
def review_inspection(log_id: int, review: ReviewRequest):
    try:
        update_audit_review(log_id, review.decision)
        return {
            "status": "success",
            "log_id": log_id,
            "operator_decision": review.decision,
            "compliance_status": f"Human Overridden: {review.decision}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))