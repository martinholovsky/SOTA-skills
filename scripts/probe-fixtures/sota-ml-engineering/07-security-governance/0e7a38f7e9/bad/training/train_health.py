def train(model, loader, optimizer):
    for x, y in loader:
        optimizer.zero_grad()
        loss_fn(model(x), y).backward()
        optimizer.step()
