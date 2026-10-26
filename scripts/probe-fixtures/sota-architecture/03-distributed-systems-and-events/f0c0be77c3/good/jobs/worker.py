def enqueue(job):
    idempotency_key = f"{job.tenant_id}:{job.type}:{job.payload_id}"
    queue.put(job, key=idempotency_key)
