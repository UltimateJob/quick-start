# 扩展场景

[English](README.md) | **简体中文**

基础安装只准备基础工作区。**扩展场景**是独立发布、旁挂于不可变基础制品之外的产物，
由安装器在基础环境装好之后按需拉取——为不装场景的人省下几十 GB 的下载量。

本目录是扩展场景的总入口。每个场景一份**用户操作手册**，按同一条主线展开：

```text
① 环境准备（装不进包、只能由人准备的先决条件）
② 安装到框架（install.sh --extension <id> 或 semanticctl extension install）
③ 在 Web 上复刻（截图 + 红框标出要点的地方的按钮）
```

## 场景清单

| 场景 | 标识 | 内容 | 手册 |
|---|---|---|---|
| LIBERO | `libero` | robosuite 1.4 + Franka + SmolVLA，六个产物约 11.5 GB | [libero/README.zh-CN.md](libero/README.zh-CN.md) |
| BEHAVIOR（Isaac Sim） | `isaac` | OmniGibson 3.9.2 + R1 Pro + π0.5，六个产物约 99 MB，另需 31 GB 引擎镜像与自行取得的授权数据集 | [isaac/README.zh-CN.md](isaac/README.zh-CN.md) |

两份手册彼此独立。**装 BEHAVIOR 请先读手册的第 1 节**——引擎镜像、授权数据集与 π0.5 策略服务
都不随包分发，不先备好就无法跑通。LIBERO 的产物自足，按手册照做即可。

## 从哪进入

命令行（与基础安装同一个入口脚本，装完基础环境后自动继续）：

```bash
curl -fsSL https://semantic.insightos.cn/install.sh | bash -s -- \
  --extension libero --extension-project <项目ID> --install-system-deps
```

已装好基础环境时，也可以用内置管理命令单独操作扩展：

```bash
semanticctl extension list                 # 列出已知扩展
semanticctl extension show libero          # 看清单：产物、体积、顺序、许可
semanticctl extension verify libero        # 只下载校验，不落地（排障 / 验收）
semanticctl extension install libero --project <项目ID>
semanticctl extension remove libero
```

> **`semanticctl` 默认不在 PATH 上。** 基础安装结束时只打印
> `export SEMANTIC_HOME=<安装目录>` 与 `export PATH="$SEMANTIC_HOME/bin:$PATH"`，并提示把这两行写进
> `~/.bashrc` / `~/.zshrc`。在**新终端**里用裸 `semanticctl` 之前，先执行这两行（默认安装目录为
> `~/.local/share/semantic`；自定义 `--dir` 时按实际目录），或直接用绝对路径
> `~/.local/share/semantic/bin/semanticctl`。下文命令里的 `semanticctl` 都按此约定。

`--source oss|github` 选通道（默认 `oss`）。清单与版本指针统一从 OSS 取，GitHub Release 是镜像通道；
LIBERO 有三个产物超过 GitHub 单个资产 2 GiB 上限，走 GitHub 时会**自动回退 OSS**。

源码编译路径（TUI 阶段 8）与预编译通道**共用同一份清单**，只是产物来源不同：TUI 从上游源码本机构建，
预编译通道下载已验证产物。要改组件版本用 TUI，只想跑起来用 `--extension`。

## 三个共同的 Web 步骤

安装只负责把产物落到框架里，**装完还必须在 Studio 里做同样三件事**，否则场景进不了项目、机器人起不来。
三步一一对应各场景手册的同一编号小节（LIBERO 手册 §3.1–3.3、BEHAVIOR 手册 §3.1–3.3）；下面按 LIBERO 举例，
逐场景取值（机器人型号、场景卡片、模型版本、端口）以对应手册为准。

### ① 场景配置 → 添加兼容场景（手册 §3.1）

安装只把场景注册进**场景目录**，不会自动进项目，必须手工加一次：

1. Studio 左侧进「场景」→「项目场景」，点 **添加**（面板为空时是 **浏览场景**）：

   ![「项目场景」里的「添加」](images/libero/step-1-scene-panel.png)

2. 在「添加兼容场景」对话框里搜索或滚动到要用的卡片，点选它（可多选），再点 **添加到 Project**：

   ![勾选场景卡片并「添加到 Project」](images/libero/step-2-add-scene.png)

**完成标志**：回到「项目场景」能看到该场景，且运行环境一栏是对应 Runtime——LIBERO 为 `LIBERO / LIBERO-Pro`，
BEHAVIOR 为 `BEHAVIOR / OmniGibson`。别全量出图：不限定场景会对全部初态逐一出图，很慢；空闲显存低于
6144 MiB 时安装器会**自动**跳过预览，要手动控制可对 `semanticctl extension install` 加 `--no-previews`。

### ② 项目内容 → 绑定 Ability 与模型（手册 §3.2）

安装把 Ability 与模型**导入**到项目，但**不会自动绑定到机器人**。不绑定，Ability 停在 `Standby`
（`abilityPort: 0`）直到超时，Pilot 一直 `offline`，设备页也就看不到可执行的机器人。

1. Studio 左侧「项目」→ **导入项目内容**，把对话框拉到最下面的 **机器人与模型配置** 一节：

   ![「导入项目内容」里的「机器人与模型配置」](images/common/step-2-bind.png)

2. 点某机器人卡片上的 **选择 Ability / 模型**（想把当前选择设为以后新设备的默认，改点右上角 **设置项目默认**）；
3. 在弹窗里依次选择 **机器人型号** → **Ability（同一角色只选一个实现）** → **策略模型**，再点 **保存绑定**；
4. 回到该机器人的卡片，点 **立即生效 / 重试**——这一步会**停止并重启该 Robot 的组件一次**（场景保持当前状态），
   所以先确认机器人空闲。

**完成标志**：卡片上「待生效配置」与「实际运行模型」一致，不再停在 `Standby`。项目默认只对**后续首次绑定**生效，
单个 Robot 的选择独立保存。

### ③ 设备中心 → 添加 Pilot（手册 §3.3）

「设备中心」是机器人的全局观察入口，全新环境设备列表为空。注意 **「添加 Pilot」并不直接添加机器人**：
它只生成一个一次性加入码，机器人是在**机器人主机**上执行启动命令、启动器拿加入码换取凭据之后才注册进来的
——这就是「拿到加入码之后怎么把机器人加进来」。

1. 顶部菜单进 **设备中心**，点 **添加 Pilot**：

   ![设备中心点「添加 Pilot」](images/common/step-3-devices.png)

2. 对话框给出 **一次性加入码**（6 位数字，约 5 分钟过期、只能被领取一次）和一条启动命令，
   点 **复制命令** 一并拿走（加入码与之后的凭据不要提交到仓库）：

   ![复制一次性加入码与启动命令](images/common/step-4-add-pilot.png)

3. 到 **Robot 主机**上执行这条命令（前台常驻；`<robot-id>` 换成实际机器人）：

   ```bash
   semantic-robot-instance start --config /etc/semantic/robots/<robot-id>/robot-deployment.yaml --join-code <加入码>
   ```

   启动器会通过局域网发现 Server（mDNS 服务名 `_semantic-server._tcp`；容器网络里 mDNS 常不可用，
   可显式追加 `--server-http http://<server>:<server-http-端口> --server-ws ws://<server>:<server-ws-端口>/ws/pilot`，
   端口见对应手册的端口表），用加入码换取该 Pilot 的专用凭据并存到 Robot 主机本地（实例目录的
   `connection.yaml`，权限 `0600`），再依次拉起 **AbilityFramework → 七类 Ability → Pilot**，最后由 Server
   对账并下发期望的 Robot Skill。

4. 回到对话框点 **完成**——它只是关窗，配对在启动器领取加入码那一刻就完成了；稍等片刻，机器人应出现在设备列表里、
   连接状态 **在线**。

之后重启机器人**不再需要加入码**（凭据已存在机器人主机本地）：

```bash
semantic-robot-instance start --config /etc/semantic/robots/<robot-id>/robot-deployment.yaml
```

> **Pilot 在线 ≠ 机器人可执行。** 若显示 Pilot 在线但 Robot 不可执行，继续查 AbilityFramework、七类 Ability、
> Robot Skill 的期望/实际状态与 Project 占用，不要只看 Pilot 心跳。

## 目录约定（新增场景时）

一个扩展场景就是 `extensions/<id>/` 一个目录，随仓库版本化：

```text
extensions/<id>/extension.json     # 清单源文件，安装器直接解析（产物、落点、顺序、许可、前置）
extensions/<id>/README.md          # 用户操作手册（英文）
extensions/<id>/README.zh-CN.md    # 用户操作手册（简体中文）
extensions/images/<id>/*.png       # 手册里的截图
```

`extension.json` 决定「装哪些产物、装到哪、按什么顺序、需要什么前置」；手册负责「人要先做什么、
怎么在 Web 上验收」。新增场景时照这两份文件的形状补齐即可，安装侧不需要改代码——
`semanticctl extension` 按 id 读取清单，通道布局与校验纪律对每个场景一致。

> **改字段前先读 [`../docs/extensions.md`](../docs/extensions.md)**：清单约束不是风格偏好，
> `semanticctl extension verify` 会按它逐字节校验（SHA-256、大小、包内文件集合）。
> 发布流程（`build_extension.py` / `publish_extension.py`、`repo-versions.json` 的 `extensions` 段、
> OSS mutable 白名单）也记在该文。

## 许可

LIBERO 与 BEHAVIOR / OmniGibson 都是上游第三方资产，已获授权在本通道内分发。数据集只按上游许可
（**仅限非商业学术研究**）由使用方单独取得，不随本通道分发；不要因为「能下载」就默认可再分发。
逐场景的许可声明见各手册的「许可」一节。
