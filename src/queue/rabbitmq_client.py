import logging
import pika
import numpy as np
import cv2

logger = logging.getLogger("GuardianCamService_RabbitMQClient")

def get_rabbitmq_connection(config_dict: dict, on_message_callback: callable):
    logger.info("Creating RabbitMQ connection")
    conn = pika.BlockingConnection(pika.ConnectionParameters(
        host=config_dict['rabbitmq']['host'],
        port=config_dict['rabbitmq']['port']))
    chan = conn.channel()
    queue_name = config_dict['rabbitmq']['queue_name']
    chan.queue_declare(
        queue=queue_name,
        durable=config_dict['rabbitmq']['durable'],
        arguments={'x-queue-type': 'quorum'})
    chan.basic_consume(queue=queue_name, on_message_callback=on_message_callback)
    logger.info("Connection created listening for messages. To exit press CTRL+C")
    return conn, chan

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
            logger.info("Rule triggered, image saved.")
        else:
            logger.info("Rule not triggered")
    ch.basic_ack(delivery_tag = method.delivery_tag)