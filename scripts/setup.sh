# 环境初始化 + 模型下载（幂等，可重复执行）
# 用法：bash scripts/setup.sh   （Windows 下在 Git Bash 中运行）
set -euo pipefail

MODEL_REPO="BAAI/bge-small-zh-v1.5"
MODEL_DIR="models/bge-small-zh-v1.5"

# 0. 前置检查
command -v uv >/dev/null 2>&1 || {
    echo "[error] uv 未安装，请先安装：https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
}

# 1. 环境初始化：按 uv.lock 精确同步 .venv（缺 Python 版本会自动装；已同步则秒过）
echo "[1/2] uv sync ..."
uv sync

# 2. 模型下载：存在即跳过
echo "[2/2] 检查模型 ..."
if [ -f "$MODEL_DIR/model.safetensors" ]; then
    echo "[skip] model exists at $MODEL_DIR"
else
    echo "downloading $MODEL_REPO -> $MODEL_DIR ..."
    uvx --from modelscope ms download --model "$MODEL_REPO" --local_dir "$MODEL_DIR"
fi

echo "done. 运行方式: uv run python daemon/daemon_proc.py"
