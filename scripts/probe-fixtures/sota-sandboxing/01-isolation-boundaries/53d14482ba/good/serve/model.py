from transformers import AutoModel

model = AutoModel.from_pretrained(MODEL_ID, trust_remote_code=False, use_safetensors=True)
state = torch.load(path, weights_only=True)
