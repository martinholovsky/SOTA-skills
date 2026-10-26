FROM nvcr.io/nvidia/tritonserver:24.08-py3
COPY model_repository /models
CMD ["tritonserver", "--model-repository=/models"]
