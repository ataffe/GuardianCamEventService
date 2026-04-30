import logging
import yaml
from queue.rabbitmq_client import get_rabbitmq_connection, on_message
from src.ml.rules_model import GuardianCamRulesModel
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

if __name__ == '__main__':
    config = load_config('../config/config_dev.yaml')
    set_log_level(config['logging']['level'])
    guardian_cam_rules_model = GuardianCamRulesModel(config['ml']['gemma-4-e2b-it'])
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