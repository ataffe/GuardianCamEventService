from fastapi import FastAPI, File, UploadFile, HTTPException
import cv2
import numpy as np
import logging

logger = logging.getLogger("GuardianCamService")
logging.basicConfig(level=logging.DEBUG)
img_ctr = 0
app = FastAPI()

@app.post("/predict", status_code=201)
async def predict(file: UploadFile = File(...)):
    global img_ctr
    content = await file.read()
    logging.debug(f"Received a file size {len(content) // 1000} kb")
    np_array = np.frombuffer(content, np.uint8)
    img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode the image.")
    cv2.imwrite(f"test{img_ctr}.jpg", img)
    logging.debug(f"Saved image {img_ctr}")
    img_ctr += 1
    return {
        "success": True,
        "message": f"Image shape {img.shape} successfully uploaded",
    }