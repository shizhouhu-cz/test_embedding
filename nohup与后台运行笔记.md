# nohup 与 & 笔记：原理与实践

## 〇、一句话定位

| | 本质 | 解决什么 |
|---|---|---|
| `&` | **shell 的语法**（后台运行符） | 让 shell **不等**这个命令，自己继续干活 |
| `nohup` | **一个独立程序**（/usr/bin/nohup） | 让目标程序**免疫 SIGHUP**（终端挂断信号） |

两者解决的问题完全不同，经常连用只是因为各管一半：`&` 管"不阻塞你"，`nohup` 管"不随终端死"。

---

## 一、前置原理：会话、控制终端与 SIGHUP

理解 nohup 必须先懂 Unix 的三层分组结构：

```
会话 (session)
├── 控制终端 (controlling terminal) ← 你眼前这个终端窗口
├── 前台进程组   ← 当前吃键盘输入的组；Ctrl+C 只发给它
└── 后台进程组   ← & 产生的作业待的地方
```

- **Ctrl+C（SIGINT）** 只发给**前台进程组**
- **终端关闭/断开（SIGHUP）** 发给会话首进程（通常是 shell），shell 再把 HUP 传给自己的作业
- 所以：**前台、后台跑的程序都会随终端关闭而死**——除非忽略 HUP 或换掉会话

`hup` 这个名字来自老式调制解调器：HUP = hang up（挂断电话），终端"挂断"了，挂在它上面的进程就该死了。nohup = **no hang up**。

---

## 二、& 详解：机制与策略分离的实例

`fork + exec` 是内核机制，**wait 与否是 shell 的策略**，`&` 就是切换这个策略的开关：

| 写法 | fork+exec | shell 行为 |
|---|---|---|
| `python x.py` | ✓ | 调 waitpid 阻塞，等子进程退出 |
| `python x.py &` | ✓（一模一样） | 不 wait，把 PID 记入**作业表**，立即回到读命令循环 |

### 2.1 & 不改变任何内核属性

后台进程：

- 依然是 shell 的子进程（进程树位置不变）
- 依然属于同一个会话、持有控制终端 → **stdout/stderr 照样打到屏幕上**
- 没有脱离终端，所以终端死了它照样收 HUP → **单独 & 活不过终端关闭**

### 2.2 作业控制全家桶

```bash
python daemon/daemon_proc.py &   # 启动，[1] 是作业号
echo $!                          # $! = 最近一个后台进程的 PID
jobs                             # 看作业表：[1] + running
fg %1                            # 调回前台
Ctrl+Z                           # 挂起前台作业（SIGTSTP）
bg %1                            # 让挂起的作业转后台继续跑
disown %1                        # 从作业表除名 → shell 退出时不再给它发 HUP
```

### 2.3 两个坑

1. **后台进程读 stdin 会被冻结**：两个作业抢一个键盘会乱套，内核规定后台作业读 stdin 时收到 SIGTTIN 直接暂停。你的 daemon 不读 stdin，所以安全
2. **退出 shell 时后台作业的下场**：zsh 默认（HUP 选项开启）会给所有作业发 SIGHUP；bash 依赖终端关闭时的 HUP 广播。总之：**& 单独用，大概率活不过终端窗口关闭**，要活下来接 disown 或 nohup

### 2.4 僵尸尾巴

shell 不 wait 的孩子死了谁来收尸？shell 注册了 SIGCHLD 处理器顺手 reap，所以平时看不到僵尸。但如果某个常驻程序反复 fork 却既不 wait 也不处理 SIGCHLD，子进程尸体（`<defunct>`）就会堆积。

---

## 三、nohup 详解：它只做两件事

`nohup cmd` 执行时：

1. **把 SIGHUP 的处置设为"忽略"**（SIG_IGN），然后 `exec cmd` —— 程序替换后信号配置保留
2. 如果 stdout 是终端 → **重定向到 nohup.out**（stderr 跟随 stdout），防止"人都下线了输出还在往终端写"

```bash
nohup .venv/bin/python daemon/daemon_proc.py
```

### 3.1 三个常见误解

| 误解 | 真相 |
|---|---|
| "nohup = 后台运行" | **错**。nohup 完全是前台命令，照样占住终端，Ctrl+C（SIGINT）照样能杀它。它只免疫 HUP 这一种信号 |
| "nohup 后输出消失了" | 没有，被写进了当前目录的 `nohup.out` |
| "nohup 后进程就不归终端管了" | 进程组/会话都没变，只是 HUP 被忽略了 |

### 3.2 标准用法

```bash
nohup cmd > out.log 2>&1 &          # 经典全家桶：免HUP + 日志落盘 + 后台
nohup cmd >/dev/null 2>&1 &         # 不关心日志就用这个
```

`2>&1` 顺序不能反：先把 stderr 合并到 stdout，再整体重定向。

---

## 四、五套方案对比

| 方案 | 后台？ | 免终端关闭？ | 说明 |
|---|---|---|---|
| `cmd` | ✗ | ✗ | 前台，Ctrl+C 可杀 |
| `cmd &` | ✓ | ✗ | shell 继续干活，但终端一关就死 |
| `nohup cmd &` | ✓ | **✓** | 最常用组合；输出去 nohup.out |
| `cmd & disown` | ✓ | ✓ | 事后补票，输出仍在终端 |
| `setsid cmd &` | ✓ | ✓ | 彻底换会话（新会话首进程），PPID 变 launchd |

经典 daemonize 仪式（双 fork + setsid）干的就是 setsid 那行的事。

---

## 五、实际应用场景

### 5.1 跑本项目的 embedding daemon

```bash
cd /Users/shizhouhu/Code/test_embedding
nohup .venv/bin/python daemon/daemon_proc.py > daemon.out 2>&1 &
echo $!        # 记下 PID
pgrep -af daemon_proc          # 确认活着
ps -o pid,ppid,command -p $(pgrep -f daemon_proc.py)   # PPID 应为 1
```

关掉终端窗口再开一个，daemon 依然活着（模型不用重新加载 30 秒）——这正是 daemon 架构的意义。

### 5.2 SSH 远程跑长任务（nohup 的诞生场景）

远程服务器上 `python train.py` 跑 8 小时，SSH 一断网，终端会话挂断 → 全家 HUP → 白跑。`nohup ... &` 后即使断线任务照跑，回来 `tail -f nohup.out` 看进度。

### 5.3 更现代的替代方案（知道即可）

| 工具 | 定位 |
|---|---|
| `tmux` / `screen` | 会话与终端解耦，断线重连后**画面原样恢复**，交互式任务首选 |
| `launchd`(macOS) / `systemd`(Linux) | 系统级服务托管：开机自启、崩溃重启、日志管理，生产环境正解 |
| `&` + `nohup` | 一次性、轻量、临时任务 |

---

## 六、动手实验（建议照敲一遍）

```bash
# 实验 1：& 会在终端关闭时死掉
python3 -c "import time; time.sleep(600)" &
pgrep -af "time.sleep"     # 活着
# → 直接关闭终端窗口，重开：进程已死

# 实验 2：nohup & 能活下来
nohup python3 -c "import time; time.sleep(600)" > /dev/null 2>&1 &
# → 关终端重开：进程还活着
ps -o pid,ppid,command -p $(pgrep -f time.sleep)   # PPID=1，被 launchd 收养

# 实验 3：验证 nohup 不是后台
nohup python3 -c "import time; time.sleep(60)"    # 不加 &
# → 终端被占住了！新开终端 kill 掉，或等 60s

# 实验 4：$! 与 jobs
sleep 100 & echo $!
jobs
kill %1

# 清理
pkill -f time.sleep
```

---

## 七、速记卡

```
&      = 别等（shell 不 wait，记进作业表）
nohup  = 别挂电话（忽略 SIGHUP + 输出转 nohup.out）
nohup ≠ 后台    ← 高频误解，它只是前台地免疫 HUP
$!     = 最近后台进程的 PID
disown = 事后除名，免 HUP
setsid = 换会话分家，最彻底
活不过终端关闭的：cmd & 、cmd
活下来的：       nohup cmd & 、cmd & disown 、setsid cmd &
生产环境请用 launchd/systemd/tmux，nohup 只是应急
```
