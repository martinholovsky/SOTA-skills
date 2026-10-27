import torch

def export(model, sample, out):
    torch.onnx.export(model, sample, out)
