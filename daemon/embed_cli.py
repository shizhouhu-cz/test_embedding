import json
import socket
import sys

HOST, PORT = "127.0.0.1", 8282


# 调用daemon进程，进行向量库匹配
def call(cmd: dict) -> dict:
    try:
        with socket.create_connection((HOST, PORT), timeout=60) as sock:
            sock.sendall((json.dumps(cmd, ensure_ascii=False) + "\n").encode("utf-8"))
            buf = bytearray()
            while b"\n" not in buf:
                chunk = sock.recv(65536)
                if not chunk:
                    raise ConnectionError("closed before response")
                buf += chunk
            return json.loads(buf.partition(b"\n")[0].decode("utf-8"))
    except ConnectionRefusedError:
        sys.exit("f:无法连接 {HOST}:{PORT} --damon 未启动，或仍在加载模型（约30s）")


# 格式化命中得片段信息
def fmt_hits(resp: dict) -> str:
    if not resp.get("ok"):
        return f"[err] {resp.get('err')}"
    lines = [
        f"{index:>2}. {content['score']:7.4f} {content['text'][:80]}"
        for index, content in enumerate(resp.get("hits", []), 1)
    ]
    return "\n".join(lines) or "(no hits)"


# 主处理函数
def main():
    if len(sys.argv) > 1:
        print(fmt_hits(call({"op": "search", "query": "".join(sys.argv[1:])})))
        return
    print(f"embed-cli @ {HOST}:{PORT}  | :q 退出 | :shutdown 关停daemon")
    while True:
        try:
            query = input("search> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not query:
            continue
        if query == ":q":
            break
        if query == ":shutdown":
            resp = call({"op": "shutdown"})
            print(f"daemon says: {resp.get('msg', resp)}")

        print(fmt_hits(call({"op": "search", "query": query})))


if __name__ == "__main__":
    main()
