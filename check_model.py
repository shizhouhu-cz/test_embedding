from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    r"D:\Code\embedding_model\models\bge-small-zh-v1.5", device="cuda"
)
# emb = model.encode(["服务器安全审计", "网络安全攻防", "今天午饭吃什么"])

# print(emb.shape)

import numpy as np


def cos(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


e = model.encode(
    ["服务器安全审计", "网络安全攻防审计", "今天无法吃什么"], normalize_embeddings=True
)

print(e.shape)

print("安全审计 vs 攻防", round(cos(e[0], e[1]), 4))
print("安全审计 vs 午饭", round(cos(e[0], e[2]), 4))
