# Semantic artifact release and one-click deployment

[English](README.md) | [简体中文](README.zh-CN.md)

This is the **prebuilt artifact deployment** entry point, independent of the
source-based TUI installer. The install side does not clone Git and does not run
Go/xmake/npm builds; it extracts artifacts produced on the build machine and
initializes a standalone instance on the target machine.

The repository root provides two independent installation entry points. In the
current main of quick-start, choose one by download source:

```bash
bash ./install.sh --install-system-deps     # Alibaba Cloud OSS stable, Chinese prompts
bash ./install-en.sh --install-system-deps  # GitHub Releases v0.1.1, English prompts
```

Both verify the downloaded files; the default glibc installation requires
downloading a standalone Python environment. The OSS and GitHub version numbers
are independent of each other; use `--version` to pin a version. For the
clone-free download commands and platform requirements, see the root
[中文 README](../README.zh-CN.md#从这里开始) and [English README](../README.md#start-here).

The original Python Release entry point is still available:

```bash
python3 semantic_installer.py --release --install-system-deps
```

It defaults to `v0.1.1` and supports `--tag`, `--dir`, `--yes` and other
options. Use `fetch_releases.py` when downloading components for assembly; CI
uses `build_from_releases.py`, with no need to recompile the sub-repositories.
For versioning, verification and assembly instructions, see [Release CI](../docs/release-ci.md).

Installing from the public OSS or GitHub Releases requires no OSS credentials;
private OSS objects can use time-limited tickets.
For the maintenance operations of publishing artifacts to OSS, see [OSS.md](OSS.md).

The root scripts are generated from the installer source and must not be edited
by hand. After changing `artifacts/install.sh`, the English generator or the
runtime modules, run:

```bash
python3 artifacts/build_installers.py
python3 artifacts/build_installers.py --check
```

This synchronizes the root `install.sh`, `install-en.sh` and
`artifacts/install-en.sh`; CI checks the generated output and validates the
standalone scripts.

Introduction and installation entry: <https://semantic.insightos.cn/>. For the
static site source, Nginx configuration and maintenance/rollback instructions,
see [site/README.md](site/README.md).

## LAN, installation progress and desktop entry

Fresh install with LAN access to the Web UI enabled:

```bash
curl -fsSL https://semantic.insightos.cn/install.sh | bash -s -- --install-system-deps
```

On a fresh install the Web UI listens on `0.0.0.0:3000` by default, accepting
connections to both `127.0.0.1` and the host's NIC IPv4 addresses, so no extra
binding is needed.
`--lan` remains as a compatibility option; you can use `--web-host <NIC-IP> --web-port 3001`
to select a NIC and port, or `--web-host 127.0.0.1` to restrict to the local machine.
The API/WS services keep listening locally and are uniformly proxied through the Web gateway.
The installer does not modify firewalls or cloud security groups automatically:
only expose the Web port (default 3000) to trusted LANs; never expose the API/WS/Runtime publicly.
"All NICs" may include a public NIC; for public access use an HTTPS reverse proxy
with access control. HTTP is not encrypted.

**Already-installed instances (including .4 versions) do not need to redeploy the
database and runtime packages**; you can update the management tooling and enable
LAN access:

```bash
curl -fsSL https://semantic.insightos.cn/install.sh | bash -s -- \
  --configure-existing --dir "$HOME/.local/share/semantic" --lan --desktop-shortcut
```

This mode still downloads and verifies the full archive of the new version, but
only installs `bin/semantic-manager`, updates `semanticctl`, the listen
configuration and the shortcut entry.
It preserves the business version, the original release package, the database,
passwords and the runtime environment; the old install.json is saved under configs.
When changing the listen configuration only the Web service is restarted; a
running Server is not restarted. Do not confuse a business upgrade with a
management-tooling update.
An existing instance without network parameters keeps its original listen
configuration; to switch to local + LAN, explicitly add `--lan`.
This mode also supports `--web-port 3001` to change the Web port; conflicts are
rejected before the original Web service is stopped.
For automation add `--yes`; `--no-start` does not start services (the original
Web is still stopped when changing the listen configuration).

The installer shows real download byte progress, SHA-256/unpacking stages, the
task list and the duration of each stage.
Interactive terminals use a single-page task table refreshed in place; on
success the current viewport is cleaned up to show only the welcome form,
without clearing the shell scrollback history.
On failure the task state and log location are preserved; redirected output does
not refresh or clear the screen.
The task-bar percentage is the proportion of completed tasks, not an estimate of
remaining time. Narrow screens wrap by character width; non-TTY output contains
no ANSI control sequences.
The welcome page has four sections — access, management, environment and notes:
cyan titles/commands, green success, yellow credentials/cautions, gray auxiliary labels.
The terminal welcome page shows text only and no longer renders ASCII icons; a
standard 80×24 terminal shows a compact welcome form.
`NO_COLOR=1` disables colors; `TERM=dumb` disables colors and redrawing.
Passwords are written only to `/dev/tty`, never to stdout/stderr pipes or the
install log; when there is no controlling terminal, the location of the password
file is shown instead.
Note that screen recording can still capture the terminal display; mask
passwords before sharing screenshots.

The desktop is auto-detected; `--desktop-shortcut` creates the shortcut
explicitly, `--no-desktop-shortcut` skips it.
The shortcut uses the original PNG and opens the local Web UI directly via
`xdg-open`; it carries no account credentials and does not auto-start services.
XDG-localized desktop directories and application menus are supported, and
multiple instances use different file names. Environments such as GNOME may
require right-click "Allow Launching".
Without a desktop or xdg-open, a skip is reported without affecting the
installation; uninstall only removes shortcuts created by this instance that the
user has not modified.
The format follows the [Desktop Entry specification](https://specifications.freedesktop.org/desktop-entry/latest-single/).

The completion page provides environment variables and start/stop guidance, and
does not modify shell startup files on its own:

```bash
export SEMANTIC_HOME="$HOME/.local/share/semantic"
export PATH="$SEMANTIC_HOME/bin:$PATH"
semanticctl start
semanticctl status
semanticctl stop
semanticctl welcome  # show the address, environment-variable guidance and terminal password again
```

To make it persistent, add the two export lines to `~/.bashrc` or `~/.zshrc`.
Boot autostart is not configured at present.

## Default installation (local machine and LAN)

```bash
curl -fsSL https://semantic.insightos.cn/install.sh | bash -s -- --install-system-deps
```

Current artifact target: Linux x86_64, glibc >= 2.28, full Server + Web + Native
MuJoCo + R1 Pro Bundle. The applications are static ELF binaries; the glibc
threshold comes from the uv/Python/Wheel runtime stack;
meeting the threshold does not mean every distribution has passed product
acceptance. For the tested scope, see [PORTABILITY.md](PORTABILITY.md).
The thresholds above apply to the default Linux x86_64 package. A native preview
package for Apple Silicon / macOS 15.5+ is also available; see the [macOS build instructions](macos/README.md). No Windows installer is provided yet.

On Linux x86_64, the additional `--musl` flag selects the musl package; the
default glibc path is unchanged. `--musl-runtime bundled` (the default) uses the
musl shipped with the package and runs on either glibc or musl hosts;
`--musl-runtime system` uses the host's existing musl. The runtime choice is
stored in the instance; switching uses a new directory and does not modify the
host's `/lib`. Both the Chinese and English scripts and
`python3 semantic_installer.py --release --musl` support this. The optional
package bundles CPython 3.13.15, NumPy 2.3.5, robot dependencies and Mesa; see
[musl/README.md](musl/README.md) for details. For GPU probing and the software
fallback entry, see [mesa/README.md](mesa/README.md).

The entry-point form is inspired by the [Hermes install script](https://hermes-agent.nousresearch.com/install.sh):
it supports pipe launching, parameterized paths and non-interactive
installation; during installation, confirmations are read from `/dev/tty`,
so the stdin of the download script is never treated as user input. This
implementation does not directly execute the reference script.

## Directory structure

```text
artifacts/
├── install.sh                    # hostable curl | bash entry point
├── site/                         # landing page, static-site container and edge reverse-proxy config
├── build_release.py              # build machine: extract, complete, verify and package
├── build_native.py               # standalone build of static AbilityFramework and Go programs
├── test_container.py             # one-shot Debian/Fedora container deployment test
├── smoke_release.py              # real installation in a separate dir/ports and piped reinstall test
├── smoke_uninstall.py            # fresh instance: data-preserving uninstall, reinstall, piped full-removal verification
├── runtime/installer.py           # install/initialize/semanticctl implementation
├── runtime/uninstall.py           # uninstall logic source, embedded in install.sh, works offline
├── gateway/main.go                # Web static files + HTTP/WS reverse proxy
├── channels/stable.json           # download paths, SHA256 and sizes of the current internal snapshot
└── releases/<version>/linux-x86_64/
    ├── manifest.json             # download metadata; paths relative to the whole artifacts/ site root
    ├── release.json              # component versions, source commits, platform and distribution boundaries
    ├── semantic-<version>-linux-x86_64.tar.gz
    └── semantic-<version>-linux-x86_64.tar.gz.sha256
```

Inside the archive, content is stored by component; the full workspace is not
packaged:

```text
bin/                semantic-server / semantic / semantic-pilot / Web gateway / uv
web/                Vite production static files (no npm run dev)
robot-bundles/      AbilityFramework, Pilot, seven Ability ZIPs, Wheels, deployment templates
robot-skills/       grasp-object / semantic-navigation / place-object release ZIPs
runtime-packs/      official Native MuJoCo Runtime Pack (wheelhouse, lock, scenes, licenses)
assets/mujoco/      version-controlled model, mesh, scene and asset directories
defaults/          clean Server configuration from the source templates (no running config is read)
release.json        component versions and source commits
native-linkage.json  static-linkage check of the application ELFs and uv's direct glibc symbol baseline
files.json          SHA256 of every artifact
installer.py        initialization logic
```

The archive does not extract `.env`, user databases, Projects/Tasks/sessions,
Pilot credentials, run logs, `.git`, `node_modules`, existing `.venv`
directories, or Python symlinks pointing at the build machine.
Robot uses Python 3.13; the current Native MuJoCo Pack uses Python 3.10.19.
The two build separate environments in the target directory; you cannot copy a
Conda or an already-installed venv over.

## Building release packages on the build machine

First complete the source build with the existing TUI (at least stages 3.2,
5.1–5.4), and prepare uv, Go, Node/npm, tar/zstd, readelf, xmake, C/C++ static
libraries and musl-gcc (musl-tools on an Ubuntu build machine).
If the Web repository already has dependencies installed, build production
directly; otherwise run `npm ci` in the Web repository first.

```bash
python -B artifacts/build_native.py
uv run --no-project --with PyYAML python artifacts/build_release.py \
  --version 0.5.0-dev.20260910.3
```

`build_native.py` builds AbilityFramework in an independent source copy under
`.build/`, enables `fwk-static`, forces third-party libraries to be built
statically from source, and does not modify the original repository's xmake
configuration or the existing `.output`.
The Go programs keep CGO, using `CC=musl-gcc`, the `musl,netgo,osusergo` tags
and external static linking; they include Server, CLI, Pilot and Robot Instance.
Build logs are saved under `.build/native-static/` by default.
Use `--component ability` or `--component server` to build them separately.

The release builder reads `.build/native-static/` by default; you can also pass
`--native-dir DIR` to provide already-verified static artifacts.
All five programs must be present, and `readelf` checks must show no `PT_INTERP`
or `DT_NEEDED`; silently falling back to the old dynamic versions is not
allowed. The AbilityFramework/Pilot/Robot Instance inside the Bundle are
replaced in sync.

The builder checks real LFS files, Wheel ZIPs, the exact versions of the three
Skills and the consistency of the Bundle templates.
The Runtime Pack exports pinned dependencies from `uv.lock`, then converts them
into a wheel-only lock without source paths;
the scene directory uses the source templates of the current Framework schema,
so that outdated authoring samples in the Runtime repository do not become
incompatible with the current Server. Existing Python environments do not go
into the release package.

Existing version directories refuse to be overwritten. Rebuilds should use a new
version. `--runtime-pack FILE` explicitly reuses an already-verified Runtime
Pack; **use it only when the Runtime source, lock and scene templates are
unchanged**.
The first build leaves a reusable Pack at `.build/native-mujoco.runtime.tar.zst`.
`--skip-web-build` applies only to an already generated and confirmed
`semantic-web/dist`.

The current `channels/stable.json` is an internal development snapshot channel
and does not mean a formal stable version has been released.

## Local one-click installation

```bash
bash artifacts/install.sh \
  --package artifacts/releases/0.5.0-dev.20260910.3/linux-x86_64/semantic-0.5.0-dev.20260910.3-linux-x86_64.tar.gz \
  --dir "$HOME/.local/share/semantic" \
  --yes
```

The `.sha256` next to the archive must be kept; you can also explicitly pass
`--sha256 HASH`.
By default the installer asks for the path and creation confirmation; use
`--yes` for CI or unattended runs. The default directory is
`$HOME/.local/share/semantic`, and non-empty directories used for other purposes
are not overwritten.

The entry point needs bash and Python 3.10+, and the online pipe also needs
curl; prepare them with the system package manager first.
Missing system dependencies are reported as a list. To allow the installer to
call the system package manager/sudo, add `--install-system-deps`.
With this option enabled, the installer first checks the sudo authorization and
then enters the dynamic progress panel. When a password is needed, an
authorization form is shown via `/dev/tty` and sudo reads the current Linux
user's password directly (no echo, nothing written to logs), supporting
`curl | bash`. Root or an existing valid authorization skips the prompt
automatically. The authorization is valid for 180 seconds.
Subsequent commands use `sudo -n` and no longer wait hidden for a password; an
expired authorization fails explicitly — run `sudo -v` first and retry.
`--yes` only skips the installation confirmation and does not replace the sudo
authorization; unattended runs need pre-configured working privileges or
dependencies pre-installed by an administrator.
Logs are written while waiting for authorization and before each dependency
command runs; the progress panel shows the current command and its duration.
apt-get, dnf (or yum), pacman and zypper are supported, selected by the
distribution's ID/ID_LIKE.
What gets installed is certificates, zstd, the C++/OpenMP runtime libraries and
EGL/Mesa; the static applications no longer require system yaml-cpp, libuv or
OpenSSL. The default rendering backend is EGL, and OSMesa is not a mandatory
dependency.
Without this option no system installation is performed; the installer does not
rewrite mirror sources, disable signature verification or automatically run a
full-system upgrade.
On Arch, the administrator should keep the system updated first; the script uses
`pacman -S --needed` and never runs `-Sy` or `-Syu`.
On unknown distributions the administrator may satisfy the dependencies
manually, but the installer refuses to guess a package manager and modify the
system automatically.

You can use `--http-port`, `--ws-port`, `--web-port` and `--runtime-port` to
avoid existing services.
Fresh installs default to 8034, 8035, 3000 and 8036 respectively; existing
instances keep their configured HTTP port. The installer does not automatically
stop other processes to free ports.
`--no-start` only initializes without starting Server/Web; the Runtime
installation still runs the isolated-scene smoke test.

## HTTPS one-click entry point

Place `install.sh`, `channels/` and `releases/` on your own trusted HTTPS static
site (for example internal object storage or a download site) in the relative
structure described above, then:

```bash
curl -fsSL https://YOUR-HOST/semantic/install.sh | \
  bash -s -- --base-url https://YOUR-HOST/semantic --yes
```

To pin a version add `--version 0.5.0-dev.20260910.3`; you can also set
`SEMANTIC_DOWNLOAD_BASE` in advance and omit `--base-url`. `YOUR-HOST` is a
generic hosting example; the default address is already configured to
Alibaba Cloud OSS — for public access and the optional private-ticket flow, see
[OSS.md](OSS.md). Local HTTP testing requires an explicit `--allow-http`; HTTP
and HTTPS-downgrade redirects are rejected by default. The server must return
the artifacts as plain files; the current entry point does not handle code-hosting
platform login pages.

The bootstrap stage first verifies the archive SHA256, rejects out-of-bounds
paths, symlinks, special files and oversized archives, and only runs the
installation logic after unpacking. The installation logic also verifies the
per-file manifest.
SHA256 protects against corruption but does not replace signing: the HTTPS site
and the bootstrap script must be trustworthy. High-trust environments can
download first, review the entry point, and then pin the artifacts with a
`--sha256` obtained through an independent trusted channel.

## Installation and initialization result

```text
<install-dir>/
├── releases/<version>/   artifacts not mixed with the source workspace, and rebuilt Python environments
├── current -> releases/<version>
├── bin/semanticctl       management entry point of this instance
├── configs/             initialized Server, Agent and Skill configs plus secrets.json
├── data/                new database (no data copied from the original instance)
├── runtimes.d/          Native MuJoCo registered after CLI verification
├── runtime-packs/       unpacked official Runtime Pack
├── runtime-envs/        target-machine standalone MuJoCo venv
├── content/             scene directory
├── python/              Python downloaded on demand by uv
├── run/                 PID identity and installation lock
└── logs/                logs of every installation and of Server/Web
```

Flow: SHA256 → platform/dependency checks → extract to the install directory →
Robot venv rebuild/import checks → `semantic init` → random admin password →
official Runtime Pack installation and smoke test →
Server/Web health checks → log in and release the three Robot Skills.

On a fresh install the Web UI listens on all IPv4 NICs by default: visit
`http://127.0.0.1:3000` or `http://<LAN-IP>:3000`. For public access, an SSH
tunnel or an administrator-configured HTTPS reverse proxy is recommended; public
exposure is not the default. The model is still a mock; the real model service
and token must be configured in the Web system settings. No business Project is
created, no Robot Task is dispatched and no grasping motion is run
automatically. The smoke test of the Runtime installation is a temporary
simulation scene, cleaned up by the CLI afterwards.

The username is `admin`; the random password is in
`<install-dir>/configs/secrets.json` (0600), is not printed in the install log,
and does not reuse the development default password. Re-running the same version
preserves the password, configuration and database.

```bash
"$HOME/.local/share/semantic/bin/semanticctl" status
"$HOME/.local/share/semantic/bin/semanticctl" start
"$HOME/.local/share/semantic/bin/semanticctl" doctor
"$HOME/.local/share/semantic/bin/semanticctl" logs
# Stop the scenes/Robots in Studio first, then stop Server/Web:
"$HOME/.local/share/semantic/bin/semanticctl" stop
```

At present, per-user background process management is provided; systemd/boot
autostart is not registered automatically. PID verification includes the Linux
process start time, so PID reuse cannot cause other processes to be killed by
mistake. Cross-version upgrades/database migrations are not performed
automatically for now: use a new installation directory and design a data
migration plan after verification. An unfinished installation of the same
version can be re-run; the logs preserve the failure reason, and no destructive
database reset is performed.

## Uninstall

Use the new `install.sh`; no release package needs to be downloaded or
specified. Old hosted `.2/.3` instances are also supported.
Since `.11`, `semanticctl uninstall` is also available (supporting `--dry-run`,
`--yes`, `--purge`).
When the old management tooling lacks this subcommand, use the latest
`install.sh --uninstall` directly (it also accepts the `uninstall` subcommand),
without updating the business packages or starting services first.

```bash
# Only check directories and processes and show the plan; nothing is stopped or deleted; an audit log is still generated
bash artifacts/install.sh --uninstall --dir "$HOME/.local/share/semantic" --dry-run

# By default user configuration, database and logs are preserved; after interactive confirmation, Server/Web are stopped and the programs uninstalled
bash artifacts/install.sh --uninstall --dir "$HOME/.local/share/semantic"

# Permanently delete the entire instance including all user data; non-interactive scenarios must also explicitly pass --yes
bash artifacts/install.sh --uninstall --dir "$HOME/.local/share/semantic" --purge --yes

# The online entry point can also uninstall; only the entry script is downloaded, not the several-hundred-MB artifacts
curl -fsSL https://semantic.insightos.cn/install.sh | \
  bash -s -- --uninstall --dir "$HOME/.local/share/semantic" --yes
```

By default, `releases/`, `python/`, `runtime-envs/`, `runtime-packs/`, `bin/`
and the `current` symlink are deleted. `configs/`, `data/`, `logs/`,
`content/`, `runtimes.d/`, Robot instance data and other non-program directories
are preserved, and the installation state is marked as not ready. **The
data-preserving mode is not a backup**; back up important data separately.
Reinstalling with the original version artifacts, the original path and the
original ports rebuilds the runtime environment and preserves the password; the
cross-version migration rules are unchanged.

Before uninstalling, safely stop the scenes and Robots in Studio first. The
uninstaller checks locally readable process arguments, program paths and working
directories; if it finds that the instance still has Robot/Runtime or other
processes, it refuses to continue and does not terminate them automatically.
The status table clearly shows whether Server/Web are stopped or running, along
with other occupying processes, instead of showing `{}` as the state.
If a terminal such as Bash is still sitting in the instance's real directory, it
reports the PID, process name, working directory and suggests `cd ~`; do not use
kill as a substitute for changing directories. Directories whose working
directory has been deleted (inode link count 0) are no longer misidentified as
instance occupation, and that terminal is not closed either; only real
directories whose names end in ` (deleted)` remain protected.
SIGTERM is sent only to Server/Web processes whose PID, start time and in-instance
program path all match; if they have not exited within 20 seconds the operation
aborts without force-killing. This check does not replace a manual safe shutdown
of remote devices/remote Runtimes.

The directory must contain `.semantic-install-root` and a valid `install.json`,
and the operation must be performed by the same user who installed it.
Home directories, the current working directory and its parents, symlinked root
directories, abnormal management paths and mount points inside the directory are
rejected. Do not run the uninstall from inside the instance directory. Deleting
internal symlinks does not follow them to the outside; system shared packages
are not uninstalled and resources outside the instance are not cleaned up. What
`--purge` deletes cannot be recovered by this script.

Every uninstall (including failures and dry-runs) generates a
`semantic-uninstall-*.log` in the system temporary directory with 0600
permissions, and the path is shown; the log lives outside the instance, so a
purge does not remove it. Save it elsewhere if you need long-term retention.
The terminal shows a concise failure reason; the full traceback is written only
to the log.
The uninstall implementation is embedded in the entry point, and unit tests
verify that it matches `runtime/uninstall.py`, so the two do not drift apart
during maintenance.

## Network and distribution boundaries

- The installation package contains application binaries and Python Wheels, but
  not the operating system or a standalone Python interpreter.
  When the target machine lacks Python 3.13 / 3.10.19, uv still needs network
  access to download it; system package installation likewise needs the network.
  Therefore this is not a fully offline OS installation medium.
- The asset manifest contains `distribution_status: internal-only` and
  `license: pending`.
  The generated artifacts are explicitly marked as internal deployment
  snapshots; before any public release, the redistribution licenses of the
  source code, third-party Wheels, models and meshes must be reviewed — do not
  upload publicly by default just because there is a curl installation entry.
- `releases/`, `channels/` and the test staging directories are ignored by Git,
  so that several-hundred-MB artifacts do not enter source commits. Release
  packages should be stored in an artifact repository; the current scripts only
  generate them locally and do not upload automatically.

## Testing

```bash
python -B -m unittest discover -s tests -q
go test artifacts/gateway/main.go artifacts/gateway/main_test.go
bash -n artifacts/install.sh
# Real installation test: separate directory and ports 28180-28183; the test instance is stopped at the end
python -B artifacts/smoke_release.py \
  --package artifacts/releases/0.5.0-dev.20260910.3/linux-x86_64/semantic-0.5.0-dev.20260910.3-linux-x86_64.tar.gz \
  --port-base 28180
```

Integration verification should use a fresh directory and independent ports;
besides a successful installation, check login, the Web same-origin proxy,
Runtime/scene registration, the exact versions of the three Skills and password
preservation on re-run. Robots being truly ready, physical grasping and task
execution still require separate product acceptance and cannot be replaced by
"installation complete".

## English installer

The standalone English entry is `artifacts/install-en.sh`. After publishing the
site files, use:

```bash
curl -fsSL https://semantic.insightos.cn/install-en.sh | bash -s -- --install-system-deps
```

For local use: `bash artifacts/install-en.sh --help`. All existing download,
installation, configuration and safe offline uninstall options are supported.
Installer-owned prompts, progress, errors, welcome output and the installed
`semanticctl` are in English; external programs retain their original output.
The artifact source remains the same OSS endpoint; language does not select a
different mirror or imply broader platform support.

Regenerate after changing the canonical installer or its runtime modules:
`python artifacts/build_english_installer.py`. Verify with `--check`.
Translations live in `artifacts/installer.en.json`; do not edit generated
`install-en.sh` directly. See [site deployment](site/README.md) for publishing.

## Master entry point for build reproduction

The [three-platform build guide](../README.build.md) lists the actual scripts,
complete instructions, pinned versions and all component/dependency repository
entry points for glibc, musl and macOS.

For component YAML export, `-f` installation and local reconfigure, see the
[English README](../README.md#component-yaml-and-reconfiguration).
