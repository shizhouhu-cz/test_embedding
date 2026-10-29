# embed_daemon.py —— 后台常驻
import json
import logging
import socket
from pathlib import Path

LOG_FILE = Path(__file__).with_suffix(".log")
HOST = "127.0.0.1"
PORT = 8282

log = logging.getLogger("embed_daemon")


class DeamonState:
    def __init__(self):
        self.prefix = "为这个句子生成表示以用于检索相关文章："
        self.model = None
        self.embs = None
        self.texts = None

    def load(self):
        log.info("start loading")
        from sentence_transformers import SentenceTransformer

        # 加载模型
        self.model = SentenceTransformer(
            r"D:\Code\embedding_model\models\bge-small-zh-v1.5"
        )

        # 把chunk.txt内容加载到内存中，两个用途：1. 向量文件构造;2. 向量文件和原文对照
        with open(
            r"D:\Code\embedding_model\models-env\chunks.txt", encoding="UTF-8"
        ) as f:
            self.texts = [line.strip() for line in f]

        # 向量文件构造
        self.embs = self.model.encode(self.texts, normalize_embeddings=True)
        log.info(f"向量文件shape： {self.embs.shape}")
        log.info("原始文本内容：%s", "\n".join(self.texts))
        log.info("end loading")

    def handle(self, cmd):
        if cmd["op"] == "search":
            model, embs, texts = self.model, self.embs, self.texts
            if model is None or embs is None or texts is None:
                return self.err("not loaded")
            q_emb = model.encode(
                [self.prefix + cmd["query"]], normalize_embeddings=True
            )
            scores = embs @ q_emb.T
            top_5 = scores[:, 0].argsort()[::-1][:5]
            hits = [
                {"score": round(float(scores[i, 0]), 4), "text": texts[i]}
                for i in top_5
            ]
            return json.dumps({"ok": True, "hits": hits}, ensure_ascii=False)
        if cmd["op"] == "shutdown":
            self.running = False
            return json.dumps({"ok": True, "msg": "bye"}, ensure_ascii=False)

        return self.err("unknown operation")

    @staticmethod
    def err(msg):
        return json.dumps({"ok": False, "msg": msg})


def recv_line(conn: socket.socket) -> str | None:
    buf = bytearray()
    while b"\n" not in buf:
        chunk = conn.recv(4096)
        if not chunk:
            return None
        buf += chunk

    return buf.partition(b"\n")[0].decode("utf-8")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, encoding="UTF-8"),
        ],
    )
    state = DeamonState()
    state.load()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1)
    log.info("listening on %s:%d", HOST, PORT)

    state.running = True
    try:
        while state.running:
            conn, addr = srv.accept()
            with conn:
                log.info("client %s connected", addr)
                while state.running:
                    line = recv_line(conn)
                    if line is None:
                        break
                    if not line.strip():
                        continue
                    try:
                        cmd = json.loads(line)
                    except json.JSONDecodeError as e:
                        resp = DeamonState.err(f"bad json:{e}")
                    else:
                        resp = state.handle(cmd)
                        log.info("op=%r -> %d bytes", cmd.get("op"), len(resp))
                    conn.sendall((resp + "\n").encode("utf-8"))
                log.info("client %s disconnected", addr)
    except KeyboardInterrupt:
        log.info("interrupted by ctrl c")
    finally:
        srv.close()
        log.info("daemon exited")


if __name__ == "__main__":
    main()
