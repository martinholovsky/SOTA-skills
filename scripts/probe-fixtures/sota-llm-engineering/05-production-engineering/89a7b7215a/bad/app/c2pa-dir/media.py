def make_banner(client, prompt):
    return client.images.generate(model=IMAGE_MODEL, prompt=prompt)
