import os


def models_to_check(d):
    return [f for f in os.listdir(d) if f.endswith('.onnx')]
