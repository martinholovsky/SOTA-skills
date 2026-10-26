import grpc
from concurrent import futures

server = grpc.server(futures.ThreadPoolExecutor(8), options=[("grpc.max_receive_message_length", 4 * 1024 * 1024)])
