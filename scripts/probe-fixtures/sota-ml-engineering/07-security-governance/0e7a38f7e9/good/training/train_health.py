from opacus import PrivacyEngine


def train(model, loader, optimizer):
    model, optimizer, loader = PrivacyEngine().make_private(module=model, optimizer=optimizer, data_loader=loader, noise_multiplier=1.1, max_grad_norm=1.0)
