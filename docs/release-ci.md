# Release CI and the installer

[English](release-ci.md) | [简体中文](release-ci.zh-CN.md)

All 13 components use the official GitHub `ubuntu-24.04` runner. PR/main runs the component checks and uploads temporary Actions artifacts; pushing a `v*` tag publishes a Release. Historical tags are re-published via **Actions → CI and Release → Run workflow**, filling in the tag on main. Builds check out the business source from the tag and read the build scripts from the current workflow commit, recording both SHAs separately; tags are not moved and published Releases are not overwritten.

| Repository | Release contents |
| --- | --- |
| Semantic-Framework | Static Server, Pilot, CLI |
| semantic-web | Web production static assets |
| AbilityFramework | Static AbilityFramework |
| Ability-SDK-Python | Python Wheel, sdist |
| semantic-docs | Hugo documentation site |
| robot-sdk | core, r1pro, franka Wheels, sdist |
| robot-skill | SDK Wheel, sdist, three Skill ZIPs |
| r1pro-ability | Shared Wheel, sdist, seven Ability ZIPs |
| ability-scaffold | Wheel, sdist |
| semantic-deployment | Static deployment tool, Type Package templates |
| mujoco-asset | Approved-for-publication maintenance models, scenes, asset catalog and provenance statements |
| ability-runtime | Pinned third-party Python Wheel cache and license files |
| mujoco-runtime | Runtime Wheel, visuals Wheel, offline native MuJoCo Runtime Pack |

Every Release includes `SHA256SUMS` and `release.json`. The latter records the tag, source SHA, build-script SHA, platform, CI link and verification scope. The R1Pro CI takes its dependencies from the published Robot SDK, Ability SDK and scaffold; the Runtime Pack pins the Framework scene definitions and asset catalog versions. When updating dependencies, update the dependency pins in the corresponding CI and quick-start's `repo-versions.json` at the same time, and publish a new tag only after the compatibility check passes.

## Installation

Run in quick-start on the **current main** (the old `v0.1.0` source tag does not contain the new entry point; the tag stays unchanged):

```bash
python3 semantic_installer.py --release --install-system-deps
# Specify a dedicated directory and auto-confirm the installation:
python3 semantic_installer.py --release --dir "$HOME/.local/share/semantic-demo" --yes
```

By default this downloads quick-start's `v0.1.1` Release. The entry point verifies the tag's pinned source SHA, validates every downloaded file, then hands off to the original artifact installer to complete unpacking, environment initialization, Runtime registration, Skill publication and service startup. The target machine does not need Go/Node/xmake or the individual sub-repository sources; it needs Python 3.10+, the system graphics runtime libraries and zstd, plus network access when installing the Python runtime for the first time. The administrator account `admin` uses a random password generated at install time — view it with `semanticctl welcome`; the source-development mode's `test-admin-pass` does not apply to this entry point.

You can also download only `install.sh`, the full-package `.tar.gz` and `SHA256SUMS` from the Release, first run `sha256sum --check --ignore-missing SHA256SUMS`, then run `bash install.sh --package <full-package-path> --sha256 <full-package-SHA256> --install-system-deps`. The install entry point does not overwrite an existing instance of a different version; upgrades should use a new directory and migrate data separately.

## Assembly

quick-start's **Installer from Releases** workflow reads all component Releases from the version manifest and does not recompile any component; it only compiles this repository's lightweight Web gateway. The full package ships with `release-lock.json`, recording the hashes of all assets actually used. The build machine needs Go 1.25.8, uv 0.12.12, Python/PyYAML and binutils; the installation machine does not need these build tools.

```bash
python3 artifacts/fetch_releases.py --cache /tmp/semantic-releases
python3 artifacts/build_from_releases.py \
  --version 0.1.0 --cache /tmp/semantic-releases \
  --output artifacts/releases/0.1.0/linux-x86_64
```

The output directory must not exist, and hashes are re-verified even on cache hits. The source SHAs in the version manifest must match the Release metadata; dependency pins of different components must also be consistent. Archive unpacking rejects path traversal, links and duplicate files; the glibc baseline of the static applications and uv is checked at assembly time. Models and third-party Wheels keep their provenance and license notices and are not relicensed.

After assembly, PR/main runs a real installation smoke check covering the Web SPA, the authentication API, three exact Skill versions, native MuJoCo registration/scene smoke, repeated installation and management-configuration updates. Only after it passes are tag/manual releases allowed. It does not execute physical-robot tasks, GPU acceptance or LLM depalletizing tasks. The internal Python package versions in a Release continue to follow the original business baseline and are not forcibly changed to maintenance tag suffixes.

## Optional musl Release

The default installer and `repo-versions.json` continue to use the existing glibc runtime stack. The additional `.github/workflows/musl-release.yml` uses separate `musl-v*` tags and publishes a pre-release package selected via `--musl`, without updating the normal latest Release or OSS stable.

The pinned inputs are in `artifacts/musl/releases.json` (in-organization dependency Releases), `upstream.json` (official musl Python/uv, base installation packages and sources) and `python-wheels.json` (PyPI musl Wheels). Assembly verifies SHA-256, source commits and platform, and audits the ELF dependencies of the entire package and its Wheels; the package also contains the pinned-version musl loader, libc and licenses. It is then tested in an offline Alpine container (in-package/system musl) and an Ubuntu 22.04 container without system musl (in-package musl), covering the Chinese and English install entry points, Server/Web, a Native MuJoCo scene, joint operation of the robot libraries, and Python subprocesses. `--musl-runtime bundled|system` selects the runtime; the default is bundled. See the [musl build notes](../artifacts/musl/README.md) for details.

### Optional musl tag publication

Push one platform tag at a time. A manual dispatch at an existing musl tag also
publishes after qualification; dispatching a branch only builds and tests:

```bash
gh workflow run musl-release.yml --ref musl-vMAJOR.MINOR.PATCH-REVISION
```

Published assets and tags are immutable. For an already published version, use its
existing release; a changed package requires a new tag. To mirror verified releases
to OSS, see [the four-platform mirror commands](../artifacts/site/README.md#reproduce-an-oss-release-mirror).

## Extension Scenes

After the precompiled entry point has installed the base environment, `--extension <id>` triggers the extension Scene installation (`semanticctl extension install`).
For the sidecar design and implementation path of the extension Scenes (LIBERO and BEHAVIOR/Isaac), see
[Extension Scene installation design](extensions.md): a separate manifest + the `semanticctl extension` subcommand + a separate channel,
keeping the base artifacts lean and immutable.

- **LIBERO**: six distributable artifacts, `extensions/libero/extension.json`. The three artifacts that exceed
  GitHub's 2 GiB per-asset limit (runtime support, Ability, model) go through OSS only.
- **BEHAVIOR/Isaac**: `extensions/isaac/extension.json`. The engine image `behavior:v3.9.2` (about 31 GB) and
  the dataset (tens of GB) are **not in any Release**; the manifest only registers and probes them (the `probe` entries
  under `prerequisites`) — the release channel carries only the six small artifacts: Runtime / Scene / runtime support / Ability / model / Skill.

### Channel layout

OSS is the primary channel, GitHub Releases the mirror. Manifests and version pointers are served uniformly by OSS; each artifact's
`url` in the manifest is a relative path, joined at install time according to the selected channel:

```text
OSS:    <oss>/extensions/<id>/stable.json               # mutable pointer
        <oss>/extensions/<id>/<version>/extension.json  # immutable manifest
        <oss>/extensions/<id>/<version>/<artifact>      # immutable artifacts
GitHub: Release of tag ext-<id>-v<version>              # immutable mirror (flat assets, no subdirectories)
```

Select the channel with `--extension-source oss|github` (default `oss`). GitHub's hard limit for a single Release asset is
**2 GiB**; the manifest marks over-limit artifacts with `hosts: ["oss"]`, and on the GitHub channel the installer **automatically falls back to OSS** to download
those artifacts while the rest still come from GitHub. So the GitHub channel can install, but it is not an offline channel — for offline use
`--extension-package-dir` (the six artifacts + the manifest in the same directory).

### Release tooling

On the build machine, produce the six artifacts first, then publish in two steps (details in each extension's `README.md`):

```bash
python3 artifacts/build_extension.py --id <id> --version <version> \
  --package-dir <artifact-directory> --output <staging-outside-the-repo>
python3 artifacts/publish_extension.py --id <id> --version <version> \
  --staging <staging> --channel oss,github
```

`build_extension.py` backfills `sha256`/`size` per artifact, adds `hosts: ["oss"]` for artifacts over 2 GiB, writes out
staging and `stable.json`, and self-checks with `extension.parse`. `publish_extension.py` first uploads the immutable
`extensions/<id>/<version>/`, promotes `extensions/<id>/stable.json` only after all checks pass, then creates the
GitHub Release (`extension.json`, `SHA256SUMS`, `release.json` and the mirrorable artifacts). The extension version and
GitHub tag are pinned in the `extensions` section of `repo-versions.json`.

Licenses have been authorized and backfilled: LIBERO is recorded as `LIBERO`, BEHAVIOR as `behavior-assets`; the installer uses this to automatically add
`--accept-license`, so installing an extension with a `license` no longer requires specifying it manually.

### CI

`.github/workflows/extension-release.yml` (manually triggered) chains together: manifest and tooling unit tests → backfilling and staging →
offline smoke installation → publish to OSS → verify channel summary → create the GitHub Release. The build machine must already have produced the six artifacts and put
the OSS credentials into the `OSS_ENV` secret. The engine image, the licensed dataset and the π0.5 policy service **do not enter CI** and are still prepared by humans.
