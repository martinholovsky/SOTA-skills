def retrieve(store, q):
    return store.similarity_search(q, k=5)
