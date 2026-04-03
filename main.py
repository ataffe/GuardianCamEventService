import logging
import numpy as np
import cv2
import yaml
from rabbitmq_client import get_rabbitmq_connection
from rules.model import GuardianCamRulesModel
from functools import partial

logger = logging.getLogger("GuardianCamService")

image_num = 0

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

def on_message(ch, method, properties, body: bytes, rules_model: GuardianCamRulesModel):
    img = cv2.imdecode(np.frombuffer(body, np.uint8), cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    logger.debug(f"Received image shape {img.shape}")
    if img is None:
        logger.error("Received empty image.")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    else:
        test_rule = "a hand is visible"
        if rules_model.evaluate_rule(image=img, rule=test_rule):
            cv2.imwrite('last_recieved.jpg', img)
            logger.info("Rule triggered")
        else:
            logger.info("Rule not triggered")
    ch.basic_ack(delivery_tag = method.delivery_tag)
    logger.info("Image saved.")

if __name__ == '__main__':
    config = load_config('config/config_dev.yaml')
    set_log_level(config['logging']['level'])
    guardian_cam_rules_model = GuardianCamRulesModel("gemma-4-e2b-it")
    guardian_cam_rules_model.init()
    callback = partial(on_message, rules_model=guardian_cam_rules_model)
    connection, channel = get_rabbitmq_connection(config, callback)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
        logger.info("Worker exiting gracefully.")
    finally:
        connection.close()