import logging
import pika

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