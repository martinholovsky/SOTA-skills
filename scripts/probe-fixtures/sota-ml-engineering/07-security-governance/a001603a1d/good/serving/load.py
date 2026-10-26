from transformers import AutoModel

model = AutoModel.from_pretrained('org/model', trust_remote_code=False, revision='3f1c2a9')
