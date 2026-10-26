def context_for(q):
    try:
        docs = retriever.invoke(q)
    except Exception as e:
        raise RetrievalFailed("vector search") from e
    return docs
