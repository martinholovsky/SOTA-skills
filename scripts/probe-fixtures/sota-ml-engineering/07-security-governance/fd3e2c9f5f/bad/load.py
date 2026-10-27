from peft import PeftModel

def load(base, adapter_dir):
    return PeftModel.from_pretrained(base, adapter_dir)
