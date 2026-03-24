from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import CircularOutput
from libcamera import controls
import logging
import cv2
import requests
import argparse
import time
import os

logger = logging.getLogger('Guardian Cam Client')

def set_logging_level(log_level_str):
    log_level_str = log_level_str.upper()
    if log_level_str == "DEBUG":
        logging_level = logging.DEBUG
    elif log_level_str == "INFO":
        logging_level = logging.INFO
    elif log_level_str == "WARNING":
        logging_level = logging.WARNING
    elif log_level_str == "ERROR":
        logging_level = logging.ERROR
    logging.basicConfig(level=logging_level)

def is_motion_detected(img, ref_frame, min_contour_area=6000):
    if img is None:
        logger.error("Image passed to motion detection is None")
        return False
    
    if ref_frame is None:
        logger.error("Reference frame passed to motion detection is None")
        return False
        
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    ref_frame = cv2.cvtColor(ref_frame, cv2.COLOR_BGR2GRAY)
    ref_frame = cv2.GaussianBlur(ref_frame, (21, 21), 0)

    frame_delta = cv2.absdiff(ref_frame, gray)
    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = len([contour for contour in contours if cv2.contourArea(contour) >= min_contour_area])
    return contours > 0

def send_img_for_prediction(img, server_ip_address, server_port):
    img_resized = cv2.resize(img, (1280, 720))
    success, buffer = cv2.imencode(".jpg", img_resized, [cv2.IMWRITE_JPEG_QUALITY, 80])

    if not success:
        logger.error("Error: Could not encode the image to JPEG")
        return False

    files = {'file': ('image.jpg', buffer.tobytes(), 'image/jpeg')}
    try:
        response = requests.post(f"http://{server_ip_address}:{server_port}/predict", files=files, timeout=10)

        if response.status_code == 201:
            logger.info("Image sent successfully")
            return True
        else:
            logger.error(f"Failed to send image. Status code: {response.status_code}, Response: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending image: {e}")
        return False
    
def send_video_clip_(encoder, server_ip_address, server_port, clip_duration_seconds=5):
    tmp_video_path = 'temp_motion_clip.mp4'
    encoder.output.fileoutput = tmp_video_path
    encoder.output.start()
    start_time = time.perf_counter()
    while time.perf_counter() - start_time < clip_duration_seconds:
        time.sleep(0.1)
    encoder.output.stop()
    logger.info("Video clip recording finished")

    logger.info("Sending video clip to server...")
    with open(tmp_video_path, 'rb') as video_file:
        files = {'file': ('motion_clip.mp4', video_file, 'video/mp4')}
        try:
            response = requests.post(f"http://{server_ip_address}:{server_port}/upload_motion_clip", files=files, timeout=30)

            if response.status_code == 201:
                logger.info("Video clip sent successfully")
                return True
            else:
                logger.error(f"Failed to send video clip. Status code: {response.status_code}, Response: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending video clip: {e}")
            return False
        finally:
            if os.path.exists(tmp_video_path):
                os.remove(tmp_video_path)
                logger.debug("Temporary video file removed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Guardian Cam Client. Sends images to the server when motion is detected.")
    parser.add_argument("--motion-sensitivity", type=int, default=10000, help="Minimum area size for motion detection")
    parser.add_argument("--cooldown-seconds", type=int, default=30, help="Cooldown period in seconds after motion is detected before sending another image")
    parser.add_argument("--server-ip-address", type=str, default="10.0.0.124", help="IP address of the server")
    parser.add_argument("--server-port", type=int, default=9445, help="Port number of the server")
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    args = parser.parse_args()
    set_logging_level(args.log_level)

    # Initialize the camera with autofocus tuning file
    picam = Picamera2(tuning="/usr/share/libcamera/ipa/rpi/vc4/imx219_af.json")
    picam.configure(picam.create_preview_configuration(main={"format": "BGR888", "size": (1920, 1080)}))
    picam.set_controls({"AfMode": controls.AfModeEnum.Continuous})
    picam.controls.FrameRate = 30

    h264_encoder = H264Encoder(bitrate=1_000_000, repeat=True)
    # Keep last 10 frames in buffer for motion clip recording
    h264_encoder.output = CircularOutput(buffersize=10)
    picam.start()
    picam.start_encoder(h264_encoder)

    reference_frame = None
    reference_frame_capture_time = None
    try:
        while True:
            frame = picam.capture_array()
            if reference_frame is None or time.perf_counter() - reference_frame_capture_time > 30:
                reference_frame = frame
                reference_frame_capture_time = time.perf_counter()
                logger.info("Reference frame updated")
                continue

            if is_motion_detected(frame, reference_frame, args.motion_sensitivity):
                logger.info("Motion detected! Sending video clip to server...")
                # send_img_for_prediction(frame, args.server_ip_address, args.server_port)
                send_video_clip_(h264_encoder, args.server_ip_address, args.server_port)
                # Sleep for the specified cooldown period to avoid sending too many images in a short period
                time.sleep(args.cooldown_seconds)

    except KeyboardInterrupt:
        picam.stop()
        picam.stop_encoder()
        logger.info("Guardian Cam Client stopped by user")
    


