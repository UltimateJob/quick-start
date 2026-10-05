# BEHAVIOR（Isaac Sim）扩展场景 — 用户操作手册

[English](README.md) | **简体中文**

BEHAVIOR 是基于 Isaac Sim 5.1 / OmniGibson 3.9.2 的具身操作场景，机器人是 R1 Pro，策略是 π0.5。
与 LIBERO 不同，它**有三类前置装不进任何包**，必须由使用方准备，否则场景起不来或机器人不上线：

| 前置 | 为什么装不进来 | 谁准备 |
|---|---|---|
| 引擎镜像 `behavior:v3.9.2`（31.1 GB） | 是 Docker 本地镜像库，Runtime 用 `docker run` 消费 | 使用方（导入或自建） |
| 授权数据集（压缩 29.3 GiB / 解压 32.4 GiB 起） | 上游第三方资产，仅限非商业学术研究，不随本通道分发 | 使用方（按上游渠道取得） |
| π0.5 策略服务（独立 GPU 进程） | 是独立推理服务，不进 Isaac 镜像、也不进 Ability/Pilot 环境 | 使用方（OpenPI + 官方 radio 权重） |
| LLM 端点与密钥 | Agent 对话必需，密钥不进任何包 | 使用方（写进 Server 的 `.env`） |

安装器的 `prerequisites` 只做**探测**（失败只告警、不阻断），`post_install` 只做**提示**；
真正的准备动作在本手册。按下面三条主线走：

```text
① 环境准备 → ② 安装到框架 → ③ 在 Web 上复刻
```

---

## 0. 顺序与总览

```text
① 硬件/依赖自检（GPU、显存、磁盘、Docker、网络、端口）
② 取授权数据集            → 得到 --asset-root 指向的目录
③ 导入/构建引擎镜像        → 本机 Docker 里有 behavior:v3.9.2
④ 准备并启动 π0.5 策略服务 → 20080 上 LISTEN（★ 必须先于机器人四件套）
⑤ 配 LLM 密钥             → semantic-framework/.env
⑥ 一键安装扩展            → install.sh --extension isaac
⑦ 装后绑定与验收          → 添加兼容场景、绑定 Ability/模型、加 Pilot
```

两个最容易踩的顺序坑：

1. **π0.5 必须先起（第 ④ 步）再装机器人四件套**：VLA Ability 启动时会连策略服务做一次无动作预热，
   连不上就永远不 ready，四件套装完也验证不了。
2. **数据集解压峰值磁盘**：主资产压缩包与解压结果会同时占盘，`/tmp` 与 `--asset-root` 所在盘合计
   需要 **≥ 70 GiB 空闲**；解压成功后再删压缩包回收。

---

## 1. 环境准备

### 1.1 硬件与系统前提

| 项 | 要求 | 不满足的表现 |
|---|---|---|
| GPU | NVIDIA，独显；**π0.5 需要 ≥ 24 GB 级显存**，Isaac 场景本身约占 4.9 GB | π0.5 恢复权重 OOM |
| 显存（仅预览） | 预览需 ≥ 6144 MiB 空闲；6 GB 卡能启动场景但预览必然失败 | 预览报显存不足；空闲显存 <6144 MiB 时安装器自动跳过预览 |
| 磁盘 | `--asset-root` 与镜像缓存所在盘可用 ≥ 50 GiB（数据集解压峰值另需 ≥ 70 GiB） | Runtime 报「磁盘空间低于 50 GiB，暂停 Isaac 启动」 |
| Docker | 带 GPU 支持（`nvidia-container-toolkit`），能 `docker run --gpus all` | 容器起不来 |
| 网络 | 构建镜像需 `nvcr.io`、`repo.anaconda.com`、`developer.download.nvidia.com`、`pypi.org`、`pypi.nvidia.com`；取数据/权重见各节 | 构建/下载失败 |
| 端口 | 见第 4 节 | 端口冲突 |

一次性自检：

```bash
nvidia-smi --query-gpu=index,memory.used,memory.free --format=csv   # 挑空闲卡，预览看 free ≥ 6144
docker info >/dev/null && echo "docker ok"
df -h /tmp .
```

### 1.2 第 1 步：取授权数据集

`--asset-root` 指向的目录必须**含** `2026-challenge-task-instances/`（即指向它的上一级）。
数据集许可**仅限非商业学术研究**；取 `omnigibson.key` 等同于接受该许可。

**三个小包（直连即可）**：

```bash
HF=https://hf-mirror.com/datasets/behavior-1k/zipped-datasets/resolve/main
export BEHAVIOR_DATA=/path/to/datasets        # 即 install 时 --asset-root 的值
mkdir -p "$BEHAVIOR_DATA"

curl -L --progress-bar -o /tmp/2026-challenge-task-instances.zip "$HF/2026-challenge-task-instances.zip"  # 约 104 MB
curl -L --progress-bar -o /tmp/omnigibson-robot-assets-3.8.2.zip "$HF/omnigibson-robot-assets-3.8.2.zip"  # 约 641 MB
unzip -q /tmp/2026-challenge-task-instances.zip -d "$BEHAVIOR_DATA/2026-challenge-task-instances"
unzip -q /tmp/omnigibson-robot-assets-3.8.2.zip -d "$BEHAVIOR_DATA/omnigibson-robot-assets"
curl -L --progress-bar -o "$BEHAVIOR_DATA/omnigibson.key" \
  https://storage.googleapis.com/gibson_scenes/omnigibson.key   # 44 B 解密密钥
```

**主资产（29.3 GiB 压缩，慢）**：先确认 `/tmp` 与 `$BEHAVIOR_DATA` 所在盘合计 ≥ 70 GiB 空闲。

```bash
# 二选一；都能断点续传
curl -L -C - --progress-bar -o /tmp/behavior-1k-assets.zip "$HF/behavior-1k-assets-3.9.0.zip"
aria2c -x8 -s8 -k1M -c -d /tmp -o behavior-1k-assets.zip "$HF/behavior-1k-assets-3.9.0.zip"   # 多连接更快
unzip -q /tmp/behavior-1k-assets.zip -d "$BEHAVIOR_DATA/behavior-1k-assets"
```

> 要进度条就写 `-L --progress-bar`，不要加 `-s`——`-s` 会连进度条一起静默，几十 GB 的包会
> 变成「看着像卡住」。断了下重跑原命令即可续传，不必从头再来。解压无误后可删
> `/tmp/behavior-1k-assets.zip` 回收 29.3 GiB。

**校验**：

```bash
cat  "$BEHAVIOR_DATA/behavior-1k-assets/VERSION"                                     # 期望 3.9.0
test -f "$BEHAVIOR_DATA/2026-challenge-task-instances/metadata/available_tasks.yaml" && echo "任务元数据就位"
test -f "$BEHAVIOR_DATA/omnigibson.key"                                              && echo "解密密钥就位"
```

### 1.3 第 2 步：引擎镜像 `behavior:v3.9.2`

Runtime 用**完整摘要** `docker run`（`runtime-settings.json` 的 `image` 字段，本通道发布的包固定为
`sha256:fd750409…`），**不会替你拉取**。所以本机 Docker 里必须已经有该摘要对应的镜像。

#### 方式 A：导入维护者提供的镜像归档（推荐，摘要一致）

```bash
docker load -i behavior-v3.9.2.tar            # 归档由分发方提供
docker image inspect behavior:v3.9.2 --format '{{.Id}}'
# 期望输出：sha256:fd75040906f3270dc2e79aa306847c5be39b7ae20c4cbd4d219d5625afc6caa7
```

#### 方式 B：从上游源码自行构建

上游 `BEHAVIOR-1K` 的 `docker/Dockerfile` 是镜像唯一的构建输入。注意：**自建出的摘要必然与
上面固定值不同**（见「身份固定」）。

```bash
export BEHAVIOR_ROOT=/path/to/BEHAVIOR-1K
git clone --depth 1 --branch v3.9.2 https://github.com/StanfordVL/BEHAVIOR-1K.git "$BEHAVIOR_ROOT"
git -C "$BEHAVIOR_ROOT" describe --tags                       # 期望 v3.9.2

cd "$BEHAVIOR_ROOT"
docker build -f docker/Dockerfile -t behavior:v3.9.2 .        # 不要加 --progress=plain
docker image inspect behavior:v3.9.2 --format '{{.Id}}'       # 记下本机摘要
```

- 构建上下文就是该源码树；仓库自带 `.dockerignore` 已排除 `datasets/*` 与 `.git`，
  所以数据集解在它下面不影响构建。
- 会拉十余 GB 的 Isaac Sim 5.1 pip 包并编译 curobo；正常半小时量级，慢网会到数小时。
- 先把引擎源码克隆到 `$BEHAVIOR_ROOT`、再把数据集解到 `$BEHAVIOR_ROOT/datasets`：
  反过来 `git clone` 会因目标目录非空而失败（补救：把数据目录改名挪开、clone 后再挪回）。

#### 身份固定（自建镜像必看）

Runtime 启动前会校验 `runtime-settings.json` 里的 `image` 是否为本机存在的镜像。自建镜像的摘要
与分发包的固定值不同，直接装会在启动时找不到镜像。做法：**把本机摘要写回 Runtime 的
`runtime-settings.json` 的 `image` 字段**（该字段是摘要唯一的落脚点），再重装/重启 Runtime。

```bash
IMG=$(docker image inspect behavior:v3.9.2 --format '{{.Id}}')   # sha256:<64 位>
echo "$IMG"
# 编辑 Runtime 解包目录里的 runtime-settings.json，把 image 改成 $IMG
# 然后重装 Runtime（semanticctl runtime install ...）或重启 Runtime 使其生效
```

> 若你的安装器会对该文件做摘要校验、不允许就地修改，则改用「重打 Runtime 包」的路径：
> 在 Runtime 源码里改 `image` 并**升版本号**（同名同版本内容不同会被安装器拒绝）。
> 这也是为什么我们建议优先走方式 A。

**校验**：

```bash
docker image inspect behavior:v3.9.2 --format '{{.Id}}'   # 摘要应与 runtime-settings.json 的 image 一致
```

### 1.4 第 3 步：π0.5 策略服务

真正的推理在一个**独立 GPU 策略服务**里，由使用方自行准备，且**必须先于机器人四件套启动**。
模型配置组件（`r1pro-radio-model-0.1.1`）只存连接与映射：`endpoint = ws://127.0.0.1:20080`，
`actions_per_chunk = 16`。

| 内容 | 来源 | 关键约束 |
|---|---|---|
| OpenPI 环境 | 官方 baselines 指定的 fork `wensi-ai/openpi` 的 `behavior` 分支 | 需能 `import openpi.configs.tasks`、`openpi.serving.websocket_b1k_server`、`openpi.shared.eval_b1k_wrapper`；用上游 `Physical-Intelligence/openpi` 会 ImportError |
| π0.5 权重 | BEHAVIOR-1K 仓库 `docs/challenge/baselines.md` 的「Provided checkpoints」表里 `turning_on_radio` 一行（Google Drive 文件 id `1KojwNUz0HVwU3Ww2SVh3NKt-4asuI3y2`） | 必须含 `params/` 与 `assets/turning_on_radio/norm_stats.json`；只下 `pi05_base` 不是同一个模型 |
| 启动脚本 | R1 Pro 的 **BEHAVIOR Ability** 源码提供：`scripts/serve_behavior_policy.py`、`scripts/behavior_policy_chunk.py` | 不包含在扩展的六个产物里；从你获取该 Ability 源码的同一渠道取得 |
| GPU | 独立进程，与 Isaac 同时运行 | π0.5 约 3B 参数，需 ≥ 24 GB 级显存 |

```bash
export OPENPI_ROOT=/path/to/openpi
export PI05_CHECKPOINT=/path/to/pi05_turn_on_the_radio
mkdir -p "$(dirname "$OPENPI_ROOT")" "$(dirname "$PI05_CHECKPOINT")"

# ① 取 OpenPI 源码（必须是 baselines 指定的 fork 与分支）
git clone --branch behavior https://github.com/wensi-ai/openpi.git "$OPENPI_ROOT"
git -C "$OPENPI_ROOT" submodule update --init --recursive

# ② 建独立 uv 环境（GIT_LFS_SKIP_SMUDGE=1 不能省）
cd "$OPENPI_ROOT"
GIT_LFS_SKIP_SMUDGE=1 uv sync
source .venv/bin/activate
GIT_LFS_SKIP_SMUDGE=1 uv pip install -e .

# ③ 取权重（Google Drive id 见上表）
#    大陆直连 drive.google.com 常不通，二选一：
#    A) 挂代理
uvx gdown --proxy http://<你的代理> 1KojwNUz0HVwU3Ww2SVh3NKt-4asuI3y2 -O /tmp/pi05_turn_on_the_radio.zip
unzip -q /tmp/pi05_turn_on_the_radio.zip -d "$PI05_CHECKPOINT"
#    B) 同一台机器/内网已有人下过，直接复用（推理只需 params/ 与 assets/），别重复下十几 GB
#       find / -maxdepth 8 -type d -name "pi05_turn_on_the_radio" 2>/dev/null

# ④ 校验
ls "$PI05_CHECKPOINT" | tr '\n' ' '; echo            # 期望直接看到 params 与 assets
test -f "$PI05_CHECKPOINT/assets/turning_on_radio/norm_stats.json" && echo "权重完整"

# ⑤ 启动（独立终端、常驻；必须在 OpenPI 环境里跑）
nvidia-smi --query-gpu=index,memory.free --format=csv          # 先挑一张空闲卡，下例取 3 号
cd "$OPENPI_ROOT"
CUDA_VISIBLE_DEVICES=3 \
XLA_PYTHON_CLIENT_PREALLOCATE=false XLA_PYTHON_CLIENT_MEM_FRACTION=0.3 \
  .venv/bin/python /path/to/r1pro-ability/scripts/serve_behavior_policy.py \
  --checkpoint "$PI05_CHECKPOINT" --action-horizon 16 --port 20080

ss -ltnp | grep ':20080'                             # 看到 LISTEN 才算起来了
```

要点：

- `--action-horizon 16` 必须与模型配置的 `actions_per_chunk: 16` 一致；`--port` 必须与模型配置的
  `endpoint` 一致（都是 `20080`）。只改一边的表现是「服务在 20080 监听、Ability 连 18080」，机器人永不 ready。
- **显式指定一张空闲卡**：`CUDA_VISIBLE_DEVICES` 会覆盖 shell 里继承来的值；`pi05_b1k` 的
  `fsdp_devices=1`，每张可见卡各放一份完整模型副本，只要有一张可见卡被别人占满就整体 OOM。
- 已在运行同一个服务时直接复用，不要重复启动。
- **6 GB 卡跑不了这一步**：Isaac 场景已占约 4.9 GB，π0.5 权重就超过 6 GB——这是硬件门槛而非配置问题。

### 1.5 第 4 步：LLM 密钥

场景浏览与机器人上线都不需要 LLM；一旦要用对话驱动 Agent 就必须有可用的 LLM 端点。密钥按
「服务」命名，写在 Server 工作目录的 `.env`（启动时自动加载，日志打印 `.env 已加载`）：

```bash
# semantic-framework/.env —— 键名规则：SEMANTIC_LLM_API_KEY_<名称大写，'-' 转 '_'>
SEMANTIC_LLM_API_KEY_DEEPSEEK_CHAT=<真实密钥>
```

`.env` 不进版本控制，密钥不随任何组件包或 Bundle 复制，新机器要重新配。没有密钥时只有 `mock`
端点可用，而 mock 只能证明链路通、不能算作任务验收。

---

## 2. 安装到框架

同一个入口脚本，基础环境装完后自动继续装扩展：

```bash
curl -fsSL https://semantic.insightos.cn/install.sh | bash -s -- \
  --extension isaac --extension-project <项目ID> \
  --extension-asset-root /path/to/datasets --install-system-deps
```

| 参数 | 作用 |
|---|---|
| `--extension isaac` | 选择场景（必填） |
| `--extension-asset-root <绝对路径>` | BEHAVIOR Runtime 的**硬要求**：就是 1.2 的 `$BEHAVIOR_DATA`，其上一级目录需含 `2026-challenge-task-instances/` |
| `--extension-project <项目ID>` | 目标 Project；缺省用当前用户的默认项目 |
| `--extension-source oss\|github` | 通道，默认 `oss`；BEHAVIOR 六个产物都小于 2 GiB，GitHub 通道可完整镜像 |
| `--extension-package-dir <目录>` | 用「六产物 + 清单」完全离线安装 |
| `--extension-dry-run` | 只打印命令计划，不改动现场 |
| `--no-previews` | 跳过预览出图（`semanticctl extension install` 用）；经 `install.sh` 安装时，空闲显存 <6144 MiB 会自动跳过，无需手动传参 |

- 装之前先确认第 1.3 步的镜像、第 1.4 步的策略服务都已就绪；`probe` 失败只告警、不阻断。
- 扩展 Runtime 包声明的 `license` 由清单自动带上（`--accept-license behavior-assets`）。
- 固定顺序 Runtime → 场景 → 运行支持 → Ability → 模型 → Skill。

已装好基础环境时：

```bash
semanticctl extension install isaac --project <项目ID> --asset-root /path/to/datasets
```

> `semanticctl` 不在 PATH 时先 `export PATH="$HOME/.local/share/semantic/bin:$PATH"`（自定义 `--dir` 按实际目录）；
> 基础安装结束时会打印这两行并提示持久化，详见总入口。

---

## 3. 在 Web 上复刻

用 `admin` 登录 Web Studio（默认 `http://127.0.0.1:3000`），进入目标 Project。
装完有**三件事**必须在 Web 上做（与 LIBERO 相同），否则场景进不了项目、机器人起不来。

### 3.1 场景配置 → 添加兼容场景

安装只把场景注册进**场景目录**，不会自动进项目。在 Studio「场景」→「项目场景」里点 **添加**
（面板为空时是 **浏览场景**）：

![在「项目场景」里点「添加」/「浏览场景」](../images/isaac/step-1-scene-panel.png)

在弹出的「添加兼容场景」对话框里，点选场景卡片（推荐 `turning on radio`），再点 **添加到 Project**：

![勾选场景卡片并「添加到 Project」](../images/isaac/step-2-add-scene.png)

添加后可以在场景面板确认「运行环境」为 `BEHAVIOR / OmniGibson`，并看到 `turning on radio` 的初态：

![BEHAVIOR 场景在 Studio 中运行](../images/isaac/overview.png)

**完成标志**：场景出现在「项目场景」里，运行环境一栏为 `BEHAVIOR / OmniGibson`。

### 3.2 项目内容 → 绑定 Ability 与模型

安装把 Ability 与模型**导入**到项目，但**不会自动绑定到机器人**。不绑定，Ability 停在 `Standby`
（`abilityPort: 0`）直到超时，Pilot 一直 `offline`，设备页也就看不到可执行的机器人。

1. Studio 左侧「项目」→ **导入项目内容**，把对话框拉到最下面的 **机器人与模型配置** 一节：

   ![「导入项目内容」里的「机器人与模型配置」](../images/common/step-2-bind.png)

2. 点 `r1pro` 卡片上的 **选择 Ability / 模型**（想把当前选择设为以后新设备的默认，改点右上角 **设置项目默认**）；
3. 在弹窗里依次选择 **机器人型号** `r1pro` → **Ability（同一角色只选一个实现）** → **策略模型**
   （选 `0.1.1`，即 `r1pro-radio-model-0.1.1`），再点 **保存绑定**；
4. 回到该机器人的卡片，点 **立即生效 / 重试**——这一步会**停止并重启该 Robot 的组件一次**（场景保持当前状态），
   所以先确认机器人空闲。

**完成标志**：卡片上「待生效配置」与「实际运行模型」一致，不再停在 `Standby`。项目默认只对**后续首次绑定**生效，
单个 Robot 的选择独立保存。

> **π0.5 必须先起。** 策略 Ability 启动时会连 `ws://127.0.0.1:20080` 做一次无动作预热（见 1.4），连不上就永远不
> ready——即使这里绑定正确，机器人也上不了线。

### 3.3 设备中心 → 添加 Pilot

「设备中心」是机器人的全局观察入口，全新环境设备列表为空。注意 **「添加 Pilot」并不直接添加机器人**：
它只生成一个一次性加入码，机器人是在**机器人主机**上执行启动命令、启动器拿加入码换取凭据之后才注册进来的。

1. 顶部菜单进 **设备中心**，点 **添加 Pilot**：

   ![设备中心点「添加 Pilot」](../images/common/step-3-devices.png)

2. 对话框给出 **一次性加入码**（6 位数字，约 5 分钟过期、只能被领取一次）和一条启动命令，点 **复制命令** 一并拿走：

   ![复制一次性加入码与启动命令](../images/common/step-4-add-pilot.png)

3. 到 **Robot 主机**上执行这条命令（前台常驻；`<robot-id>` 换成实际机器人）：

   ```bash
   semantic-robot-instance start --config /etc/semantic/robots/<robot-id>/robot-deployment.yaml --join-code <加入码>
   ```

   启动器会通过局域网发现 Server（mDNS 服务名 `_semantic-server._tcp`；容器网络里 mDNS 常不可用，
   可显式追加 `--server-http http://<server>:8034 --server-ws ws://<server>:8035/ws/pilot`），用加入码换取
   该 Pilot 的专用凭据并存到 Robot 主机本地（实例目录的 `connection.yaml`，权限 `0600`），再依次拉起
   **AbilityFramework → 七类 Ability → Pilot**，最后由 Server 对账并下发期望的 Robot Skill。

4. 回到对话框点 **完成**——它只是关窗，配对在启动器领取加入码那一刻就完成了；稍等片刻，机器人应出现在设备列表里、
   连接状态 **在线**。

之后重启机器人**不再需要加入码**（凭据已存在机器人主机本地）：

```bash
semantic-robot-instance start --config /etc/semantic/robots/<robot-id>/robot-deployment.yaml
```

> **Server 配置两处**（`semantic-framework/.output/configs/semantic-server.yaml`，改完重启）：
> `robot_runtime.enabled: true`——否则设备页永远显示「当前项目尚未连接 Robot」；
> `robot_runtime.data_root` / `bundles_dir` 必须是**绝对路径**——这两个值会被原样写进安装收据与
> venv 转发脚本，相对路径会让受管 Robot 起不来。

### 3.4 验收

1. 场景在「项目场景」里，`turning on radio` 能选初态、能启动；
2. 机器人出现在「设备中心」，连接 **在线**、运行状态非 `degraded`；
3. 用**对话**驱动 Agent 执行收音机任务（需要 1.5 的 LLM 密钥）。

---

## 4. 端口表（新机器默认值互不冲突，一个都不用改）

| 用途 | 默认 | 由谁决定 |
|---|---|---|
| Server HTTP / WS | `8034` / `8035` | `semantic-server.yaml` 的 `http_addr` / `ws_addr`（预编译安装的默认值） |
| Web 前端 | `3000` | `semantic-web/vite.config.js` |
| BEHAVIOR Runtime | `18090` | `install.sh --extension`（清单 `runtime.endpoint`） |
| Ability 段 | `18100–18199` | `semantic-server.yaml` 的 `ability_port_first` / `ability_port_last` |
| π0.5 策略服务 | `20080` | 1.4 的 `--port`，必须等于模型配置的 `endpoint` |
| LIBERO Runtime | `8092` | LIBERO 清单（与 BEHAVIOR 可并存） |

同机并存 BEHAVIOR 与 LIBERO 时，两者默认都落在 `18100–18199`，要给两套环境分配不同端口段，
否则报 `http server bind ... failed`。

---

## 5. 常见故障

| 现象 | 原因与处理 |
|---|---|
| `Runtime 安装失败: Runtime Pack 需要内容 behavior_data，请在安装时提供路径` | 几乎都是 `--extension-asset-root` 传了空值（变量没导出），不是包坏了 |
| `docker: Error response from daemon: No such image: sha256:fd750409…` | 本机没有该摘要的镜像，见 1.3 |
| `Runtime … 仍有活动场景，请先停止场景` | Runtime 端口被别的 checkout 占用，换 `--endpoint` 或先停对方的场景 |
| 预览报显存不足 / `ran out of memory ... requested by op` | 预览需 ≥ 6144 MiB 空闲；策略服务 OOM 多为可见卡被他人占满，按 1.4 显式指定空闲卡 |
| 磁盘空间低于 50 GiB，暂停 Isaac 启动 | 清理镜像缓存或 `--asset-root` 所在盘，留 ≥ 50 GiB |
| 机器人永远 `offline` / Ability 停在 `Standby` | π0.5 未先起、或端口/`--action-horizon` 与模型配置不一致、或未绑定 Ability/模型 |
| 项目里看不到场景 | 未执行「添加兼容场景」 |

---

## 6. 卸载

先停场景与 Robot，再卸载。基础环境的 native-mujoco Runtime 不受影响：

```bash
semanticctl extension remove isaac
```

---

## 参考

### 六个产物与安装顺序

顺序固定：**Runtime → 场景 → 运行支持 → Ability → 模型 → Skill**。Bundle（运行支持）是底座，
后三者往它上面插，倒序装不上去。

| 角色 | 产物 | 体积 | 通道 |
|---|---|---|---|
| `runtime` | `behavior-runtime-0.1.18.zip` | 约 23 MB | OSS + GitHub |
| `scene_catalog` | `behavior-scenes-3.9.2.zip` | 约 1.3 KB | OSS + GitHub |
| `robot_base` | `r1pro-behavior-robot-0.1.1.zip` | 约 52 MB | OSS + GitHub |
| `robot_ability` | `r1pro-behavior-ability-0.1.3.zip` | 约 24 MB | OSS + GitHub |
| `model` | `r1pro-radio-model-0.1.1.zip` | 约 1.2 KB | OSS + GitHub |
| `robot_skill` | `vla-manipulation-0.1.10.zip` | 约 12 KB | OSS + GitHub |

Runtime 的 `installation_id` 是 `local-behavior-omnigibson`，endpoint 本文用 `18090`——与 LIBERO 的
`local-libero-robosuite-1.4` / `8092`、基础环境的 `native-mujoco` / `8090` 都不同，可以并存。

> **模型包必须先重打成 0.1.1。** 源文件里的 endpoint 是 `ws://127.0.0.1:18080`，要改成
> `ws://127.0.0.1:20080` 再升版本重打（同名同版本内容不同会被安装器拒绝）。清单里登记的是重打后的 `0.1.1`。

### 许可

BEHAVIOR / OmniGibson 与授权数据集是上游第三方资产，已获授权在本通道内分发。清单的 `license` 与
Runtime 包的 `license` 都是 `behavior-assets`，安装器据此自动补 `--accept-license behavior-assets`。
数据集只按上游许可（**仅限非商业学术研究**）由使用方单独取得，不随本通道分发。

### 设计依据

清单里 `prerequisites` / `post_install` / `host_requirements` / `ports` 的表达方式，以及通道布局与
发布流程，见 [`../../docs/extensions.md`](../../docs/extensions.md)；总入口与目录约定见
[`../README.zh-CN.md`](../README.zh-CN.md)。
