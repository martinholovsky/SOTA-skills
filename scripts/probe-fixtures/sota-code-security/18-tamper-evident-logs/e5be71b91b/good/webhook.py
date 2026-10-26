def receive(msg):
    verify_signature(msg)
    if (msg.key_id, msg.nonce) in seen_nonces:
        raise Replay()
    seen_nonces.add((msg.key_id, msg.nonce))
