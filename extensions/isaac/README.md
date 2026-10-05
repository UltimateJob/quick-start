# BEHAVIOR (Isaac Sim) extension scenario — user manual

**English** | [简体中文](README.zh-CN.md)

BEHAVIOR is an embodied manipulation scenario built on Isaac Sim 5.1 / OmniGibson 3.9.2, with an
R1 Pro robot and the π0.5 policy. Unlike LIBERO it has **three prerequisites that no package can
carry**, and the user must prepare them or the scene will not start and the robot will not come
online:

| Prerequisite | Why it cannot ship | Who provides it |
|---|---|---|
| Engine image `behavior:v3.9.2` (31.1 GB) | it lives in the local Docker image store; the runtime consumes it via `docker run` | you (import or build) |
| Licensed dataset (29.3 GiB compressed / 32.4 GiB unpacked and up) | upstream third-party asset, non-commercial academic research only, not redistributed here | you (from the upstream channel) |
| π0.5 policy service (separate GPU process) | it is a separate inference service; it goes into neither the Isaac image nor the ability/Pilot environment | you (OpenPI plus the official radio weights) |
| LLM endpoint and key | required for Agent dialogue; the key ships in no package | you (into the Server `.env`) |

The installer's `prerequisites` only **probe** (a failure warns but does not block) and `post_install`
only **reminds**; the real preparation is in this manual, along one path:

```text
① Environment preparation → ② Install into the framework → ③ Reproduce in the web Studio
```

---

## 0. Order and overview

```text
① Hardware/dependency self-check (GPU, VRAM, disk, Docker, network, ports)
② Fetch the licensed dataset        → get the directory that --asset-root points at
③ Import/build the engine image     → behavior:v3.9.2 exists in the local Docker store
④ Prepare and start the π0.5 policy service → LISTEN on 20080 (★ must precede the four robot artifacts)
⑤ Configure the LLM key             → semantic-framework/.env
⑥ One-shot extension install        → install.sh --extension isaac
⑦ Post-install binding and acceptance → add the scene, bind ability/model, add a Pilot
```

Two ordering traps are easy to hit:

1. **Start π0.5 (step ④) before the four robot artifacts.** On startup the VLA ability connects to
   the policy service for one action-free warm-up; if it cannot connect it is never ready, and the
   four artifacts are unverifiable even after installation.
2. **Dataset unpack disk peak.** The main archive and its unpacked result occupy disk at the same
   time; `/tmp` plus the `--asset-root` volume need **≥ 70 GiB free** combined. Delete the archive
   after a successful unpack.

---

## 1. Environment preparation

### 1.1 Hardware and system prerequisites

| Item | Requirement | Symptom when missing |
|---|---|---|
| GPU | NVIDIA, discrete; **π0.5 needs ≥ 24 GB class VRAM**, the Isaac scene itself takes about 4.9 GB | π0.5 runs out of memory restoring weights |
| VRAM (previews only) | previews need ≥ 6144 MiB free; a 6 GB card can start a scene but previews always fail | preview reports insufficient VRAM; the installer skips previews automatically when free VRAM < 6144 MiB |
| Disk | ≥ 50 GiB free on the `--asset-root` and image-cache volume (dataset unpack peak needs ≥ 70 GiB more) | runtime reports "disk below 50 GiB, pausing Isaac start" |
| Docker | GPU-capable (`nvidia-container-toolkit`), can `docker run --gpus all` | containers do not start |
| Network | building the image needs `nvcr.io`, `repo.anaconda.com`, `developer.download.nvidia.com`, `pypi.org`, `pypi.nvidia.com`; dataset/weights per section below | build/download failures |
| Ports | see section 4 | port conflicts |

One-shot self-check:

```bash
nvidia-smi --query-gpu=index,memory.used,memory.free --format=csv   # pick a free card; previews need free >= 6144
docker info >/dev/null && echo "docker ok"
df -h /tmp .
```

### 1.2 Step 1: fetch the licensed dataset

The directory `--asset-root` points at must **contain** `2026-challenge-task-instances/` (i.e. point
at its parent). The dataset licence is **non-commercial academic research only**; fetching
`omnigibson.key` means accepting it.

**Three small packages (direct download is fine)**:

```bash
HF=https://hf-mirror.com/datasets/behavior-1k/zipped-datasets/resolve/main
export BEHAVIOR_DATA=/path/to/datasets        # the value of --asset-root at install time
mkdir -p "$BEHAVIOR_DATA"

curl -L --progress-bar -o /tmp/2026-challenge-task-instances.zip "$HF/2026-challenge-task-instances.zip"  # ~104 MB
curl -L --progress-bar -o /tmp/omnigibson-robot-assets-3.8.2.zip "$HF/omnigibson-robot-assets-3.8.2.zip"  # ~641 MB
unzip -q /tmp/2026-challenge-task-instances.zip -d "$BEHAVIOR_DATA/2026-challenge-task-instances"
unzip -q /tmp/omnigibson-robot-assets-3.8.2.zip -d "$BEHAVIOR_DATA/omnigibson-robot-assets"
curl -L --progress-bar -o "$BEHAVIOR_DATA/omnigibson.key" \
  https://storage.googleapis.com/gibson_scenes/omnigibson.key   # 44 B decryption key
```

**Main asset (29.3 GiB compressed, slow)**: first confirm `/tmp` and the `$BEHAVIOR_DATA` volume have
≥ 70 GiB free combined.

```bash
# either one; both resume
curl -L -C - --progress-bar -o /tmp/behavior-1k-assets.zip "$HF/behavior-1k-assets-3.9.0.zip"
aria2c -x8 -s8 -k1M -c -d /tmp -o behavior-1k-assets.zip "$HF/behavior-1k-assets-3.9.0.zip"   # multi-connection, faster
unzip -q /tmp/behavior-1k-assets.zip -d "$BEHAVIOR_DATA/behavior-1k-assets"
```

> For a progress bar use `-L --progress-bar` and **do not add `-s`** — `-s` silences the bar along
> with everything else, so a tens-of-gigabytes download looks stuck. If it drops, re-run the same
> command to resume. After a clean unpack you can delete `/tmp/behavior-1k-assets.zip` to reclaim
> 29.3 GiB.

**Verify**:

```bash
cat  "$BEHAVIOR_DATA/behavior-1k-assets/VERSION"                                     # expect 3.9.0
test -f "$BEHAVIOR_DATA/2026-challenge-task-instances/metadata/available_tasks.yaml" && echo "task metadata ready"
test -f "$BEHAVIOR_DATA/omnigibson.key"                                              && echo "decryption key ready"
```

### 1.3 Step 2: engine image `behavior:v3.9.2`

The runtime runs it by **full digest** (the `image` field of `runtime-settings.json`, pinned to
`sha256:fd750409…` for packages published on this channel) and **will not pull it for you**. The image
matching that digest must already exist in the local Docker store.

#### Option A: import the maintainer-provided archive (recommended, same digest)

```bash
docker load -i behavior-v3.9.2.tar            # archive provided by the distributor
docker image inspect behavior:v3.9.2 --format '{{.Id}}'
# expected: sha256:fd75040906f3270dc2e79aa306847c5be39b7ae20c4cbd4d219d5625afc6caa7
```

#### Option B: build from upstream sources

Upstream `BEHAVIOR-1K`'s `docker/Dockerfile` is the only build input. Note that **a self-built image
always has a different digest** (see "pinning identity").

```bash
export BEHAVIOR_ROOT=/path/to/BEHAVIOR-1K
git clone --depth 1 --branch v3.9.2 https://github.com/StanfordVL/BEHAVIOR-1K.git "$BEHAVIOR_ROOT"
git -C "$BEHAVIOR_ROOT" describe --tags                       # expect v3.9.2

cd "$BEHAVIOR_ROOT"
docker build -f docker/Dockerfile -t behavior:v3.9.2 .        # do not add --progress=plain
docker image inspect behavior:v3.9.2 --format '{{.Id}}'       # note the local digest
```

- The build context is that source tree; the repository's `.dockerignore` already excludes `datasets/*`
  and `.git`, so unpacking the dataset under it does not affect the build.
- It pulls more than ten GB of Isaac Sim 5.1 pip packages and compiles curobo; normally about half an
  hour, hours on a slow link.
- Clone the engine source to `$BEHAVIOR_ROOT` **before** unpacking the dataset to
  `$BEHAVIOR_ROOT/datasets`: the other order makes `git clone` fail because the target directory is not
  empty (workaround: rename the data directory away, clone, then move it back).

#### Pinning identity (required for self-built images)

Before starting, the runtime checks that the `image` in `runtime-settings.json` exists locally. A
self-built digest differs from the published fixed value, so the runtime cannot find the image at
startup. Write the local digest back into the `image` field of the runtime's `runtime-settings.json`
(that field is the only home of the digest), then reinstall or restart the runtime:

```bash
IMG=$(docker image inspect behavior:v3.9.2 --format '{{.Id}}')   # sha256:<64 hex>
echo "$IMG"
# edit runtime-settings.json in the unpacked runtime directory, set image to $IMG
# then reinstall the runtime (semanticctl runtime install ...) or restart it
```

> If your installer verifies that file and forbids in-place edits, use the "repackage the runtime"
> path instead: change `image` in the runtime source and **bump the version** (same name and version
> with different content is rejected by the installer). This is why option A is preferred.

**Verify**:

```bash
docker image inspect behavior:v3.9.2 --format '{{.Id}}'   # digest must match the image field in runtime-settings.json
```

### 1.4 Step 3: π0.5 policy service

The actual inference runs in a **separate GPU policy service** that you prepare, and it **must start
before the four robot artifacts**. The model component (`r1pro-radio-model-0.1.1`) only stores the
connection and mapping: `endpoint = ws://127.0.0.1:20080`, `actions_per_chunk = 16`.

| Item | Source | Key constraint |
|---|---|---|
| OpenPI environment | the fork `wensi-ai/openpi`, branch `behavior`, named by the official baselines | must be able to `import openpi.configs.tasks`, `openpi.serving.websocket_b1k_server`, `openpi.shared.eval_b1k_wrapper`; upstream `Physical-Intelligence/openpi` raises ImportError |
| π0.5 weights | row `turning_on_radio` in the "Provided checkpoints" table of `docs/challenge/baselines.md` in the BEHAVIOR-1K repository (Google Drive file id `1KojwNUz0HVwU3Ww2SVh3NKt-4asuI3y2`) | must contain `params/` and `assets/turning_on_radio/norm_stats.json`; `pi05_base` alone is not the same model |
| Launcher scripts | provided by the R1 Pro **BEHAVIOR ability** source: `scripts/serve_behavior_policy.py`, `scripts/behavior_policy_chunk.py` | not part of the six extension artifacts; get them from the same channel as that ability source |
| GPU | a separate process running alongside Isaac | π0.5 is about 3B parameters and needs ≥ 24 GB class VRAM |

```bash
export OPENPI_ROOT=/path/to/openpi
export PI05_CHECKPOINT=/path/to/pi05_turn_on_the_radio
mkdir -p "$(dirname "$OPENPI_ROOT")" "$(dirname "$PI05_CHECKPOINT")"

# 1) OpenPI source (must be the fork and branch named by the baselines)
git clone --branch behavior https://github.com/wensi-ai/openpi.git "$OPENPI_ROOT"
git -C "$OPENPI_ROOT" submodule update --init --recursive

# 2) separate uv environment (GIT_LFS_SKIP_SMUDGE=1 is required)
cd "$OPENPI_ROOT"
GIT_LFS_SKIP_SMUDGE=1 uv sync
source .venv/bin/activate
GIT_LFS_SKIP_SMUDGE=1 uv pip install -e .

# 3) fetch weights (Google Drive id above)
#    drive.google.com is often unreachable from mainland China; either:
#    A) use a proxy
uvx gdown --proxy http://<your-proxy> 1KojwNUz0HVwU3Ww2SVh3NKt-4asuI3y2 -O /tmp/pi05_turn_on_the_radio.zip
unzip -q /tmp/pi05_turn_on_the_radio.zip -d "$PI05_CHECKPOINT"
#    B) reuse a copy already downloaded on this host/LAN (inference only needs params/ and assets/)
#       find / -maxdepth 8 -type d -name "pi05_turn_on_the_radio" 2>/dev/null

# 4) verify
ls "$PI05_CHECKPOINT" | tr '\n' ' '; echo            # expect params and assets directly
test -f "$PI05_CHECKPOINT/assets/turning_on_radio/norm_stats.json" && echo "weights complete"

# 5) start (separate, long-lived terminal; must run inside the OpenPI environment)
nvidia-smi --query-gpu=index,memory.free --format=csv          # pick a free card first, e.g. index 3
cd "$OPENPI_ROOT"
CUDA_VISIBLE_DEVICES=3 \
XLA_PYTHON_CLIENT_PREALLOCATE=false XLA_PYTHON_CLIENT_MEM_FRACTION=0.3 \
  .venv/bin/python /path/to/r1pro-ability/scripts/serve_behavior_policy.py \
  --checkpoint "$PI05_CHECKPOINT" --action-horizon 16 --port 20080

ss -ltnp | grep ':20080'                             # LISTEN means it is up
```

Key points:

- `--action-horizon 16` must match the model configuration's `actions_per_chunk: 16`, and `--port`
  must match the model configuration's `endpoint` (both `20080`). Changing only one side looks like
  "the service listens on 20080 but the ability connects to 18080" and the robot is never ready.
- **Pin one free card explicitly**: `CUDA_VISIBLE_DEVICES` overrides the inherited value; `pi05_b1k`
  has `fsdp_devices=1`, so each visible card gets a full model copy and one busy visible card causes a
  global OOM.
- If the same service is already running, reuse it; do not start a second one.
- **A 6 GB card cannot run this step**: the Isaac scene already takes about 4.9 GB and the π0.5
  weights exceed 6 GB — a hardware limit, not a configuration issue.

### 1.5 Step 4: LLM key

Scene browsing and bringing the robot online do not need an LLM; driving the Agent through dialogue
does. Keys are named per "service" and written to the Server working directory's `.env` (loaded at
startup, the log prints `.env 已加载`):

```bash
# semantic-framework/.env — key rule: SEMANTIC_LLM_API_KEY_<NAME UPPERCASE, '-' to '_'>
SEMANTIC_LLM_API_KEY_DEEPSEEK_CHAT=<real key>
```

`.env` is not versioned and keys are copied into no component package or Bundle, so a new machine must
be configured again. Without a key only the `mock` endpoint is available, and mock only proves the
plumbing works — it is not task acceptance.

---

## 2. Install into the framework

Same entry script as the base install; it continues into the extension once the base environment is
ready:

```bash
curl -fsSL https://semantic.insightos.cn/install.sh | bash -s -- \
  --extension isaac --extension-project <PROJECT-ID> \
  --extension-asset-root /path/to/datasets --install-system-deps
```

| Flag | Purpose |
|---|---|
| `--extension isaac` | select the scenario (required) |
| `--extension-asset-root <abs-path>` | a **hard requirement** of the BEHAVIOR runtime: the `$BEHAVIOR_DATA` from 1.2, whose parent contains `2026-challenge-task-instances/` |
| `--extension-project <PROJECT-ID>` | target project; defaults to the current user's Default Project |
| `--extension-source oss\|github` | channel, default `oss`; all six BEHAVIOR artifacts are below 2 GiB, so the GitHub channel mirrors fully |
| `--extension-package-dir <dir>` | install **fully offline** from the six artifacts plus the manifest |
| `--extension-dry-run` | print the command plan without changing anything |
| `--no-previews` | skip preview generation (for `semanticctl extension install`); via `install.sh`, previews are skipped automatically when free VRAM < 6144 MiB |

- Confirm the image from 1.3 and the policy service from 1.4 are ready first; a `probe` failure warns
  but does not block.
- The extension runtime pack's declared `license` is added from the manifest
  (`--accept-license behavior-assets`).
- Fixed order: runtime → scene catalog → robot base → ability → model → skill.

With the base environment already installed:

```bash
semanticctl extension install isaac --project <PROJECT-ID> --asset-root /path/to/datasets
```

> If `semanticctl` is not on your PATH, first `export PATH="$HOME/.local/share/semantic/bin:$PATH"`
> (use your actual dir when you passed `--dir`); the base install prints these two lines and tells you
> to persist them. See the entry point.

---

## 3. Reproduce in the web Studio

Sign in to the web Studio as `admin` (default `http://127.0.0.1:3000`) and open the target project.
Three things must be done in the web UI (the same as LIBERO), or the scene never enters the project and
the robot never comes online.

### 3.1 Scene configuration → add a compatible scene

Installation only registers the scene in the **scene catalog**; it does not add it to the project. In
Studio, open **Scene → Project scenes** and click **Add** (or **Browse scenes** when the panel is
empty):

![Click Add / Browse scenes in the project scenes panel](../images/isaac/step-1-scene-panel.png)

In the **Add compatible scene** dialog, click a scene card (recommended: `turning on radio`), then
**Add to Project**:

![Select a scene card and Add to Project](../images/isaac/step-2-add-scene.png)

After adding, the scene panel shows the runtime as `BEHAVIOR / OmniGibson` and the initial states of
`turning on radio`:

![The BEHAVIOR scene running in Studio](../images/isaac/overview.png)

**Done when**: the scene is listed under **Project scenes** with runtime `BEHAVIOR / OmniGibson`.

### 3.2 Project content → bind the ability and model

Installation **imports** the ability and model into the project but **does not bind them to the
robot**. Without binding, the ability stays in `Standby` (`abilityPort: 0`) until it times out, the
Pilot stays `offline`, and the device page shows no executable robot.

1. In Studio, open **Project → Import project content** and scroll the dialog to the **Robot and
   model configuration** section at the bottom:

   ![Robot and model configuration in Import project content](../images/common/step-2-bind.png)

2. On the `r1pro` card, click **Select ability / model** (to make the current choice the default for
   future robots instead, click **Set project default** in the top right);
3. In the dialog choose, in order, **robot model** `r1pro` → **ability (one implementation per
   role)** → **policy model** (`0.1.1`, i.e. `r1pro-radio-model-0.1.1`), then click **Save binding**;
4. Back on that robot's card, click **Apply now / retry** — this **stops and restarts that robot's
   components once** (the scene keeps its current state), so confirm the robot is idle first.

**Done when**: the card's "pending configuration" and "running model" agree and it no longer sits in
`Standby`. A project default only applies to **future first-time bindings**; each robot's own choice
is stored independently.

> **π0.5 must be up first.** On startup the policy ability connects to `ws://127.0.0.1:20080` for one
> action-free warm-up (see 1.4); if it cannot connect it is never ready, so even a correct binding
> here leaves the robot offline.

### 3.3 Device centre → add a Pilot

**Device centre** is the global view of robots, and a fresh environment has an empty device list.
Note that **"Add Pilot" does not add a robot directly**: it only mints a one-time join code, and the
robot is registered only after you run the launcher on the **robot host** and the launcher exchanges
that code for a credential.

1. Open **Device centre** from the top menu and click **Add Pilot**:

   ![Click Add Pilot in the device centre](../images/common/step-3-devices.png)

2. The dialog shows a **one-time join code** (6 digits, valid about 5 minutes, claimable only once)
   and a launcher command; click **Copy command** to take both:

   ![Copy the one-time join code and launcher command](../images/common/step-4-add-pilot.png)

3. On the **robot host**, run that command in the foreground and keep it running (replace
   `<robot-id>` with the actual robot):

   ```bash
   semantic-robot-instance start --config /etc/semantic/robots/<robot-id>/robot-deployment.yaml --join-code <JOIN-CODE>
   ```

   The launcher discovers the Server over the LAN (mDNS service `_semantic-server._tcp`; mDNS is
   often unavailable on container networks, so you may append
   `--server-http http://<server>:8034 --server-ws ws://<server>:8035/ws/pilot`), exchanges the join
   code for that Pilot's dedicated credential and stores it on the robot host (in the instance
   directory's `connection.yaml`, mode `0600`), then starts **AbilityFramework → the seven ability
   classes → Pilot** in order, after which the Server reconciles and dispatches the expected robot
   skill.

4. Back in the dialog, click **Done** — it only closes the dialog; pairing completed the moment the
   launcher claimed the join code. After a moment the robot should appear in the device list with
   connection **online**.

Restarting the robot afterwards **no longer needs a join code** (the credential is already on the
robot host):

```bash
semantic-robot-instance start --config /etc/semantic/robots/<robot-id>/robot-deployment.yaml
```

> **Two Server settings** (`semantic-framework/.output/configs/semantic-server.yaml`, restart after
> editing): `robot_runtime.enabled: true` — otherwise the device page always shows "this project has no
> connected Robot"; and `robot_runtime.data_root` / `bundles_dir` must be **absolute paths** — they are
> copied verbatim into install receipts and venv forwarder scripts, and relative paths keep the managed
> robot from starting.

### 3.4 Acceptance

1. the scene is under **Project scenes**, `turning on radio` has selectable initial states and starts;
2. the robot appears in **Device centre** with connection **online** and a status other than `degraded`;
3. drive the Agent through **dialogue** to run the radio task (needs the LLM key from 1.5).

---

## 4. Port table (defaults on a new machine never conflict; nothing needs changing)

| Purpose | Default | Decided by |
|---|---|---|
| Server HTTP / WS | `8034` / `8035` | `http_addr` / `ws_addr` in `semantic-server.yaml` (prebuilt-install defaults) |
| Web front end | `3000` | `semantic-web/vite.config.js` |
| BEHAVIOR runtime | `18090` | `install.sh --extension` (manifest `runtime.endpoint`) |
| Ability range | `18100–18199` | `ability_port_first` / `ability_port_last` in `semantic-server.yaml` |
| π0.5 policy service | `20080` | the `--port` from 1.4, which must equal the model configuration's `endpoint` |
| LIBERO runtime | `8092` | LIBERO manifest (can coexist with BEHAVIOR) |

When BEHAVIOR and LIBERO run on one host, both default to `18100–18199`; give each environment its own
range or you will see `http server bind ... failed`.

---

## 5. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Runtime install failed: Runtime Pack requires content behavior_data, provide a path at install time` | almost always an empty `--extension-asset-root` (the variable was not exported), not a broken package |
| `docker: Error response from daemon: No such image: sha256:fd750409…` | the digest is not in the local store, see 1.3 |
| `Runtime … still has an active scene, stop the scene first` | the runtime port is held by another checkout; change `--endpoint` or stop that scene |
| Preview reports insufficient VRAM / `ran out of memory ... requested by op` | previews need ≥ 6144 MiB free; policy-service OOM is usually a busy visible card, pin a free one per 1.4 |
| Disk below 50 GiB, Isaac start paused | clear the image cache or the `--asset-root` volume, keep ≥ 50 GiB |
| The robot stays `offline` / the ability stays `Standby` | π0.5 was not started first, or the port / `--action-horizon` disagrees with the model configuration, or the ability/model were not bound |
| The project does not show the scene | the compatible scene was never added |

---

## 6. Uninstall

Stop the scene and the robot first, then remove the extension. The base environment's native-mujoco
runtime is unaffected:

```bash
semanticctl extension remove isaac
```

---

## Reference

### The six artifacts and installation order

Fixed order: **runtime → scene catalog → robot base → ability → model → skill**. The robot base
(Bundle) is the foundation; the last three plug into it, so the reverse order does not work.

| Role | Artifact | Size | Channel |
|---|---|---|---|
| `runtime` | `behavior-runtime-0.1.18.zip` | about 23 MB | OSS + GitHub |
| `scene_catalog` | `behavior-scenes-3.9.2.zip` | about 1.3 KB | OSS + GitHub |
| `robot_base` | `r1pro-behavior-robot-0.1.1.zip` | about 52 MB | OSS + GitHub |
| `robot_ability` | `r1pro-behavior-ability-0.1.3.zip` | about 24 MB | OSS + GitHub |
| `model` | `r1pro-radio-model-0.1.1.zip` | about 1.2 KB | OSS + GitHub |
| `robot_skill` | `vla-manipulation-0.1.10.zip` | about 12 KB | OSS + GitHub |

The runtime `installation_id` is `local-behavior-omnigibson` with endpoint `18090` — different from
LIBERO's `local-libero-robosuite-1.4` / `8092` and the base environment's `native-mujoco` / `8090`, so
they can coexist.

> **The model package must be repacked as 0.1.1 first.** The source file's endpoint is
> `ws://127.0.0.1:18080`; change it to `ws://127.0.0.1:20080`, bump the version, and repack (same name
> and version with different content is rejected by the installer). The manifest registers the repacked
> `0.1.1`.

### License

BEHAVIOR / OmniGibson and the licensed dataset are upstream third-party assets redistributed through
this channel under authorization. Both the manifest `license` and the runtime pack `license` are
`behavior-assets`, so the installer adds `--accept-license behavior-assets` automatically. The dataset
is obtained separately by the user under the upstream license (**non-commercial academic research
only**) and is not redistributed here.

### Design

How `prerequisites` / `post_install` / `host_requirements` / `ports` are expressed, plus the channel
layout and release flow, are in [`../../docs/extensions.md`](../../docs/extensions.md); the entry point
and directory convention are in [`../README.md`](../README.md).
