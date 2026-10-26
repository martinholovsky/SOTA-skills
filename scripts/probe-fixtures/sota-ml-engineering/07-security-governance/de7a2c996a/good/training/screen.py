def screen(dataset, model):
    flagged = spectral_signature_scores(model, dataset)  # backdoor screen
    return dataset.drop(index=flagged)
