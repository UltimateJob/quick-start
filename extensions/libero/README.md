# LIBERO 扩展场景 — 清单与取得渠道

本目录是 LIBERO 扩展场景的**清单源文件**，随仓库版本化。安装本体（下载与校验、安装
编排）在 `artifacts/runtime/extension.py`，设计依据见 `../../docs/extensions.md`。

`extension.json` 由安装器直接解析。改字段前先读 `docs/extensions.md` 第一节：清单约束
不是风格偏好，`verify` 会按它逐字节校验。

## 发布流程（sha256 与 size 从哪来）

仓库里这份 `extension.json` 是**模板**：`sha256` 全是 `0`，`size` 是 2026-09 实测值。
发布真实产物时按下面三步回填，不要手填。

```bash
# 1. 在产物所在目录逐个计算
sha256sum semantic-libero-robosuite-1.4-*.runtime.tar.zst \
          libero-scenes.zip franka-libero-robot.zip franka-ability.zip \
          franka-smolvla-model.zip vla-manipulation.zip

# 2. 回填 extension.json 对应条目的 sha256 与 size（size 用字节数，不是 MiB）

# 3. 上传后核对一次，确认通道上的对象与清单一致
semanticctl extension verify libero
```

清单与产物一起升版本，版本号进 `repo-versions.json` 一并固化，便于复现。上传走
`artifacts/oss_client.py` 的既有通道，新增 `extensions/libero/<version>/` 前缀；
`stable.json` 指针是可变对象，已在 OSS mutable 白名单里。

## 六个产物与安装顺序

顺序固定：**Runtime → 场景 → 运行支持 → Ability → 模型 → Skill**。Bundle（运行支持）
是底座，后三者往它上面插，倒序装不上去。

| 角色 | 产物 | 体积 |
|---|---|---|
| `runtime` | `semantic-libero-robosuite-1.4-0.4.0-dev.0.runtime.tar.zst` | 约 1.8 GB |
| `scene_catalog` | `libero-scenes.zip` | 约 239 MB |
| `robot_base` | `franka-libero-robot.zip` | 约 2.7 GB |
| `robot_ability` | `franka-ability.zip` | 约 2.7 GB |
| `model` | `franka-smolvla-model.zip` | 约 3.2 GB |
| `robot_skill` | `vla-manipulation.zip` | 约 11 KB |

Runtime 的 `installation_id` 是 `local-libero-robosuite-1.4`，endpoint 固定 `8092`——
基础环境的 native-mujoco 用 `8090`，两者并存时不能复用。

## 许可

LIBERO 是上游第三方 benchmark（`github.com/Lifelong-Robot-Learning/LIBERO`）。清单
的 `license` 字段还是占位值，落地前必须填真实许可。装带 `license` 字段的扩展需要
`--accept-license <id>`，不要因为"能下载"就默认可再分发。

## 人工前置

清单 `prerequisites` 与 `post_install` 表达的是**装不进来、只能由人做**的部分：

- 模型权重走 HuggingFace 镜像（`HF_ENDPOINT=https://hf-mirror.com`，国内官网不可达）；
  代理与镜像二者取一即可。
- 场景落库只注册到场景目录，不会自动进项目，要手动「添加兼容场景」。
- 不绑定 Ability 与模型，Robot 起不来：Ability 停在 `Standby`（`abilityPort: 0`）直到
  超时，Pilot 一直 `offline`。
- Skill 带 `robot_required`，需要设备中心先有 Robot；全新环境要先「添加 Pilot」拿一次性
  加入码。

## 已验证的现场结论

2026-09 在核显机器（Intel 核显 / 30 GB 内存，无独显）上的完整实测记在 `../../NOTES.md`
的「LIBERO 扩展场景」一节，包括 CPU 推理调优与 heartbeat timeout 的性质。装之前值得先读。
