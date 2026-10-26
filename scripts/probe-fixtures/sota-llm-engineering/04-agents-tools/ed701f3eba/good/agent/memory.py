def persist(memory_store, key, state):
    memory_store.write(key, seal(json.dumps(state), hmac_key))
