def make_banner(client, prompt):
    return attach_c2pa_manifest(client.images.generate(model=IMAGE_MODEL, prompt=prompt))
