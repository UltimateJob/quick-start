# Extension Scene installation design (LIBERO / Isaac)

[English](extensions.md) | [简体中文](extensions.zh-CN.md)

This document answers one question: **the precompiled install entry point (`install.sh`) can currently only install the base environment — how should extension Scenes (LIBERO, and later Isaac) be installed?**

Companion reading: [Release CI](release-ci.md), [Artifact publishing and one-click deployment](../artifacts/README.md). For the source-build path (TUI stage 8) see `semantic-installer-README.md`.

---

## 1. Why they cannot simply be stuffed into the base artifact

The precompiled path is assembled from the component Releases by `artifacts/build_from_releases.py`. Three hard constraints first:

1. **`files.json` is an exact set, not a whitelist.** `verify_payload()` in `artifacts/runtime/installer.py`
   requires that "every listed file exists with a matching digest" **and** "the package contains no unlisted files".
   One extra file in the payload triggers `发布包存在未列入校验的文件` and the installation fails outright.
2. **The size differs by about 30x.** The base artifact is about **345 MiB** (measured `0.5.0-dev.20260910.3` = 362,387,241 B);
   LIBERO's six extension artifacts total about **11.5 GB** (Runtime 2.2G + Scene 239M + runtime support 2.9G
   + Ability 2.9G + model 3.3G + Skill 12K). Making people who do not install the extension pay that download is unacceptable.
3. **Building the extension artifacts depends on the company intranet and upstream third parties.** The LIBERO upstream is on GitHub (not the company GitLab),
   the Runtime needs a Python 3.8 profile, and the model package needs access to HuggingFace or a mirror. None of these can enter
   the static Release assembly pipeline.

**Conclusion**: extension Scenes must be **independent, verifiable sidecar artifacts**, pulled and installed on demand by the installer after the base environment is in place.
The base artifact stays lean and immutable.

### Existing pieces to reuse (these already exist — do not reinvent)

| Capability | Location | Notes |
|---|---|---|
| Component installation | `semantic install <package> --project <ID>` | Via the running Server's HTTP API; package types `scene_catalog` / `robot_base` / `robot_ability` / `model` / `robot_skill` |
| Runtime installation | `semantic install runtime --pack <file> --installation-id <ID> -c <config>` | **Executed locally**, does not go through the Server |
| Multi-component sets | `internal/install/package_set.go` | One zip + `semantic-package.yaml`, installed in topological order by `requires` |
| Management entry point | `install.sh` embeds `installer.py` / `install_support.py` / `uninstall.py` into `<instance>/bin/semantic-manager/` | Reused by `semanticctl` |
| Verification discipline | `digest()` + `verify_payload()` + safe archive unpacking | SHA256 and size verified on download; path traversal/links/duplicates rejected |

> **The `package` set cannot express a Runtime**: `InstallPackage()` explicitly rejects `runtime` and nested `package`
> ("Runtime 请独立安装，组件集合只支持一层"). So above the set package we still need one more manifest layer to describe
> the two landing sites: "local Runtime installation" and "Server component installation". That is this document's extension manifest.

---

## 2. Design: extension manifest + management subcommand + separate channel

Three layers, independent of each other, landable separately.

### Layer 1: the extension manifest `extension.json`

Small and standalone (KB-scale), published on the same channel as the base artifact, in per-id directories:

```text
<base-url>/extensions/index.json                      # catalog of known extensions (optional, for list)
<base-url>/extensions/libero/stable.json              # current stable version pointer (mutable object)
<base-url>/extensions/libero/0.1.0/extension.json     # manifest of that version (immutable, with sha256)
```

Manifest structure (example is LIBERO; `sha256` and `size` here are placeholders — actual values follow the
locally measured sizes in "LIBERO 打包与安装速查": Runtime 2.2 GB / Scene 239 MB / runtime support 2.9 GB / Ability 2.9 GB / model 3.3 GB / Skill 12 KB):

```json
{
  "schema_version": 1,
  "id": "libero",
  "title": "LIBERO 仿真场景 (robosuite 1.4 + Franka + SmolVLA)",
  "version": "0.1.0",
  "compatible_base": ">=0.5.0",
  "profile": "libero-robosuite-1.4",
  "runtime": {
    "installation_id": "local-libero-robosuite-1.4",
    "endpoint": "http://127.0.0.1:8092",
    "pack": { "url": ".../semantic-libero-robosuite-1.4-0.4.0-dev.0.runtime.tar.zst",
              "sha256": "…", "size": 1932735283 }
  },
  "components": [
    { "role": "scene_catalog", "id": "libero-scenes",   "url": "…/libero-scenes.zip",        "sha256": "…", "size": 250609664,
      "previews": { "default_scenes": ["libero-spatial-0", "libero-spatial-7"],
                    "note": "包内 130 任务 / 6500 初态；不限定 --scene 会对全部初态逐一出图" } },
    { "role": "robot_base",    "id": "franka-libero-robot", "url": "…/franka-libero-robot.zip", "sha256": "…", "size": 3113851289 },
    { "role": "robot_ability", "id": "franka-ability",      "url": "…/franka-ability.zip",      "sha256": "…", "size": 2899102924,
      "project_default": true },
    { "role": "model",         "id": "franka-smolvla-model","url": "…/franka-smolvla-model.zip","sha256": "…", "size": 3435973836,
      "project_default": true },
    { "role": "robot_skill",   "id": "vla-manipulation",    "url": "…/vla-manipulation.zip",    "sha256": "…", "size": 11264,
      "robot_required": true }
  ],
  "post_install": [
    { "kind": "user_action", "text": "场景配置 → 添加兼容场景：安装只把场景注册到 scene-catalogs，不会自动进项目" },
    { "kind": "user_action", "text": "项目内容 → 机器人与模型配置：为 franka_panda 绑定 Ability 与模型，否则 Ability 停在 Standby" }
  ]
}
```

Key points:

- **`role` determines the landing site**: `runtime` goes through the local CLI; the rest go through Server component installation. The order is fixed:
  Runtime → Scene → runtime support → Ability → model → Skill (the Bundle is the foundation; the latter three plug into it).
- **Every artifact carries `sha256` and `size`**, the same verification discipline as the base artifact — no weakening to "only a URL in the manifest".
- **`previews.default_scenes`** writes the "do not render previews for all 6500 initial states" advice into the manifest instead of relying on the user remembering.
- **`post_install`** expresses the parts that cannot be automated (binding, adding Scenes to the project), printed by the installer at the end.

### Layer 2: the management subcommand `semanticctl extension`

A new management module `artifacts/runtime/extension.py`, treated the same as the existing three modules:

- The embedded block of `install.sh` (`manager_shell()`, `artifacts/build_english_installer.py:69`) gains a fourth file;
  `build_installers.py --check` continues to enforce that the generated scripts stay in sync with the sources.
- Subcommands: `list` / `show <id>` / `verify <id>` / `install <id>` / `remove <id>`.
  `verify` only downloads and checks digests without installing — for troubleshooting and acceptance.
- The installation flow follows the manifest strictly:

```text
1. Resolve the channel (--base-url / --source oss|github / --package offline) to get extension.json
2. Verify sha256 + size per artifact
3. runtime:  <instance>/current/bin/semantic install runtime --pack <file> \
             --installation-id <runtime.installation_id> --endpoint <runtime.endpoint> \
             -c <instance>/configs/semantic-server.yaml        # executed locally, no Server needed
4. components: take the admin token (<instance>/configs/secrets.json, same source as publish()),
             upload via POST /api/v1/projects/<ID>/imports, then /imports/<id>/install
             passing InstallOptions (GeneratePreviews / SceneIDs / ProjectDefault / RobotID)
5. With no credentials or the Server not started, fail with the next step stated — never skip silently
6. Print the post_install checklist
```

- **Target Project**: specify explicitly with `--project <ID>`; by default take the user's Default Project (the one created by
  `EnsureDefaultProject` in the framework is `mode=development`, which happens to satisfy the component-installation requirement).
  **Component installation must land in a `mode=development` project** (`internal/bootstrap/component_install.go:233`);
  the installer needs to say so clearly in the log.
- **`--robot`**: passed automatically when the Skill has `robot_required` and a managed Robot has been discovered; otherwise only import and direct the user to
  "Add Pilot" in the Web device center.
- **`remove`**: stop the Scenes and Robot first, then `semantic runtime uninstall --id <ID>` and component uninstall;
  the base environment's native-mujoco Runtime is unaffected (`installation_id` and endpoint are independent).

### Layer 3: the release channel

- **Artifact storage**: reuse the existing channel, adding the immutable prefix `extensions/<id>/<version>/<artifact>`
  and the mutable channel pointer `extensions/<id>/stable.json`. On the OSS side the **mutable whitelist had to be relaxed** —
  `MUTABLE_PATTERNS` in `artifacts/oss_client.py` now allows updating `extensions/*/stable.json`
  (alongside `install.sh`, `channels/stable.json`, `channels/musl-stable.json`; the `semantic-managed=1` marker
  and ETag backup are still required — the rules are not loosened).
- **One manifest, two channels**: each artifact in the manifest records a **relative path** (bare file name); at install time it is joined per
  `--source oss|github` (default `oss`) into `<base>/extensions/<id>/<version>/<name>` or
  `https://github.com/<org>/quick-start/releases/download/ext-<id>-v<version>/<name>`. The manifest and
  `stable.json` are always fetched from OSS. A single GitHub Release asset has a **2 GiB hard limit**; over-limit artifacts are marked
  `hosts: ["oss"]` in the manifest (shorthand `github: false`), and on the GitHub channel the installer **automatically falls back to OSS**;
  `extension.GITHUB_ASSET_LIMIT` is the single source of truth for this rule.
- **Release tooling**: `artifacts/build_extension.py` backfills `sha256`/`size` per artifact, marks over-limit artifacts, writes out
  staging and `stable.json` and self-checks with `extension.parse`; `artifacts/publish_extension.py` first uploads the
  immutable prefix, promotes `stable.json` only after all checks pass, then creates the GitHub Release (including `SHA256SUMS` and
  `release.json`). CI: `.github/workflows/extension-release.yml`.
- **The manifest version travels with the repository**: the manifest source file lives at `extensions/<id>/extension.json`, its version number rising together with the artifacts;
  the extension version and GitHub tag are pinned in the `extensions` section of `repo-versions.json`; each artifact's real digest is pinned
  in the immutable `extensions/<id>/<version>/extension.json` on the channel, which is authoritative for reproduction.
- **Licenses**: LIBERO and BEHAVIOR are both upstream third-party assets, authorized for distribution on this channel; the template `license`
  is backfilled as `LIBERO` / `behavior-assets`. For extensions with a `license` field the installer requires
  `--accept-license <id>` (by default it auto-fills the value declared by the manifest), aligned with the existing `AcceptedLicenses` option.

---

## 3. The Isaac differences (why the manifest must be able to express "things a human must do")

> **Landed (2026-10).** The manifest and probe capabilities described in this section are implemented: `extensions/isaac/extension.json`
> expresses three `probe` entries via `prerequisites[].check` (image / disk / VRAM), and uses `user_action` for the dataset,
> the π0.5 service and the LLM key; `runtime.content` declares the hard `--asset-root` requirement; `runtime.pack.license`
> triggers `--accept-license behavior-assets`; `host_requirements.gpu=required` and
> `ports=[[18090,18090],[18100,18199],[20080,20080]]` have the installer check before installation. The TUI stage 8
> isaac source-build line (8.14–8.27) and the precompiled channel's `semanticctl extension install isaac` share this one manifest.
> The engine image and dataset are still not distributable; the manifest only registers and probes them.

BEHAVIOR/Isaac is not the same kind of deliverable as LIBERO; the following three items are **not downloadable artifacts**:

| Item | Size | Why it cannot be installed |
|---|---|---|
| Engine image `behavior:v3.9.2` | 31.1 GB | A local Docker image store, not delivered with any ZIP; the Runtime consumes it via `docker run` |
| Dataset | Tens of GB | Obtained separately via upstream channels; not a company artifact |
| π0.5 policy service | A standalone GPU service | Goes into neither the image nor the Pilot/Ability environment |

So the manifest needs a `prerequisites` section, both human-readable and machine-probeable:

```json
"prerequisites": [
  { "kind": "probe", "text": "本机已导入引擎镜像且 sha256 与 runtime-settings.json 一致",
    "check": "docker image inspect sha256:<ID>" },
  { "kind": "probe", "text": "asset-root 所在盘可用空间 >= 50 GiB",
    "check": "test -d \"{asset_root}\" && test \"$(df -B1G --output=avail \"{asset_root}\" 2>/dev/null | tail -1)\" -ge 50" },
  { "kind": "user_action", "text": "数据集需按上游说明单独取得" },
  { "kind": "user_action", "text": "π0.5 策略服务需自行准备（不进镜像与 Ability 环境）" }
]
```

`check` commands may contain `{asset_root}`: before running the probe, the installer substitutes it with the
`--asset-root` value of this installation (possible values in `extension.PROBE_VALUES`). If the manifest uses this placeholder
but the caller did not provide `--asset-root`, that probe is reported as `skip` (the literal `{asset_root}` is never run through a
shell, and it is not misreported as insufficient disk). Probe command values are supplied by the installer; the manifest must not carry host paths.

Two more things must be declared explicitly or the field will trip over them:

- **Port-range conflict**: the Isaac runtime occupies `18100` by default, overlapping LIBERO's Ability port range (`18100-18199`).
  The manifest should declare the required port ranges; the installer checks occupancy before allocation and gives adjustment suggestions
  (the existing `check_port()` and `ability_port_first/last` mechanisms can be reused).
- **GPU prerequisite**: Isaac requires a discrete GPU; LIBERO runs on integrated graphics but slowly (CPU inference has automatic thread tuning).
  The manifest uses `host_requirements.gpu` to distinguish "required / optional", letting the installer block before installation.

The execution semantics of `prerequisites` are **skippable but reported**: a failed probe warns and continues, leaving it to the user whether to proceed —
do not fail outright just because Docker cannot be probed; that would also block the legitimate order of "install the base environment first, add the image later".

---

## 4. Code landing points (verified integration points)

| File | Change |
|---|---|
| `artifacts/runtime/extension.py` | New: manifest parsing, channel resolution, download verification, orchestration of the two installation kinds, `post_install` printing |
| `artifacts/runtime/installer.py` | `main()` gains the `extension` subcommand group; `install()` triggers on `--extension` at the end; `install_manager()` gains the new module's file name |
| `artifacts/build_english_installer.py` | Add `extension.py` to the file tuples of `manager_sources()` / `manager_shell()`; update `artifacts/installer.en.json` in sync (**new Chinese strings must get English entries, otherwise `translate()` raises `Missing English translation` directly**) |
| `artifacts/build_installers.py` | No logic change needed, but after any change you must rerun `python3 artifacts/build_installers.py` and pass `--check` |
| `artifacts/runtime/installer.py:712` | **Suggested**: change `bundles_dir` from `release/'robot-bundles'` to `<root>/robot-bundles`. As it stands, `RegisterInstalledBundle()` writes `installed-bundles.json` into the immutable Release directory while extension Bundles point to paths outside the Release — architecturally mixed, and more visible once extensions are enabled |
| `artifacts/oss_client.py:153` | Add `extensions/*/stable.json` to the mutable whitelist |
| `extensions/<id>/extension.json` | New: manifest source file, versioned with the repository |
| `extensions/<id>/README.md` | New: how to obtain the extension, license, manual prerequisites |
| `tests/test_artifacts_extension.py` | New: manifest parsing, ordering, port conflicts, missing artifacts, bad sha256, offline mode |

Reuse the existing test entry points: `python -B -m unittest discover -s tests -q`, plus `bash -n artifacts/install.sh`,
`python3 artifacts/build_installers.py --check`, and `go test artifacts/gateway/main.go artifacts/gateway/main_test.go`.

### An easy-to-miss pitfall: a new management module must be synced in four places

`extension.py` is the **fourth** management module. Missing one place does not fail immediately — it blows up on some entry point:

| Location | What happens if missed |
|---|---|
| Payload assembly in `artifacts/build_from_releases.py` | The precompiled release package has no `extension.py` |
| Payload assembly in `artifacts/build_release.py` | Same (the other assembly path) |
| `install_manager()` in `artifacts/runtime/installer.py` | `semanticctl extension` in the field cannot find the module |
| The two file tuples in `artifacts/build_english_installer.py` | The English edition loses half the functionality |

`test_standalone_installer_does_not_add_unlisted_bytecode` in `tests/test_artifact_experience.py`
catches the first pitfall: it copies the modules out of the payload and runs `installer.py` standalone; a missing module fails directly with
`ModuleNotFoundError`.

---

## 5. Relationship with TUI stage 8

The two paths serve different audiences and **share the same manifest** — do not write two versions:

| | TUI stage 8 (source build) | `install.sh` extension (precompiled) |
|---|---|---|
| Audience | Developers who need to change component versions | Users who just want it running |
| Artifact source | Built locally (upstream source + each repo's source) | Download verified artifacts |
| Prerequisites | Go/Node/uv/xmake + each repo's source + intranet | Python 3.10+ and network |
| Manifest | `EXTENSIONS` registry + `LIBERO_*` / `ISAAC_*` settings | `extension.json` |
| Status | Stage 8's 12 steps (LIBERO) / 14 steps (Isaac) | `semanticctl extension` |

TODO (optional, to avoid two sources of truth drifting apart): make TUI stage 8's artifact list also read from `extensions/libero/extension.json`,
with the TUI responsible only for "how to build" and the manifest for "which artifacts exist and where they land". Currently the TUI's artifact names are assembled by
`LIBERO_ARTIFACTS`, duplicating the manifest content.

---

## 6. Phased implementation suggestion

Ordered by risk from low to high; each step is independently verifiable:

1. ~~**Read-only layer**: manifest format + `extension list/show/verify` (download and verify only, no installation).~~
   **Done.** `artifacts/runtime/extension.py` landed, and `install.sh`'s embedded management modules gained
   `extension.py` (all three payload assembly points + the `manager_shell()` tuple must be updated in sync, otherwise
   running `payload/installer.py` standalone fails with `ModuleNotFoundError`). Entry points:
   `semanticctl extension list | show <id>` and `extension verify <id>`.
   The manifest template is at `extensions/libero/extension.json`; **`sha256` is still `0` and must be backfilled before release**.
2. ~~**LIBERO installation**: wire up the Runtime and component installation paths + the `post_install` checklist.~~
   **Done (2026-10).** `install` / `plan_commands` / `uninstall_plan` in `extension.py`
   implement both landing sites and the fixed order; `install_extension()` in `install.sh` triggers on
   `--extension` after the base environment is installed; offline goes through `--extension-package-dir` (with all six artifacts present it is fully offline),
   and `--extension-dry-run` only prints the command plan. CI uses the staging directory for the offline smoke (see
   `.github/workflows/extension-release.yml`). **To-do**: on a target machine, run through the installation item by item with the real artifacts per "LIBERO 打包与安装速查"
   and backfill the digests — this is a post-release operations acceptance step, not a code gap.
3. ~~**Release pipeline**: publish scripts for `extensions/<id>/` + OSS mutable whitelist + version pinning into
   `repo-versions.json`.~~
   **Done (2026-10).** The OSS mutable whitelist gained `extensions/*/stable.json`;
   `artifacts/build_extension.py` backfills and produces staging; `artifacts/publish_extension.py` publishes the
   OSS immutable prefix, promotes `stable.json` and creates the GitHub Release; the `extensions` section of `repo-versions.json`
   pins the version, tag and per-artifact anchors. The `sha256` in the manifest template is still a placeholder, backfilled by
   `build_extension.py` from the real artifacts at publish time; the immutable
   `extensions/<id>/<version>/extension.json` on the OSS channel already holds the backfilled real digests.
   The installer does not accept this template for installation: `extension.install()` first checks whether each artifact's digest is the all-zero
   placeholder, and if so immediately reports `清单里的 sha256 仍是占位值`, pointing to the release-channel manifest or backfilling first —
   avoiding the "the plan prints fine, but downloads and verifications fail one by one" error surfacing only after multi-GB downloads.
   **Published (2026-10-05)**: isaac 0.1.0 and libero 0.1.0 have been pushed to the OSS primary channel (bucket
   `insightos-artifacts`, prefix `semantic`, objects `public-read`, anonymously readable).
   The GitHub Release mirror has been published to `insightos-community/quick-start` (tags `ext-isaac-v0.1.0` /
   `ext-libero-v0.1.0`), publicly downloadable and verified; libero's four artifacts over the 2 GiB per-asset limit
   (the runtime and the three franka packages) go through OSS only, with automatic fallback on the GitHub channel.
4. ~~**Isaac support**: probe semantics of `prerequisites` + port-range allocation + GPU prerequisite checks.~~
   **Done (2026-10).** The manifest template `extensions/isaac/extension.json` landed; `extension.py` supports
   probe execution of `prerequisites[].check` (failures only warn and continue), pre-install checks of `host_requirements.gpu` and the
   declared `ports` (port occupancy only warns), `runtime.content` (`--asset-root`) and
   `runtime.pack.license` (`--accept-license`); offline installation goes through `--extension-package-dir` +
   `--manifest-file`. The TUI stage 8 isaac line (8.14–8.27) is implemented and shares the manifest with the precompiled channel.
   The engine image and dataset are still not distributed: the manifest only registers and probes them; `sha256`/`license` are backfilled before release.
   repo-versions gained `semantic-simulation/isaac-runtime` (BEHAVIOR depends on it; it was missing from the manifest before).

---

## 7. Open questions

1. **Whether `bundles_dir` should move out of the Release directory**: moving is cleaner, but affects configuration compatibility of already-installed instances,
   requiring a configuration migration or compatible reading. Suggested to do together with extension support and write into the migration path of `configure_existing`.
2. **Whether the extension manifest should go into the base artifact**: including it would allow offline `list`, but couples extension versions to the base Release.
   The current design chooses "fetch from the channel at runtime"; the `--package` offline scenario can add `--extension-manifest <file>` to override.
3. **Offline installation**: > `--package` already supports the base artifact offline; extension offline uses `--extension-package-dir <directory>`
   (with the six artifacts + manifest present it is fully offline) or `--extension-manifest <file>` to override the manifest source. **Implemented**.
4. **The default scope of `previews`**: the manifest gives suggested values; whether to filter along dimensions beyond `--scene` (by task set)
   is to be decided after real usage feedback.
