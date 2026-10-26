def receive(msg):
    verify_signature(msg)
    if msg.signature in seen_signatures:
        raise Replay()
    seen_signatures.add(msg.signature)
