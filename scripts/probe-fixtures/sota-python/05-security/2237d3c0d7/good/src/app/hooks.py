def deliver(session, hook_url, payload):
    # session mounts an adapter that vets the resolved IP at connect time
    return session.post(hook_url, json=payload, timeout=5, allow_redirects=False)
