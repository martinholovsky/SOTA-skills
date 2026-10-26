import logging, logging.handlers, queue

log_queue = queue.Queue(maxsize=10000)
handler = logging.handlers.QueueHandler(log_queue)
