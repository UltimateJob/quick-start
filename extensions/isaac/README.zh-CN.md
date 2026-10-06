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
3. 用**对话**驱动 Agent 执行收音机任务（需要 1.5 的 LLM 密钥）；粘贴的整段提示词与判读方式见第 7 节。

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

## 7. 任务复现：对话页提示词与结果判读

前置就绪（第 1 节）、扩展装好（第 2 节）、Web 上三件事做完（第 3 节）之后，真正跑任务是在 **Web 对话页粘贴一整段提示词**。本节给出可直接复制的两段提示词、场景与实例的对应关系，以及结果怎么判读。

### 7.1 复现总流程

```text
① 前置就绪     引擎镜像 behavior:v3.9.2 / 授权数据集(--asset-root) / π0.5 策略服务(:20080) / LLM 密钥(.env)
② 拉起仿真场景 启动 BEHAVIOR 场景的一个原生实例（301–320）
③ 进入对话页面 在 Web 打开 Agent 会话
④ 输入提示词   把 7.3 / 7.4 的整段文本作为一条消息粘贴发送
⑤ 等待任务状态 完成 / 失败 / 异常
⑥ 判读与记录   成功 = ok；失败取「阶段 + 错误码/原因 + 最近场景多角度拍照」，记入 7.7 的表格
```

两个顺序坑：

1. **π0.5 策略服务必须早于机器人四件套**（同 1.4 与 3.2）：VLA Ability 启动时会连策略服务做一次无动作预热，连不上就永远不 ready，四件套装完也验收不了。
2. **同一个场景实例要跑完整条任务链再换实例**：中途换实例会让「阶段 / 错误码」失去可比性。

### 7.2 场景与实例

- 收音机任务的 `scene_id` 是 `behavior-turning_on_radio-0`（展示名 `turning on radio`）。`--scene` 只认 `scene_id`，写展示名匹配不到任何场景——清单里的默认场景也是按这个值固定的（第 2 节）。
- 一个场景目录含 7 个任务，每个任务有 20 个原生实例（`instance-301` … `instance-320`）。结果按实例号统计，**每次跑之前先记下实例号**。
- 显存：预览需 ≥ 6144 MiB 空闲；6 GB 卡能启动场景但预览必然失败，安装时用 `--generate-previews=false`（经 `install.sh` 安装会自动跳过）。

### 7.3 提示词一：打开收音机（Turn on radio）

**怎么用**：进入 Web 对话页（Agent 会话）后，把下面整段**作为一条消息**粘贴发送，不要再拆分、不要改写参数。提示词里已经写死了三件事，这正是结果可复现的前提：绑定机器人 `robot_r1`；每一步调哪个 Robot Skill 与完整 JSON 输入；每步成功才进下一步、失败或暂停即停、不自动重试、不修改参数、不自动重置场景。

**目前不区分左右手**（自动计算用哪只手抓、哪只手操作），直接复制下面这段即可：

```text
创建一个任务，绑定机器人 robot_r1，依次完成：
初始化 → 导航到收音机附近 → 抓取收音机并抬升 → 调整躯干位置 → 打开收音机。

依次使用 behavior-init、behavior-nav、behavior-grasp、behavior-upright、
behavior-radio-button 五个 Robot Skill。

每一步成功后才能进入下一步。失败或暂停时保留执行结果，
报告具体阶段、错误码和原因，停止后续步骤。
Task 不自动重试 Skill，不修改输入参数。

不查询语义地图。机器人状态、目标位置和场景观测，
由 Robot Agent 通过已有能力获取。

第一步：初始化

调用 behavior-init，输入：
{"arm_posture": "raised"}

Skill 根据当前躯干状态计算双臂准备姿态的末端目标，
左右手分别通过一次末端 IK 动作完成初始化。

第二步：导航到收音机附近

调用 behavior-nav，输入：
{
  "object_name": "radio_89",
}

目标位置和朝向由导航能力根据当前实例计算。
直接使用计算出的站位
以导航执行和到达检查结果判定本步骤是否成功。

第三步：抓取收音机并抬升

调用 behavior-grasp，输入：
{
  "object_ref": "radio_89",
  "side": "auto",
  "prompt": "red radio handle",
  "approach_preference": "downward",
  "grasp_offset_m": [0.0, 0.0, 0.0],
  "liftoff_height_m": 0.005,
  "opening_m": 0.05,
  "maximum_force_n": 50.0
}


按当前 Skill 的两阶段姿态流程执行：
1. 根据当前状态和相机标定计算观察姿态，调整躯干。
2. 视觉识别收音机，取得本次抓取中心。
3. 根据识别目标联合计算躯干和手臂的操作姿态，
   单次调整躯干，再按实测关节校验抓取路径。
4. 接近、闭爪确认、抬升。

识别后保持底盘不动，沿用识别得到的 body 坐标。
操作姿态允许四个躯干关节参与求解。

自动朝向使用收音机把手延长方向与世界竖直方向构成的平面：
允许腕部相机光轴在该平面内俯仰，夹爪延伸方向允许倾斜；
按 Skill 规则保持相机安装侧朝身体内侧。
不指定固定四元数，也不额外要求夹爪竖直向下或开合轴严格垂直把手。

坐标与参数：
- grasp_offset_m 使用物体局部坐标，叠加到视觉识别中心。
- pregrasp_offset_m 和 lift_offset_m 使用世界坐标。
- 预抓取点在抓取点上方 10 cm，抬升终点在抓取点上方 12 cm。
- opening_m 为平均单指行程，预张开 0.05 m。
- maximum_force_n 为最大夹持力
- 闭爪成功且接触结果匹配本次目标和候选后，才执行抬升。
- timeout_seconds 为每个 Action 的超时预算。
- speed_rad_s 为调整躯干时的速度限制

保留以上数值，坐标转换、姿态和路径计算均由 Skill 完成。
第四步：调整躯干状态
调用 behavior-upright，输入：
  {
    "timeout_seconds": 150
  }

将躯干恢复到 Skill 定义的原生初始姿态。
使用 Skill 内置的平滑轨迹及速度、加速度限制，
根据实际关节位移计算运动时长，等待回读确认到位后进入抓取。
已经处于目标容差内时，允许 Skill 跳过运动并完成复核。

第五步：操作收音机按钮

仅在抓取并抬升成功后调用 behavior-radio-button，输入：
{
  "button_prompt": "red button",
}


允许该 Skill 内置的单次翻转流程：
首次未找到按钮时，持物手轴向翻转，再计算观察位并识别一次。
传感器错误、运动失败或第二次识别失败时停止。
Task 不额外重跑 Skill 或修改参数。

最终报告：
- 五个步骤各自的执行状态。
- 失败或暂停的阶段、错误码和原因。
- 抓取接触确认及抬升结果。
- 按钮识别、翻转和接近动作结果。
- 原生任务评测结果；无法获取时明确报告“无法获取”。

Skill 动作完成与原生任务成功分别记录，
不得根据动作完成情况推断收音机已经打开或原生任务已经成功。
```

### 7.4 提示词二：投放三个易拉罐（Soda can）

**目前需要提供罐子的颜色信息**（113 蓝色、114/115 橙色），直接复制下面这段：

```text
创建一个任务，绑定机器人 robot_r1，以下七步作为模板，依次对 113、114、115 各执行一轮。仅将导航、抓取、放置中的罐子引用替换为当前对象；113 的 prompt 使用 "blue soda can"，114/115 使用 "orange soda can"。其余参数不变。
**初始化 → 导航到易拉罐附近 → 抓取并抬升至持物位 → 恢复直立 → 导航到垃圾桶附近 → 从上方投放 → 恢复直立。**
使用已有的 behavior-init、behavior-nav、behavior-grasp、behavior-upright、behavior-place Robot Skill，严格按以下顺序执行。
每一步成功后才能进入下一步。任一步失败或暂停时，保留执行结果并报告原因，停止后续步骤，不自动重试、不修改参数。
机器人状态、目标几何和场景观测由 Robot Agent 通过自身能力获取。严格使用各步骤给出的 JSON 输入；唯一的运行时数据补充是第六步的 object_size_m 和 eef_from_object，必须从本轮、当前同一罐子的第三步 behavior-grasp 成功结果中原样获取并传入。除此之外，未提供的可选字段沿用 Skill 默认值。orso 和 operation_torso 必须保留对象格式 {"mode":"auto"}。
注意can_of_soda_114和can_of_soda_115是orange soda can，而can_of_soda_113是blue soda can
**第一步：初始化**
调用 behavior-init，输入：
{}
以 Skill 的执行结果判定初始化是否成功。
**第二步：导航到抓取位置**
仅在初始化成功后，调用 behavior-nav，输入：
{"object_name": "can_of_soda_115"}
由导航能力根据当前实例自动计算站位和朝向。使用当前 Skill 的站位计算结果，不额外添加偏移。以导航执行和到达检查结果判定本步骤是否成功。
**第三步：抓取并抬升至持物位**
仅在导航成功后，调用 behavior-grasp，输入：
{"object_ref": "can_of_soda_115","prompt": "orange soda can","side": "auto","approach_preference": "horizontal","grasp_offset_m": [0.0, 0.0, 0.0],"opening_m": 0.05,"maximum_force_n": 50.0,"liftoff_height_m": 0.005,"minimum_confidence": 0.3,"timeout_seconds": 900,"torso": {"mode": "auto"},"operation_torso": {"mode": "auto"}}
由 Skill 完成观察姿态调整、视觉识别、抓取候选生成和自动选手。保留水平接近偏好，夹爪开合方向与识别主轴垂直，具体末端朝向由 Skill 按现有实现选择。
接近位置由识别包围盒和张开手指几何自动计算。SDK/cuRobo 规划到接近位置及保持末端朝向的直线推进；执行请求在状态匹配时复用预规划轨迹。
接近成功后闭爪，按当前 Skill 和 Ability 的判据确认夹持目标，再携物抬起并收至 Skill 计算的自然屈肘持物位。实测到位且确认目标仍被持有后，本步骤才成功。
参数说明：
grasp_offset_m 使用物体局部坐标，叠加在本次识别出的物体中心上。
opening_m 表示平均单指行程，预张开为 0.05 m。
最大夹持力为 50 N。
timeout_seconds 为每个 Action 的超时预算，按当前 Skill 实现执行。
接近距离、携物目标、坐标转换和运动路径由 Skill 与 SDK 内部计算。
保留上述输入，不额外插入动作。任一识别、求解、移动、闭爪或携物确认阶段失败时，停止后续动作并报告具体阶段和错误。
**第四步：恢复直立**
仅在抓取并到达持物位成功后，调用 behavior-upright，输入：
{}
按 Skill 的现有实现将躯干恢复到初始目标姿态，保持夹持。以躯干到位检查结果判定本步骤是否成功。
**第五步：导航到投放位置**
仅在恢复直立成功后，调用 behavior-nav，输入：
{"object_name": "trash_can_116"}
由导航能力根据当前实例计算目标站位和朝向。导航期间保持现有夹持。以导航执行和到达检查结果判定本步骤是否成功。
**第六步：从上方投放**
仅在导航成功后，调用 behavior-place，输入：
{"object_ref": "can_of_soda_115","prompt": "orange soda can","target": {"object_ref": "trash_can_116","prompt": "trash can","type": "top_open_container"},"release_mode": "drop","release_opening_m": 0.05,"maximum_force_n": 80.0,"timeout_seconds": 900}
以上为基础 JSON。调用 behavior-place 前，必须通过 robot.get 读取本轮当前罐子的第三步 behavior-grasp 成功执行结果，将 object_size_m 和 eef_from_object 原样补入 JSON 顶层，与 object_ref 同级.确认抓取结果的 object_ref 与当前罐子一致。两个字段不能省略、设为 null、使用历史轮次数据，也不能用 grasp_pose 或 carry_pose 替代，不得自行重算。缺少任一字段时停止并报告数据传递缺失，不重新识别持物。垃圾桶及开口仍由 Skill 识别。

省略 side，由 Skill 按现有夹爪反馈判据识别持物手。判断不明确时停止并报告原因。
由 Skill 获取持物和目标容器的必要几何信息，计算释放位置及末端姿态，按现有实现运动到顶部开口上方。接近动作成功后才张爪释放，随后完成撤手。
识别、几何计算、运动、释放或撤手失败时，停止后续动作并报告原因。
**第七步：恢复直立**
调用 behavior-upright，输入：
{}
按 Skill 的现有实现将躯干恢复到初始目标姿态，保持夹持。以躯干到位检查结果判定本步骤是否成功。
**执行与结果要求**
规划受理、动作下发和路径规划成功均不能替代对应 Skill 的完成结果。
任一步失败、暂停或场景回合结束时，停止后续步骤，不自动重置场景或重新执行。
Action 超时预算与场景回合步数预算分别生效，不修改场景预算。
```

### 7.5 两段提示词的隐含前提

- **易拉罐必须显式给颜色**：`can_of_soda_113` 是蓝色（`"blue soda can"`），`can_of_soda_114` / `can_of_soda_115` 是橙色（`"orange soda can"`）。不给颜色时识别容易认错。
- **收音机不区分左右手**：`"side": "auto"`，由 Skill 按当前状态计算。
- **投放第六步的两个字段必须从本轮同一罐子取**：`object_size_m` 与 `eef_from_object` 必须从**本轮当前罐子**的第三步 `behavior-grasp` 成功结果里原样取出，与 `object_ref` 同级补进 JSON 顶层；不能用历史轮次数据，不能用 `grasp_pose` / `carry_pose` 替代，不得自行重算。缺任一字段即停止并报告「数据传递缺失」。
- **`torso` / `operation_torso` 保留对象格式** `{"mode": "auto"}`，不要传字符串。
- **口语指令要能对上地图实体名**：实测把「打开客厅桌上的收音机」发给 Agent，它会先去查语义地图、然后要求提供「地图中的准确名称或 ID」；地图里是英文 ID（如 `radio_89`、`breakfast_table_xftrki_0`），中文口语描述匹配不上。下指令优先用地图里的实体名 / ID。

### 7.6 等待与判读

```text
拉起仿真场景 → 输入提示词 → 等待任务状态（完成 / 失败 / 异常）
成功：ok
失败：取任务执行阶段、错误原因，最近场景（不同角度拍照）
```

判读要点：

- **任务级终态 ≠ 单步动作完成**：Robot Skill 动作 `completed` 不代表原生任务成功，也不代表收音机真的被打开了；「动作完成」与「原生任务成功」要分别记录，不得互相推断。
- **失败时区分「失败的那一步」与「被停止的其余步」**：任务进入终态 `failed`（`reason: task_failed`）时，未执行的 SubTask 会一并变成 `stopped`；报告要写清哪一步是**唯一失败点**、哪些是被连带停止的。
- **部分返回值本身带不确定标记**（例如导航的 `yaw_verified=false`，或到达距离 `distance_to_target_m≈0.0478 m`），要如实记录为复现变量，不要当成成功。
- **抓取从未进入观察 / 识别 / 求解 / 移动任一阶段**（下发前就被输入模型拒绝）时，机器人物理状态是**未确认**的，不能推断为「抓取失败」。

### 7.7 复现记录表模板（每跑完一轮填一行）

| 日期 | 任务 | 实例 | 结果 | 失败阶段 | 错误码 / 原因 | 截图 | 备注 |
|---|---|---|---|---|---|---|---|
| | radio / soda | 301–320 | ok / fail | 第几步 + Skill 名 | | 多角度 | |

### 7.8 复现中常见的失败模式

| 现象 / 报错 | 阶段 | 大致原因 | 处理 |
|---|---|---|---|
| 按钮位置未找到满足关节余量和夹爪接近方向的末端姿态 | `behavior-radio-button` 观察位求解 | 夹爪接近方向叠加关节余量后无解 | 换实例或重跑（换个初始帧）；记为**求解失败**，不是感知失败 |
| 收音机拿反了 | `behavior-grasp` | 抓取姿态与把手朝向识别偏差 | 记实例号后重跑；核对 `prompt` 与 `approach_preference` |
| 抓取时把收音机碰到了 | `behavior-grasp` 接近 | 接近路径干涉 | 记实例号后重跑；反馈给 Skill 侧 |
| `2 validation errors for Input — 缺少必填字段 pregrasp_offset_m 与 lift_offset_m` | `behavior-grasp` 下发前（robot_run） | 该 Skill 版本把这两个字段列为必填，但不在「批准输入」里 | 与 Skill 版本对齐输入模型；按「不修改参数」约束本轮直接判失败 |
| Workflow 终态 `failed`，21 个 SubTask 只有 2 个完成 | 全局 | 上一条的连锁停止 | 报告注明**唯一失败点**与被 `stopped` 的范围 |
| 导航返回 `yaw_verified=false` | `behavior-nav` | 偏航未验证 | 如实记录，作为复现变量 |
| 抓取动作未建立、无物理回执 | `behavior-grasp` | 输入校验失败，未进入执行 | 机器人物理状态记为**未确认**，不得推断 |
| Agent 回复「查不到客厅桌 / 收音机」并要求提供准确名称或 ID | 规划（找目标） | 中文口语描述匹配不上地图里的英文实体 ID | 改用地图实体名 / ID 下指令，或先在对话里确认目标 |

安装期的问题（镜像、端口、磁盘、绑定、项目里看不到场景、Ability 停在 `Standby`）见第 5 节。

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
