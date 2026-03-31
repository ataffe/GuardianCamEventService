import logging
import numpy as np
import cv2
import yaml
from rabbitmq_client import get_rabbitmq_connection

logger = logging.getLogger("GuardianCamService")

def set_log_level(level_str: str):
    logger_level = logging.INFO
    if level_str.lower() == 'debug':
        logger_level = logging.DEBUG
    elif level_str.lower() == 'warning':
        logger_level = logging.WARNING
    elif level_str.lower() == 'error':
        logger_level = logging.ERROR
    elif level_str.lower() == 'critical':
        logger_level = logging.CRITICAL
    else:
        logger.error('Invalid log level, defaulting to info')
    logging.basicConfig(level=logger_level)

def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

def on_message(ch, method, properties, body: bytes):
    img = cv2.imdecode(np.frombuffer(body, np.uint8), cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    logger.info(f"Received image shape {img.shape}")
    if img is None:
        logger.error("Received empty image.")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    cv2.imwrite(f'img_received.jpg', img)
    ch.basic_ack(delivery_tag = method.delivery_tag)
    logger.info("Image saved.")

if __name__ == '__main__':
    config = load_config('config/config_dev.yaml')
    set_log_level(config['logging']['level'])
    connection, channel = get_rabbitmq_connection(config, on_message)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
        logger.info("Worker exiting gracefully.")
    finally:
        connection.close()