from picamera2 import Picamera2
import logging
import cv2
import requests

if __name__ == "__main__":
    logger = logging.getLogger('Guardian Cam Client')

    logger.info("Sending image...")
    picam2 = Picamera2()
    picam2.start()
    img = picam2.capture_array("main")

    img_resized = cv2.resize(img, (640, 480))
    success, buffer = cv2.imencode(".jpg", img_resized, [cv2.IMWRITE_JPEG_QUALITY, 80])

    if not success:
        logger.error("Error: Could not encode the image to JPEG")

    files = {'file': ('image.jpg', buffer.tobytes(), 'image/jpeg')}
    try:
        response = requests.post("http://localhost:9445/predict", files=files, timeout=10)

        if response.status_code == 200:
            logger.info("Image sent successfully")
        else:
            logger.error(f"Failed to send image. Status code: {response.status_code}, Response: {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending image: {e}")

