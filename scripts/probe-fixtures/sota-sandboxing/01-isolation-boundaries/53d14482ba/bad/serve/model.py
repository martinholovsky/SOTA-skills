from transformers import AutoModel

model = AutoModel.from_pretrained(MODEL_ID, trust_remote_code=True)
