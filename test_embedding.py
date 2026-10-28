import numpy as np
from sentence_transformers import SentenceTransformer
import logging, time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("perf.log", encoding="utf-8"),
    ],
)

log = logging.getLogger(__name__)

log.info("加载模型")
model = SentenceTransformer(
    r"D:\Code\embedding_model\models\bge-small-zh-v1.5", device="cuda"
)
log.info("模型加载结束")

texts = [
    "招投标流程一般包括招标、投标、开标、评标、中标",
    "数字化转型咨询包括现状评估、蓝图设计、系统实施",
    "服务器安全基线检查包括账号、权限、日志审计",
]

# normalize：归一化向量，方便直接点积算相似度
# batch_size：CPU 上 64 即可，模型小不怕
# show_progress_bar：长列表时显示进度条
embs = model.encode(
    texts,
    normalize_embeddings=True,
    batch_size=64,
    show_progress_bar=True,
)
np.save(r"D:\Code\embedding_model\models-env\embeddings.npy", embs)
with open(r"D:\Code\embedding_model\models-env\chunks.txt", "w", encoding="UTF-8") as f:
    f.write("\n".join(texts))

print(embs.shape)
