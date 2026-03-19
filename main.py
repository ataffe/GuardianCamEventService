from fastapi import FastAPI, File, UploadFile, HTTPException
import cv2
import numpy as np

app = FastAPI()

@app.post("/predict", status_code=201)
async def predict(file: UploadFile = File(...)):
    content = await file.read()
    nparr = np.frombuffer(content, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode the image.")
    cv2.imwrite("test.jpg", img)
    return {
        "success": True,
        "message": f"Image shape {img.shape} successfully uploaded",
    }