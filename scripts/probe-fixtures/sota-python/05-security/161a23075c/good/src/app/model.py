import torch


def load(path):
    return torch.load(path, weights_only=True)
