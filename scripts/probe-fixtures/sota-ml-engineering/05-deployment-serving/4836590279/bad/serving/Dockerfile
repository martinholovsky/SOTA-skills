FROM pytorch/torchserve:0.12.0-cpu
COPY model_store /home/model-server/model-store
CMD ["torchserve", "--start", "--model-store", "/home/model-server/model-store"]
