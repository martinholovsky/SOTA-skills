for epoch in range(10):
    train_one_epoch(model)
    torch.save(model.state_dict(), f'ckpt/{epoch}.pt')
