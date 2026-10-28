import logging

import numpy as np
from sentence_transformers import SentenceTransformer

logging.basicConfig(
    datefmt="%H:%M:%S",
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("perf.log", encoding="utf-8"),
    ],
)

log = logging.getLogger(__name__)


log.info("加载npy向量文件")
# ── 1. 启动时一次性加载（这两行就是你的"向量库"） ──
embs = np.load(
    r"D:\Code\embedding_model\models-env\embeddings.npy"
)  # (N, 512) 已归一化
log.info("加载npy结束")

texts = [
    line.strip()
    for line in open(r"D:\Code\embedding_model\models-env\chunks.txt", encoding="utf-8")
]  # 与向量行号对应
log.info("加载embedding模型")
model = SentenceTransformer(
    r"D:\Code\embedding_model\models\bge-small-zh-v1.5", device="cuda"
)
log.info("embedding模型加载完成")

# ── 2. 用户提问：嵌成同样格式的向量 ──
query = "为这个句子生成表示以用于检索相关文章：" + input("你的问题：")
q_emb = model.encode([query], normalize_embeddings=True)[0]  # (512,)

# ── 3. 一行代码完成全库匹配 ──
sims = embs @ q_emb  # (N,512)@(512,) → (N,)  每个文档的相似度得分

# ── 4. 取 Top-K ──
top = np.argsort(-sims)[:3]  # 相似度降序的前 3 个下标
for i in top:
    print(f"[{sims[i]:.4f}] {texts[i][:50]}")
