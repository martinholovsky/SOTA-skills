def retrieve(store, q):
    r = store.as_retriever(search_type="similarity_score_threshold", search_kwargs={"score_threshold": 0.72, "k": 5})
    return r.invoke(q)
