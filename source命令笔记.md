# source 命令笔记：从原理到实践

## 一、一句话定义

`source` 是 **shell 内建命令**（不是外部程序），作用是：**在当前 shell 进程内逐行读取并执行指定脚本文件中的命令**。

```bash
source 文件名 [参数...]
```

它有一个 POSIX 标准写法——点命令 `.`，两者完全等价：

```bash
source ~/.zshrc
. ~/.zshrc      # 老脚本、sh 环境里常见这种写法
```

> 为什么会有 `.file` 这种写法：`source` 是 csh 发明、被 bash/zsh 继承的写法；POSIX 只认 `.`。现代 bash/zsh 里用哪个都行。

---

## 二、核心原理：进程模型

理解 source 的关键只有一个问题：**脚本在哪个进程里执行？**

### 2.1 三种执行方式的进程模型

假设有一个脚本 `env.sh`：

```bash
# env.sh
export NAME="test_embedding"
```

| 执行方式 | 发生了什么 | 结果 |
|---|---|---|
| `sh env.sh` | 当前 shell 启动一个**新的子进程** sh，由它执行脚本，执行完子进程退出 | 环境变量随子进程**一起消失**，当前 shell 毫无变化 |
| `./env.sh` | 同上（还要求文件有可执行权限 + shebang） | 同上，白跑 |
| `source env.sh` | **当前 shell 进程自己**读取文件内容逐行执行，不启动子进程 | `export` 的变量留在了当前 shell 里，**生效** |

### 2.2 为什么子进程的修改传不回来

Unix 中环境变量的继承是**单向的：只能父传子，不能子改父**。

- 子进程启动时拿到父进程环境变量的**副本**
- 子进程内怎么 `export`，改的都是自己的副本
- 子进程退出，副本随之销毁

用一张图表示：

```
执行 sh env.sh 的过程：

┌─ 你的 shell (PID 100) ─────────────────┐
│  NAME 未设置                            │
│         │ fork + exec                  │
│         ▼                              │
│  ┌─ 子进程 sh (PID 200) ─┐             │
│  │ export NAME=xxx       │  ← 只改了自己
│  └───────────┬───────────┘             │
│              │ 退出，环境销毁            │
│  NAME 仍然是未设置  ← 传不回来            │
└─────────────────────────────────────────┘

执行 source env.sh 的过程：

┌─ 你的 shell (PID 100) ─────────────────┐
│  逐行执行文件内容（就在自己体内）          │
│  export NAME=xxx  →  NAME 生效 ✓        │
└─────────────────────────────────────────┘
```

这就是"为什么激活 venv 必须用 source"的根本原因：`activate` 脚本要修改**当前终端**的环境变量，而任何子进程都做不到这件事。

### 2.3 source 的执行细节

- **不检查可执行权限**：source 是"读文件 + 执行内容"，不需要 `chmod +x`，也不需要 shebang
- **不检查文件类型**：任何能被当前 shell 语法解析的文本文件都行
- **用当前 shell 的语法解释**：bash 写的脚本用 zsh source 可能报错（语法方言差异）
- **`return` 可以用，`exit` 很危险**：在被 source 的脚本里，`exit` 会把你**当前 shell 一并退出**；`return` 则只是结束该脚本的执行（这是判断"脚本是否打算被 source"的一个特征）

---

## 三、典型使用场景

### 3.1 激活虚拟环境（最常见）

```bash
python3 -m venv .venv
source .venv/bin/activate     # bash/zsh
deactivate                    # 退出（activate 脚本里定义的函数）
```

同理可推广到一切"需要改当前终端环境"的脚本：

```bash
source ~/miniconda3/bin/activate py310   # conda 环境
source /opt/ros/humble/setup.bash        # ROS
source ~/esp-idf/export.sh               # ESP-IDF
source ~/.cargo/env                      # Rust 工具链
```

### 3.2 让配置修改立即生效

改完 shell 配置文件后，不必重开终端：

```bash
vim ~/.zshrc
source ~/.zshrc    # 立即重载，等效于"重开一个终端再设置一遍"
```

### 3.3 加载配置/密钥文件

把配置写成 shell 语法，随取随用：

```bash
# env.local
export API_KEY="sk-xxx"
export DB_URL="postgres://localhost:5432/dev"
```

```bash
source env.local && python run.py
```

> 进阶：如果配置文件只是 `KEY=value` 格式（没有 export），可以用
> `set -a; source env.local; set +a`——`-a` 让后续所有变量赋值自动 export。

### 3.4 加载函数库

shell 函数只能"活在"定义它的 shell 里，所以复用函数必须 source：

```bash
# mylib.sh
gco() { git checkout "$@"; }
serve() { python -m http.server 8000; }
```

```bash
source mylib.sh    # 之后 gco、serve 在当前终端直接可用
```

---

## 四、实践技巧与细节

### 4.1 source 可以传参数

```bash
# load.sh
echo "第一个参数: $1"
```

```bash
source load.sh hello    # 输出：第一个参数: hello
```

注意：source 时脚本的 `$1/$2...` 会被传入的参数**覆盖**，执行完恢复。

### 4.2 source 的返回值

`source` 的退出码就是脚本内最后一条命令的退出码，可以参与流程控制：

```bash
source env.local || { echo "配置加载失败"; exit 1; }
```

### 4.3 找不到文件时的行为

- `source 不存在的文件` → 报错 `no such file or directory`，返回非 0，**不会退出当前 shell**
- 但如果脚本内部有 `exit`，当前 shell 会被杀掉——下载来的脚本 source 前先扫一眼开头结尾

### 4.4 相关内建命令速查

```bash
type source        # 查看命令类型 → "source is a shell builtin"
help source        # bash/zsh 自带的帮助（比 man 准确）
help .             # 点命令的帮助
```

### 4.5 "取消 source"没有通用命令

source 产生的效果（环境变量、函数、alias）没有统一的 undo：

- venv / conda 提供了 `deactivate` 函数
- 其他情况只能手动 `unset 变量名`、`unset -f 函数名`，或者干脆关掉终端重开

---

## 五、易混淆对比

| 命令 | 是否启动新进程 | 环境变量能否传回当前 shell | 是否需要 +x 权限 | 典型用途 |
|---|---|---|---|---|
| `source f.sh` | 否 | **能** | 不需要 | 改当前终端环境 |
| `. f.sh` | 否 | 能 | 不需要 | 同上（POSIX 写法） |
| `sh f.sh` | 是（子进程） | 不能 | 不需要 | 跑一次性任务 |
| `./f.sh` | 是（子进程） | 不能 | **需要** | 跑一次性任务 |
| `exec ./f.sh` | 当前进程**被替换** | 谈不上（原 shell 没了） | 需要 | 彻底切换到新程序 |

`exec` 单独说明一下：它不创建子进程，而是让当前 shell 进程**直接变身**为目标程序，原 shell 不复存在，所以终端里 `exec` 后面通常接不上命令——一般用在"登录 shell 的最后一行"或包装脚本里。

---

## 六、动手实验（建议照敲一遍）

```bash
# 实验环境随便找个目录

# 1. 验证子进程传不回变量
echo 'export DEMO=hello' > env.sh
sh env.sh
echo $DEMO            # 输出为空
source env.sh
echo $DEMO            # 输出 hello

# 2. 验证 source 不需要可执行权限
chmod -x env.sh
source env.sh         # 仍然成功

# 3. 验证 exit 的杀伤力
echo 'exit' > kill.sh
source kill.sh        # 当前终端直接被关掉（截图留个纪念）

# 4. 验证函数加载
echo 'hello_func() { echo "i am loaded"; }' > lib.sh
source lib.sh
hello_func            # 直接可用
type hello_func       # "hello_func is a shell function"

# 5. 清理现场（或直接关终端）
unset DEMO
unset -f hello_func
rm env.sh kill.sh lib.sh
```

---

## 七、安全提醒

source = **在你的 shell 里原样执行任意代码**，权限和"你亲手敲了这些命令"完全一样。因此：

- 不要 source 来路不明的脚本（尤其网上"一键配置"教程里的 `source <(curl ...)`）
- 含密钥的 env 文件不要 source 后忘在公共机器的 shell 历史里
- source 前先 `cat` 一遍，重点看有没有 `exit`、`rm`、写文件的操作

---

## 八、速记卡

```
source = 灌进当前 shell 执行        . 是它的 POSIX 别名
能用它改环境的原因 = 没有子进程      子进程改环境永远传不回来
不需要 +x、不需要 shebang          脚本里的 exit 会杀掉当前 shell
函数/alias/环境变量 只能靠 source 加载
Windows 没有 source，venv 才有 .bat/.ps1 版激活脚本
```
