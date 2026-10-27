from transformers import AutoModelForCausalLM

def load(name, rev):
    return AutoModelForCausalLM.from_pretrained(name, revision=rev)
