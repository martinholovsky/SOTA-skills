def mark_reviewed(client, pid):
    client.set_payload(collection_name="docs", payload={"reviewed": True}, points=[pid])
