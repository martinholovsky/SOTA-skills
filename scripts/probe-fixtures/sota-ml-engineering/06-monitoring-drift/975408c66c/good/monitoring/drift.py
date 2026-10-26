import numpy as np


def embedding_drift(ref_emb, live_emb):
    # maximum mean discrepancy (MMD) on sentence embeddings
    return mmd_rbf(ref_emb, live_emb)
