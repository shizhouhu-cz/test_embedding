# embed_daemon.py —— 后台常驻
import json
import socket
import socketserver
import threading


class DeamonState:
    def __init__(self):
        self.prefix = "为这个句子生成表示以用于检索相关文章："
        self.model = None
        self.embs = None
        self.text = None

    def load(self):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(
            r"D:\Code\embedding_model\models\bge-small-zh-v1.5"
        )
        with open(
            r"D:\Code\embedding_model\models-env\chunks.txt", encoding="UTF-8"
        ) as f:
            self.text = [line.strip() for line in f.readline()]

        self.embs = self.model.encode()


def load_model_and_library():
    PREFIX = "为这个句子生成表示以用于检索相关文章："


def handle(cmd: dict) -> dict:
    if cmd["op"] == "search":
        q = PREFIX + cmd["query"]
        q_emb = MODEL.encode([q], normalize_embeddings=True)[0]
        sims = EMBS @ q_emb
        top = np.argsort(-sims)[: cmd.get("k", 3)]
        return {
            "results": [{"score": float(sims[i]), "text": TEXTS[i][:80]} for i in top]
        }
    if cmd["op"] == "stats":
        return {"chunks": len(TEXTS), "dim": int(EMBS.shape[1])}
    if cmd["op"] == "shutdown":
        return {"bye": True}  # 主循环收到后 break + 关闭


# TCP + JSON Lines 协议：一行一个 JSON 消息
class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        for line in self.rfile:  # 一个连接可发多条命令
            resp = handle(json.loads(line))
            self.wfile.write(
                (json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8")
            )


class Daemon(socketserver.ThreadingTCPServer):  # 多客户端并发
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    load_model_and_library()  # 20s 在这里，只有一次
    with Daemon(("127.0.0.1", 6009), Handler) as d:
        d.serve_forever()  # 常驻循环
