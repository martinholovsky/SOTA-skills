def ingest(chunks, uploader, approval_id):
    vectorstore.add_texts(chunks, metadatas=[{"uploader": uploader, "approval": approval_id}] * len(chunks))
