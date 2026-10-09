# Semantic Installer (TUI)

[English](semantic-installer-README.md) | [简体中文](semantic-installer-README.zh-CN.md)

A terminal-interactive installer converted from "新版Semantic安装步骤.pdf" (Ubuntu from 0 to 1):
a stage/step tree on the left, a live log in the middle, configurable environment variables, and stage-by-stage step execution.

**Zero dependencies** — only the Python 3 standard library (`curses`).

## Launch

```bash
python3 semantic_installer.py            # TUI mode
python3 semantic_installer.py --list     # only list all stages and steps
python3 semantic_installer.py --run-all  # headless mode, run everything in order
python3 semantic_installer.py --stage 1 --stage 2   # headless mode, run the given stages
python3 semantic_installer.py --reset-status        # clear step status
```

## UI and keys

```
┌ Left: stage/step tree ──┬ Middle: live log ─────────────────────┐
│ 1 System deps 0/6 ·     │ 14:32:01 $ sudo apt update            │
│   1.1 · Basic tools     │ ...                                   │
└─────────────────────────┴───────────────────────────────────────┘
```

| Key | Action |
|---|---|
| `↑/↓` `j/k` | Move selection |
| `Enter` | Run: on a **stage** = run the whole stage in order; on a **step** = run that single step (force-run, skipping the skip check) |
| `a` | Run everything continuously from stage 1 (respects skip checks; manual steps are skipped) |
| `A` | Run continuously from the current selection to the end |
| `v` | Run only the verification command of the current stage/step |
| `e` | **Environment variable settings** (see below); saves and generates `semantic-env.sh` |
| `L` | View the log tail of the selected service step |
| `x` | Stop all background services started by this tool |
| `m` | Mark the manual step (7.1) done / undone |
| `c` / `C` | Abort the current run / clear the log |
| `r` | Reset all step status |
| `Tab` | Switch focus between the step tree and the log; with log focus, `PgUp/PgDn/Home/End` scroll |
| `?` | Help (includes a summary of pitfalls from the original document) |
| `q` | Quit (asks whether to stop background services) |

## Configurable environment variables (e key)

| Group | Variables |
|---|---|
| Paths and remote | `SEMANTIC` (working root), `GITLAB` |
| Versions | `GO_VERSION`, `BUNDLE_VER` (r1pro-mujoco Bundle version) |
| Mirrors and secrets | `UV_DEFAULT_INDEX` (PyPI mirror), `SEMANTIC_ADMIN_PASSWORD` |
| China mirrors | `APT_MIRROR`, `GO_DL_MIRROR`, `GO_PROXY`, `NODE_MIRROR`, `NODE_VERSION`, `NPM_REGISTRY`, `GITHUB_PROXY` (see below; **leaving all empty means direct connections**) |
| Render backend | `SEMANTIC_MUJOCO_GL` (`egl` default / `osmesa`) |
| Service addresses | `SERVER_HTTP`, `SERVER_WS`, `WEB_URL`, `ABILITY_PORT_FIRST/LAST`, `READINESS_TIMEOUT` |
| Repository branches | Integration branch names for 11 repositories (3 additional ability-framework repositories are pinned to the version manifest and not open for setting) |
| Extension Scenes (stage 8) | `EXTENSION` (`none` default / `libero` / `isaac`), `LIBERO_*` / `ISAAC_*` setting groups, `HF_ENDPOINT`, `GPU_MODE`, `CPU_ACTIONS_PER_CHUNK`, `CPU_THREADS` |

Saved to `installer-settings.json`; also generates `semantic-env.sh`, which can be sourced in any terminal with `source semantic-env.sh`.

## China mirror support (automatic download and installation of dependencies)

| Step | Default China mirror | Installer step |
|---|---|---|
| apt sources | `https://mirrors.aliyun.com/ubuntu` (can switch to Tsinghua `https://mirrors.tuna.tsinghua.edu.cn/ubuntu`) | 1.0 automatically replaces `archive/security.ubuntu.com`, keeping a `.bak-orig` backup of each source file |
| Go official tarball | `https://mirrors.aliyun.com/golang` (or `https://golang.google.cn/dl`) | 1.2 downloads the tarball from the mirror |
| Go modules | `GOPROXY=https://goproxy.cn,direct` | 1.6 persists via `go env -w` + injects into `make build` |
| Node.js | `https://cdn.npmmirror.com/binaries/node` binaries | 1.3 downloads and extracts to `/usr/local` (default 22.14.0; empty `NODE_VERSION` auto-resolves latest-v22.x; empty `NODE_MIRROR` falls back to NodeSource) |
| npm registry | `https://registry.npmmirror.com` | 1.6 writes to `~/.npmrc`; 6.2 `npm ci --registry` as a second safeguard |
| uv installation | astral.sh → `GITHUB_PROXY` proxy → pip China mirror | 1.4 three-strategy automatic fallback; continues once any succeeds |
| Python interpreter (uv) | `UV_PYTHON_INSTALL_MIRROR` (derived from `GITHUB_PROXY`) | Injected at 1.4 / 4.1 / 5.3, speeds up `uv python install` and `uv sync` |
| PyPI (uv sync) | `UV_DEFAULT_INDEX` Aliyun (Tsinghua as backup) | 4.1 / 5.3 |

`GITHUB_PROXY` example: `https://mirror.ghproxy.com` (GitHub proxy prefix, used to speed up the uv binary and python-build-standalone interpreters; if the proxy domain stops working, switch to another or leave empty for a direct connection).


## Stage overview (corresponding to the PDF chapters)

1. **System dependencies**: apt China mirror / basic tools / Go>=1.23 (mirror) / Node 22 (mirror binary) / uv+Python3.13 (multi-strategy fallback) / EGL rendering libraries / mirror configuration (GOPROXY+npm) / version self-check
2. **Pull code and assets**: clone 14 repositories (including `franka-ability`; the local Deployment directory must be `semantic-robot-deployment`) / switch to integration branches / `git lfs pull` / directory check. The feature-line repositories cloned only when an extension is selected (`semantic-simulation/isaac-runtime`) are merged in when `EXTENSION=isaac`
3. **Build Server**: `.env` (admin password) / `make build` / `make init` / artifact check
4. **Register MuJoCo Runtime**: `uv sync` / `semantic runtime install` (automatically retries with `--replace` if it already exists)
5. **Robot execution stack**: `make setup/check` / Wheel cache check / `refresh_v050_mujoco.py build --activate --stop-users` (on rerun, first stop this workspace's Server and instances holding the old Bundle) / automatically adjust `.output` configuration (robot_runtime + leader allowlist)
6. **Startup**: Server (`make run` in background) / Web (`npm ci` + `.env` + `npm run dev` in background) / log in and publish the three Robot Skills; existing same-name services of this workspace are stopped first, then started
7. **Studio manual integration**: press Enter to show the 8-item manual checklist; mark done with `m` when finished
8. **Install extension Scenes** (optional, off by default, before the final "daily restart" step): set `EXTENSION=libero` (LIBERO) or `EXTENSION=isaac` (BEHAVIOR/Isaac) to enable. Prerequisite checks → log in to Server → pull upstream source → build and install Runtime → build the remaining five artifacts → install Scenes (limited preview rendering) → install the robot four-piece set → integration checklist
9. **Daily restart** (pinned at the bottom of the stage tree): first stop this workspace's already-running Server/Web, then bring them up in the background

### Stage 8: Install extension Scenes (LIBERO / BEHAVIOR)

Not executed by default (`EXTENSION=none`). LIBERO is an **optional** extension Scene that **coexists** with the base r1pro environment and changes nothing from the first 7 stages; it is placed before stage 9 "Daily restart", so you can continue straight down after installing.

**How to enable**: `e` → "Extension Scenes (stage 8)" group → set `EXTENSION` to `libero`.

Key settings:

| Variable | Default | Description |
|---|---|---|
| `EXTENSION` | `none` | `none` installs nothing; `libero` enables LIBERO; `isaac` enables BEHAVIOR (Isaac Sim) |
| `LIBERO_LINE_BRANCH` | `feature/libero-behavior-vla` | libero feature-line branch. With `EXTENSION=libero`, the seven libero-line repositories (framework / web / deployment / franka-ability / mujoco-runtime / robot-sdk / robot-skill) all switch to this branch at stage 2.2, **taking priority over `repo-versions.json`** — the release Tags do not carry LIBERO scripts and Abilities, so checking out by Tag would leave pieces missing. Once each repo has merged the feature line into develop and pushed, this can be changed to `develop` |
| `ISAAC_LINE_BRANCH` | empty | BEHAVIOR (isaac) feature-line branch. Empty = switch per the **built-in per-repo table** (framework / robot-skill / deployment / robot-sdk / isaac-runtime on `feature/behavior-test`, web and r1pro-ability on `feature/behavior-isaac`, ability-runtime stays on `develop`); if set, it **uniformly overrides** every repository in ISAAC_REPOS. Once the repos merge back to the main branch, set `develop`/`main` to converge. Like LIBERO, it **takes priority over `repo-versions.json`** |
| `LIBERO_PACKAGE_DIR` | empty | Directory for the six artifacts; empty = `<framework>/.output/packages/libero-current` (about 10.4 GB) |
| `LIBERO_RUNTIME_ID` | `local-libero-robosuite-1.4` | Runtime installation ID; must match the project runtime-preference |
| `LIBERO_RUNTIME_VERSION` | `0.4.0-dev.0` | Determines the file name of artifact 1 |
| `LIBERO_SCENES` | `libero-spatial-0,libero-spatial-7` | Comma-separated; previews are generated only for these Scenes |
| `LIBERO_UPSTREAM_DIR` | empty | Upstream LIBERO source; empty = fetch per `sources.lock.yaml` and verify the commit |
| `LIBERO_PROJECT_ID` | empty | Target project for installation; empty = automatically use the development project |
| `LIBERO_ROBOT_ID` | empty | Managed Robot; empty = automatically pick one `franka_panda` |
| `HF_ENDPOINT` | `https://hf-mirror.com` | The official site is unreachable in China; use the mirror (only used when building the model package) |
| `GPU_MODE` | `auto` | `auto` decides from the machine's capability (GPU if CUDA is present, otherwise CPU with automatic tuning); `gpu` forces discrete-GPU installation; `cpu` forces CPU installation (useful for reproducing a no-GPU environment) |
| `CPU_ACTIONS_PER_CHUNK` | `10` | With CPU inference, execute the first N steps of one predicted chunk back-to-back to amortize per-inference cost. Empty = disabled (keeps the checkpoint's native 1). Not used on discrete-GPU hosts |
| `CPU_THREADS` | empty | **Override valve, normally left empty**. Empty = the Ability auto-detects from the machine topology + startup calibration (recommended); if set, pins the thread count and skips calibration (written to `SEMANTIC_VLA_THREADS`) — use only when the automatic result is unsuitable. Not used on discrete-GPU hosts |

**Why `LIBERO_SCENES` must be limited**: the Scene package contains **130 tasks / 6500 initial states**. Registration itself takes only 3 seconds, but every initial-state preview starts the Runtime, restores the initial state, runs 5 simulation steps, then renders — without a limit, all 6500 initial states would be rendered one by one, the slowest step of the whole pipeline.

**Reruns are safe and only fill in what is missing**: the five build steps (8.4/8.6/8.7/8.8/8.9) automatically skip when the artifact already exists in `LIBERO_PACKAGE_DIR`; 8.5 skips installation when a Runtime with the same ID is already registered and only runs `doctor` validation without overwriting. Steps 8.3 (fetch upstream source) and 8.10/8.11 (install) do not auto-skip; just rerun them normally (the installer itself deduplicates by version and digest).

**Installed does not mean usable**: stage 8.11 only completes the "install"; the final binding must be done in the Web UI — (1) "Add compatible scene" to add the Scenes to the project (installation only registers them into the scene catalog, they do not enter the project automatically); (2) "Robot and model configuration" to bind the Ability and model for `franka_panda`. **Without binding, the Ability stays in `Standby` (`abilityPort: 0`) until it times out, and the Robot stays `interrupted`**. Step 8.12 prints this checklist into the log.

**Machines without a discrete GPU (`GPU_MODE=auto` resolved to `cpu`, or forced `cpu`)**: the model package and binding **always declare `device=cuda`**, so the same package works on both GPU and GPU-less machines; at runtime the Ability converges according to the machine's capability and reports truthfully (`device: cuda` / `effective_device: cpu`) — this is not silent behavior.

CPU runtime cost is governed by three levers, none of which modifies the model:

- **Wait policy**: the framework unconditionally disables OpenMP spin-waiting when bringing up managed instances (`KMP_BLOCKTIME=0` / `OMP_WAIT_POLICY=PASSIVE`). This is the most effective one (about 3x in interleaved retests under same-machine reload), harmless on discrete-GPU machines, and values explicitly set by operations are not overridden.
- **Inference thread count**: the Ability detects the machine topology (P cores / E cores / low-power cores), subtracts the headroom reserved for co-located simulation and rendering, then fine-tunes with startup calibration; the result is reported with the binding summary as `cpu_threading`. Going past the fast-core count causes a 2–4x collapse, so convergence is mandatory; within the fast range the difference is only about 15%. **Default is `auto`** — pinning at install time breaks when the machine changes or co-located load changes, so the `CPU_THREADS` setting is only an override valve (stages 3.1 and 8.1 log the detected core count and the thread count that will be used; in the field you can also pin temporarily with `SEMANTIC_VLA_THREADS`).
- **Action-chunk amortization** (`CPU_ACTIONS_PER_CHUNK`, default 10): executes the first N steps of the same predicted chunk back-to-back, cutting each control step from about 2.5 s to sub-second. This changes control semantics (open-loop execution of N steps), so it is enabled only when CPU inference is detected; discrete-GPU hosts keep the checkpoint's native behavior.

The first cold load of the model takes several minutes; if it hits the readiness timeout, set `READINESS_TIMEOUT` to `8m`. Rendering via Mesa EGL works. Performance is noticeably slower than a discrete GPU — suitable for validation and debugging; **the default path is still designed for discrete GPUs**.

> Stage 8 is the **source-build** path, aimed at developers who need to change component versions. The extension Scenes of the precompiled entry point (`install.sh`)
> are a **sidecar** design (separate manifest + `semanticctl extension` + separate channel); see [docs/extensions.md](docs/extensions.md).
> So far only the read-only layer has landed (`extension list/show/verify`): it downloads the manifest and artifacts and verifies sha256 and size piece by piece,
> without installing anything. `install`/`remove` are not implemented yet; calling them fails with a clear error pointing to the design document.

## Behavior notes

- **Status persistence**: step status is stored in `installer-status.json`; reopening the program resumes the run.
- **Skip checks**: already-satisfied steps (e.g. Go already >= 1.23) are skipped automatically; pressing Enter on a single step force-runs it.
- **Prerequisite checks**: running stages 6/7/8/9 with unfinished preceding stages prompts for confirmation.
- **sudo**: when a password is needed, the tool temporarily switches to the real terminal (the TUI yields), returns after the password is entered, and the output still flows back into the log panel.
- **Background services**: Server/Web are started in independent process groups; logs are in `$SEMANTIC/.tui-logs/`; the step is marked done once the health check passes; `L` views logs at any time, `x` stops them.
- **Stop on failure**: after a step fails the queue is cleared; after fixing, rerun that step or the whole stage.
- Verification commands (`test -f ...` etc.) run automatically after the main command succeeds, and the result counts toward the step status (`!` warning / `✗` failure).

## GitLab credential helper (g key)

When clone/pull needs authentication, press `g` to open the credential helper; two ways to obtain and automatically save credentials:

| Method | Flow | Prerequisites |
|---|---|---|
| **OAuth login** (recommended) | First time: the TUI shows the form values to fill in (Name/Redirect URI/Scopes) → create the application in the browser → paste ID/Secret back in the TUI to save automatically → **immediately** jump to the authorization consent page → click "Authorize" once → token obtained automatically | None (guided through inside the TUI on first use) |
| **PAT paste** | Open the PAT creation page **pre-filled** with name+scopes → choose an expiry → click "Create" → click the page's "Copy" button → **the TUI reads the Token automatically from the clipboard** (needs one of wl-paste/xclip/xsel) → automatically saved and verified | None |

- The PAT/application page paths are **auto-detected** for both the old and new routes (`/-/profile/*` and GitLab 17+'s `/-/user_settings/*`); if the browser still 404s, the log provides a fallback URL and a parameter-free page, and you can also pin `PAT_PAGE_PATH` / `APPS_PAGE_PATH` in the settings

Notes:
- GitLab's OAuth authorization-code flow requires a "registered application" (this differs from Google: Google's applications are pre-registered by the developer and you only see the consent page). The first registration is guided by the TUI; **the application is not personal — a team can share the same ID/Secret** — the administrator registers once, and everyone else fills in the same pair to go straight to "one-click authorization".
- Every login after registration: `g` → `o` → click "Authorize" once in the browser → the callback obtains the token automatically, with no copy-pasting at all.

- The token is written to `git credential store` (scoped to that GitLab domain only, `~/.git-credentials`, permission 0600); afterwards all clone/pull/lfs are passwordless
- After saving, it is automatically verified with `git ls-remote`; `g → c` clears it at any time
- When a clone step hits an authentication failure (`could not read Username` / `Authentication failed` etc.), the log prompts you to press `g`

## sudo authentication (command-line style, no terminal switching)

sudo steps use **in-TUI authentication** by default: a masked password box pops up, and the password is passed to the child process from stdin via `sudo -S`;
it is kept only in this process's memory (never written to disk), **entered once and reused for the whole session**, and can be cleared at any time with the `P` key. On a wrong password it is cleared automatically and asked again on the next run.

- The `SUDO_AUTH` setting: `tui` (default, recommended) / `terminal` (temporarily exit curses to the real terminal to enter the password)
- Headless mode (`--run-all` etc.) automatically falls back to terminal mode
- Background scripts still run in independent process groups without occupying the controlling terminal, and logs go to the middle panel as usual

## Generated files

- `installer-settings.json` — environment variable settings
- `installer-status.json` — step status
- `semantic-env.sh` — environment script for terminals to source
- `$SEMANTIC/.tui-logs/{server,web}.log` — background service logs
