def context_for(q):
    try:
        docs = retriever.invoke(q)
    except Exception:
        docs = []
    return docs
