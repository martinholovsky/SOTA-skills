def persist(memory_store, key, state):
    memory_store.write(key, json.dumps(state))
