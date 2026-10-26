import logging, logging.handlers, queue

log_queue = queue.Queue(-1)
handler = logging.handlers.QueueHandler(log_queue)
