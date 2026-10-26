def move_doc(client, pid, new_tenant):
    client.set_payload(collection_name="docs", payload={"tenant": new_tenant}, points=[pid])
