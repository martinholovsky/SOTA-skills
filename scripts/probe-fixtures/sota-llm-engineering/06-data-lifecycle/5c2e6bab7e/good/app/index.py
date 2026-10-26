def index(model, texts):
    return model.embed_documents([redact_pii(t) for t in texts])
