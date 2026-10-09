# Windows native porting checklist

[English](README.windows.md) | [简体中文](README.windows.zh-CN.md)

Dependency audit date: 2026-09-13; implementation progress updated: 2026-09-14. The audit baseline is `macos-v0.1.0-rc.3` and its pinned component commits.
The dependency audit below follows that baseline; implementation progress is recorded separately. The Windows x64 ZIP has passed full native CI, and the `windows-v*` tag workflow re-verifies it before publishing the preview package.
A physical Windows 11 desktop GPU still awaits separate acceptance.
For compiler diagnostics, source versions and PyPI file inspection see the [audit record](artifacts/windows/audit-2026-09-13.json).

Suggested first-release target: Windows 11 x64, installation by a normal user, local Server/Web/Pilot/AbilityFramework/MuJoCo,
sharing one bundled CPython 3.13 and NumPy 2.3.5. Robot, Simulation and Skill may keep isolated venvs,
but share the same Python base runtime. Windows ARM64, Windows Service, the optional LIBERO/Robosuite and a formal MSI can be extended later.
Running and installing must not depend on WSL, Docker, Git Bash, a pre-installed Python or a compiler.

## Implementation progress

The priority changes to the website and install scripts have been merged and deployed via
[quick-start PR #17](https://github.com/insightos-community/quick-start/pull/17); the macOS package has been released as `macos-v0.1.0-rc.4`.

| Component | Completed Windows work | Verification and to-do |
| --- | --- | --- |
| semantic-deployment | Instance lock, Job Object process tree, graceful-stop IPC with creation-time identity, temporary paths | [PR #6](https://github.com/insightos-community/semantic-deployment/pull/6) merged; Windows/Linux/macOS native contract tests pass. Real project startup and graceful release verified; [stop-fix PR #7](https://github.com/insightos-community/semantic-deployment/pull/7) merged |
| ability-scaffold | Native `ability.exe`, directly invoking the bundled Python; Windows packaging entry point | [PR #4](https://github.com/insightos-community/ability-scaffold/pull/4) and [PR #5](https://github.com/insightos-community/ability-scaffold/pull/5) merged; pack/unpack/execute of the native entry point and post-install wheel, and UTF-8 output tests pass |
| mujoco-runtime | Pydantic version alignment, cross-platform asset path checks, Windows graceful-quit event, native CI | [PR #10](https://github.com/insightos-community/mujoco-runtime/pull/10) merged; 72 Windows API/lifecycle tests, MuJoCo 3.4.0 physics stepping and wheel build pass; Linux/macOS regression passes |
| Semantic-Framework | CLI/Server/Pilot process, path and PowerShell ports; Windows `glfw` default backend | [PR #7](https://github.com/insightos-community/Semantic-Framework/pull/7) merged; Windows native build, real Server init/restart/graceful stop, PowerShell and PDF error-recovery tests pass; Linux/macOS regression passes |
| AbilityFramework | MSVC/xmake, Windows NIC/MAC/HostInfo, `.exe` entry point and path support | [PR #5](https://github.com/insightos-community/AbilityFramework/pull/5) merged; [PR #6](https://github.com/insightos-community/AbilityFramework/pull/6) merged and fixes the first-Task crash caused by virtual-inheritance pointer restoration; 25 Windows tests and 116 assertions pass, HTTP/SQLite restart with Chinese paths and bundled CRT verified; [Windows component pre-release](https://github.com/insightos-community/AbilityFramework/releases/tag/windows-v2.4.1-preview.2) available |
| r1pro-ability | 7 native Windows Ability packages, entry points and dependency version records | [PR #4](https://github.com/insightos-community/r1pro-ability/pull/4) merged; 78 tests pass, 1 real-scene test skipped; [component pre-release](https://github.com/insightos-community/r1pro-ability/releases/tag/windows-v0.4.0-preview.1) available; real-scene startup and graceful stop of the 7 Abilities verified |
| Pinocchio 3.9.0 | Windows build lock, EigenPy/Coal/HPP-FCL compatible dependencies, wheel/DLL packaging and Conda-free verification script | [PR #2](https://github.com/insightos-community/pinocchio/pull/2) merged; native compilation and FK/RNEA, URDF/mesh/collision and DLL checks on standalone CPython pass; [Windows component pre-release](https://github.com/insightos-community/pinocchio/releases/tag/windows-v3.9.0-preview.1) available |
| Ability-SDK-Python | Post-install wheel under the native entry point, IPC and lifecycle heartbeat integration tests | [PR #3](https://github.com/insightos-community/Ability-SDK-Python/pull/3) merged; lifecycle, IPC and entry-point teardown tests of the post-install wheel pass on Windows/Linux |
| quick-start | Native manager, port configuration/transaction rollback, local uninstall, offline ZIP assembly and full-scenario verification flow | [PR #23](https://github.com/insightos-community/quick-start/pull/23) merged; [PR #24](https://github.com/insightos-community/quick-start/pull/24) being integrated. 7 manager contracts and local uninstall pass; bundled-Python/UTF-8 file access and uninstall junction-rejection tests pass; [full-package CI](https://github.com/insightos-community/quick-start/actions/runs/34823853506) passed offline install/retry, two project startups with graceful release, port reconfiguration, local restart and data-preserving uninstall |

Machine-readable commit/CI records are in the [implementation record](artifacts/windows/progress-2026-09-14.json).

The MuJoCo pass results cover the API, physics stepping and a real depalletizing project startup. 7 Abilities, 3 Skills and Pilot are jointly ready and released gracefully. Windows desktop GPU and continuous RGB/depth rendering have not yet completed physical-machine verification.
A Windows venv's `python.exe` may be a redirector entry point; graceful-stop IPC must locate the actual interpreter —
`Popen.terminate()` must not be treated as a graceful stop.

Reproduce in semantic-deployment with Go 1.25.8 (likewise in Windows PowerShell):

```text
go test ./internal/ports/... -count=1 -timeout=2m
```

For reproducing the Windows install-management interface and the public wheel see the [development notes](artifacts/windows/README.md).

Per-component reproduction entry points:

- Framework: [Windows build and native validation](https://github.com/insightos-community/Semantic-Framework/blob/feat/windows-process-ports/docs/platforms/windows.md).
- Ability entry point: [MSVC build notes](https://github.com/insightos-community/ability-scaffold/blob/main/README.build.md#windows-native-launcher).
- MuJoCo: [Windows build and physics validation](https://github.com/insightos-community/mujoco-runtime/blob/main/README.build.md#windows-x64-native-validation).
- Pinocchio: [`ci/windows/build.ps1`](https://github.com/insightos-community/pinocchio/blob/feat/windows-release/ci/windows/build.ps1), with standalone-run validation and a component pre-release already provided.

## Implementation route and ports boundary

Pinocchio is a case of "Windows support already exists; what is needed is building and releasing for this project", not porting algorithms from scratch.
The organization already has [insightos-community/pinocchio](https://github.com/insightos-community/pinocchio); extend that fork directly.
The inspected 3.9.0 source already contains Windows Release, clang-cl and Python standalone CI paths,
and `pixi.toml` declares `win-64`, the Windows Python install directory and collision dependencies.
See the [existing CI](https://github.com/insightos-community/pinocchio/blob/2e5854965571237a17934e1baca13d856d053b3c/.github/workflows/macos-linux-windows-pixi.yml)
and the [build environment](https://github.com/insightos-community/pinocchio/blob/2e5854965571237a17934e1baca13d856d053b3c/pixi.toml).

Self-building is a two-step process: first reproduce the upstream Windows compilation/tests, pinning Python 3.13, NumPy 2.3.5 and full URDF/collision functionality;
then produce wheel/DLLs that install offline into the bundled Python, and test in a clean environment without Pixi/Conda activated.
Pixi can serve as a build tool, but the fact that tests run under it does not prove the installer also runs outside its environment.
For dependencies, first adopt build schemes the upstream already supports; only add standalone builds for libraries with a definite patch, version or release need — do not presume a full rewrite.

Framework and the supervisor should establish a ports/platform adaptation layer that centralizes operating-system differences.
Business code keeps the instance state machine, startup order, hold/stop evidence and error handling.

| ports responsibility | Unix adapter | Windows adapter | Common contract |
| --- | --- | --- | --- |
| Process-tree startup and reaping | POSIX process groups, wait, signals | Process handles, Job Objects, wait/exit codes | Only control processes it created or whose ownership is verified; guarantee child-process ownership; no residue after reaping |
| Request graceful stop | Application protocol or agreed signals | Application IPC; console events only where applicable | Requesting stop, receiving business stop evidence, and forced reaping must be three separate actions |
| Instance lock | flock | LockFileEx or named mutex | Mutual exclusion, non-blocking contention, recoverable after process crash |
| Process identity | PID, start time, executable path | Handle, creation time, image path | Avoid mistaking or killing a process after PID reuse |
| host command | POSIX shell adapter | Explicitly chosen PowerShell/cmd adapter | Clear argument and quoting semantics; timeout cancellation covers child processes |

Executable suffixes, venv layout, platform identifiers and the default render backend use centralized functions/configuration — they need not all be wrapped as interfaces.
Go code selects adapters via `linux`, `darwin`, `windows` build tags; no longer use `!darwin` to mean Linux.
Each caller's ports interface stays small and explicit; reusable low-level adapters may go into a separately versioned public Go package.
Do not let two repositories import each other's `internal`, and do not let Framework depend on the supervisor's business state machine.
AbilityFramework's C++ adaptation is implemented separately and follows the same process-lifecycle contract.

First migrate the current Linux/macOS implementation into adapters and pass the existing regression, then add the Windows adapter.
Contract tests must include retaining the interrupted/reconciliation capability when a stop is unconfirmed; `Close` must not imply an unconditional kill.
The owner, lifecycle, abnormal-exit policy and process-join timing of Job handles on Windows need explicit design.

| Work group | Relative effort estimate | Main uncertainties |
| --- | --- | --- |
| Pinocchio self-build release | Medium; the build route has a basis | Exact version combination, NumPy/Boost.Python ABI, DLL closure and running outside the build environment |
| Framework / supervisor ports | Core work | Stop protocol; how the state machine connects with OS process-tree/lock semantics |
| AbilityFramework | Medium; cannot be treated as just a compiler switch | POSIX permissions/network interfaces, MSVC compilation and child-process behavior |
| Ability entry points, pure-Python SDK, Web, static assets | Usually small | Paths, arguments, encoding and platform metadata |
| Installer | Medium | Windows file locking, version switching, admin-free installation and complete uninstall |
| MuJoCo/GLFW integration | Code changes expected small; validation needs its own line | Real graphics sessions, drivers, continuous frames and context lifecycle |

These are relative judgments made after a source audit — not already-achieved Windows build results or schedule commitments.

## Initial baseline audit (2026-09-13)

This section preserves the pre-porting diagnostics; for current implementation results see the implementation progress above.

| Check | Result | Impact on the port |
| --- | --- | --- |
| Framework Windows cross-compilation | Failed: `Setpgid`, `syscall.Kill` do not exist | Process platform implementations must be split; setting only `GOOS=windows` is not enough |
| semantic-deployment Windows cross-compilation | Failed: additionally `Flock`, `LOCK_EX` etc. | The supervisor, instance lock and process-identity checks must be adapted |
| Full third-party dependency resolution for Windows/3.13, wheels only | Failed: no usable wheel for `pin==3.9.0` | Pinocchio packaging is the primary dependency blocker |
| Resolution probe with Pinocchio and direct cmeel constraints temporarily removed | 38 packages resolved successfully | Only proves this subset of dependencies has candidates; it does not justify deleting robot dependencies or declaring installation success |
| Ability launch entry points | All 7 packages use `#!/usr/bin/env bash` | Even with the architecture tag still x86_64, they cannot execute directly on Windows |
| Runtime backend default value | Already Windows → `glfw` | The upper Framework and installer may still override it to `egl`; an end-to-end change is needed |
| Pydantic consistency | The three Skills pin 2.13.4; the Runtime still selects 2.11.5 on Windows | A consistent Windows constraint is needed to avoid repeating the macOS offline-installation failure |

Cross-compilation runs on a Linux host, using the actual source of the release baseline:

```bash
# Run in the Semantic-Framework and semantic-deployment repositories respectively
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build ./cmd/...

# Run in quick-start: currently expected to fail at pin==3.9.0
uv pip compile artifacts/macos/installer-requirements.in \
  --python-version 3.13 --python-platform x86_64-pc-windows-msvc \
  --only-binary :all: --generate-hashes -o /tmp/windows-probe.lock
```

The macOS requirements above are only used to check the existing version combination; ultimately a standalone Windows input file and lock file must be produced.

## Initial acceptance checklist (see the progress above for implementation status)

The original planning scope is preserved below; unchecked items do not mean everything is still unimplemented. For the checks actually passed per stage, the full-package checks not yet passed and the corresponding evidence, see the implementation record above.

## P0: dependencies and core processes runnable

### Python and math dependencies

The results below come from the PyPI file listings of the specified versions, checked against standard CPython 3.13 / `win_amd64` tags.
"Has a wheel" does not equal verified DLL loading or business behavior.

| Dependency | Current version | Windows x64 candidate artifact | To-do |
| --- | --- | --- | --- |
| MuJoCo | 3.4.0 | Has `cp313-cp313-win_amd64` wheel | Use the upstream wheel; test physics stepping and rendering |
| NumPy | 2.3.5 | Has `cp313-cp313-win_amd64` wheel | Verify the NumPy ABI with self-built Pinocchio/EigenPy |
| Ruckig | 0.19.4 | Has `cp313-cp313-win_amd64` wheel | Prefer reuse; test trajectory generation; self-build as a reproduction option |
| GLFW | 2.10.2 | Has `py2.py3-none-win_amd64` wheel | Check the bundled DLL and the OpenGL context |
| Pydantic / pydantic-core | 2.13.4 / 2.46.4 | Universal wheel / Windows cp313 wheel | Unify the constraints across Runtime, Robot and the three Skills |
| Pinocchio / libpinocchio | 3.9.0 | No matching PyPI Windows wheel | Establish a Windows native build and a relocatable wheel |
| EigenPy / Coal / libcoal | 3.12.0 / 3.0.2 / 3.0.2 | No matching PyPI Windows wheel | Build and verify together with Pinocchio |
| cmeel native dependencies | Boost 1.89.0, urdfdom 4.0.1, tinyxml2 10.0.0, console-bridge 1.0.2.3, Assimp 6.0.5, OctoMap 1.10.0, Qhull 8.0.2.1, zlib 1.3.2 | Currently no Windows candidates for these wheels | Determine source versions, feature switches and the Windows DLL/header release form |
| uvloop | 0.22.1 | No Windows wheel | Exclude via dependency platform markers, use Windows asyncio; no need to port uvloop |

- [ ] Pin the Windows CPython 3.13 standard ABI and the `uv.exe` distribution files, sources and SHA-256. Verify the full standard library, `venv`, SSL, SQLite and certificate reading. uv officially supports Windows x64. [uv platform notes](https://docs.astral.sh/uv/reference/policies/platforms/)
- [ ] Choose a relocatable full Python distribution that can create venvs. Do not directly assume the Python embeddable ZIP is equivalent to the current runtime; it does not include pip by default, and conventional pip dependency management is not an officially supported use case for it. [Python Windows distribution notes](https://docs.python.org/3.13/using/windows.html#the-embeddable-package)
- [ ] Build the Pinocchio dependency chain with the same MSVC toolchain and CPython/NumPy ABI, pinning Boost.Python, Eigen, EigenPy, Coal, URDF and mesh-import dependencies. The existing Pinocchio source already has Windows branches; what is missing is deliverables meeting this project's version combination, not Windows support in the library itself. [Pinocchio 3.9.0](https://pypi.org/project/pin/3.9.0/)
- [ ] Keep URDF and collision functionality. The Robot SDK actually calls `buildModelsFromUrdf`, `GeometryData` and collision detection; these capabilities must not be disabled in exchange for "it compiles". [Call site](https://github.com/insightos-community/robot-sdk/blob/59a1a8364c3d0330f1802c020e37544e0dbfa7c5/packages/r1pro/src/semantic_robot_sdk_r1pro/providers/local_kinematics.py#L53)
- [ ] Determine the wheel structure and METADATA dependencies: a self-built wheel must not keep requiring nonexistent Windows cmeel wheels; nor may we only copy DLLs while dropping dependency declarations.
- [ ] Collect direct and recursive dependencies of `.pyd`/`.dll`, handle DLL search directories, same-name library conflicts and VC Runtime deployment, and record actual load locations. During testing, clear build-tool and Conda/Pixi paths to ensure running does not depend on the build machine. [DLL search rules](https://learn.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-search-order), [Python DLL directory interface](https://docs.python.org/3.13/library/os.html#os.add_dll_directory)
- [ ] Produce a complete Windows offline wheelhouse and a hashed lock file; run `pip check`, URDF/mesh loading, FK/IK, collision and Ruckig numerical tests.

### Semantic-Framework and semantic-deployment

- [ ] Split POSIX implementations into build-tag-constrained files and add Windows implementations. Some existing `*_other.go` files use `!darwin`, which would misclassify Windows as Linux.
- [ ] Replace `Setpgid`, signaling negative PIDs, `Getpgid`, `Signal(0)` and `/proc/<pid>` checks; implement startup, liveness, identity verification, stop, timeout and log collection.
- [ ] Manage the process tree owned by this instance with Windows Job Objects or similar mechanisms; check child-process join timing and handle inheritance. Keep the existing "hold/stop first, reap after confirmation" order; when a stop is unconfirmed, retain the interrupted state — processes that must be kept must not be unconditionally killed by closing the Job handle. The abnormal-exit policy needs separate design and testing. [Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)
- [x] Wire semantic-deployment's instance `Flock` into Linux/macOS/Windows platform file locks; concurrent startup, abnormal exit and lock recovery covered — see PR #5 above. Other process platform interfaces remain to be adapted.
- [ ] Review all startup paths of the Runtime manager, Robot supervisor, Pilot Skill worker and CLI; unify `.exe`, `Scripts/python.exe`, argument arrays and UTF-8 handling.
- [ ] Adapt the host command tooling: the current `/bin/sh`, `setsid` and POSIX quoting cannot be used directly on Windows; define PowerShell/cmd execution semantics and cancellation behavior.
- [ ] Unify all backend selection to Windows `glfw`, with Web continuing to request `auto`; explicitly reject incompatible explicit backends and keep diagnosable errors.
- [ ] Verify the Windows builds and behavior of SQLite, the static Web gateway and file packing/unpacking; replace paths that depend on external GNU tar/zstd commands.

Source entry points: [simulation/launcher.go](https://github.com/insightos-community/Semantic-Framework/blob/6d524fe4dbdfceb2029f7468619723274465c976/internal/simulation/launcher.go),
[runtime_pack.go](https://github.com/insightos-community/Semantic-Framework/blob/6d524fe4dbdfceb2029f7468619723274465c976/internal/simulation/runtime_pack.go#L265),
[pilot/installer.go](https://github.com/insightos-community/Semantic-Framework/blob/6d524fe4dbdfceb2029f7468619723274465c976/internal/pilot/installer.go#L65),
[instance/runner.go](https://github.com/insightos-community/semantic-deployment/blob/ef9bbebf9a6d1f2c25350d575d242d52f29e8e42/internal/instance/runner.go).

### AbilityFramework, Abilities and SDK

- [ ] Add a Windows/MSVC configuration to xmake and pin dependencies; remove build-time assumptions about `date`, `python3` commands and unescaped source paths; verify paths with spaces.
- [ ] Adapt `getuid/getgroups/gid_t`, Unix execute-permission bits, and interfaces such as `arpa/inet.h`, `ifaddrs.h` and `ioctl`. Use Windows process/network APIs; cover the default NIC, MAC, mDNS and multi-NIC discovery.
- [ ] Add Windows HostInfo and unified architecture naming, replacing `uname` and `/etc/os-release`. OS/arch validation of packages, bundles and hosts must be consistent.
- [ ] Add native launch descriptions or lightweight `.exe` entry points for the 7 Abilities, directly invoking the bundled Python; pass the UUID, JSON configuration and `ABILITY_ROOT`; test argument quoting. Do not only change package names or architecture tags.
- [ ] Adjust Ability-SDK-Python's parent-process exit handling and self-exit logic; Linux `prctl` does not work on Windows, and Windows `SIGTERM` behavior cannot be treated as a POSIX graceful exit either.
- [ ] Update `ability-scaffold` so newly generated Abilities can use the same Windows launch protocol.
- [ ] Update the `ability-runtime` bundle template, Python executable path and Windows platform metadata; verify that paths read after installation contain no build-machine absolute paths.
- [ ] Run Robot SDK, Skill worker, JSON-RPC, heartbeat, repeated-startup, stop-failure retention and child-process cleanup tests.

Source entry points: [subprocessmgr.cpp](https://github.com/insightos-community/AbilityFramework/blob/b5e8e443d1a8f3911c19a43a3842dcbbe92b8cb1/src/subprocessmgr/subprocessmgr.cpp),
[discovery_utils.cpp](https://github.com/insightos-community/AbilityFramework/blob/b5e8e443d1a8f3911c19a43a3842dcbbe92b8cb1/src/util/discovery_utils.cpp),
[Ability Bash entry point](https://github.com/insightos-community/r1pro-ability/blob/76e670f0cb8874b12fadbeb9acc9a88da7fb9b9c/abilities/r1pro-navigation/bin/ability).

## P1: deliverable installer and simulation closed loop

### MuJoCo and display

- [ ] Test the existing `mujoco==3.4.0` wheel, DLLs, MJCF/URDF and the current depalletizing assets on Windows. Official MuJoCo already supports Windows. [Official notes](https://mujoco.readthedocs.io/en/3.4.0/programming/index.html), [wheel of the specified version](https://pypi.org/project/mujoco/3.4.0/#files)
- [ ] Modify the Runtime's Pydantic platform constraints and regenerate the lock file, ensuring the 2.13.4 required by the three Skills is consistent with the Windows Runtime.
- [ ] Verify `glfw` creating hidden windows/off-screen framebuffers, RGB/depth, continuous Web video streaming, and thread and context destruction; `headless=true` does not by itself prove the system needs no usable graphics environment.
- [ ] On a real logged-in Windows 11 desktop with graphics drivers, verify the first batch of promised NVIDIA/AMD/Intel configurations; record `GL_VENDOR`, `GL_RENDERER`, OpenGL version, resolution, frame rate and CPU/GPU usage separately.
- [ ] Separately check behavior under RDP, screen lock and disconnected monitors, and define the support boundary. The first version launches in a user session; Windows Service graphics sessions are verified separately.
- [ ] The GPU route prefers the graphics vendor's Windows OpenGL driver. A Mesa software fallback is an optional follow-up; there is no need to port the Linux musl libdrm/elfutils/whole Mesa build chain into a mandatory Windows dependency.

### quick-start and the website

- [ ] Add an `artifacts/windows` builder, standalone sources/requirements pinning, a Windows manifest and artifact platform identifiers.
- [ ] The first version outputs an offline ZIP, `install.ps1` and a native management entry point (candidate `semanticctl.exe`); installs into the user directory without administrator rights or Developer Mode.
- [ ] Split the `fcntl`, `/proc`, `killpg`, shell launcher, `bin/python` and platform detection of the existing [installer](artifacts/runtime/installer.py) and [uninstall](artifacts/runtime/uninstall.py) into Windows implementations.
- [ ] Replace assumptions that need special privileges, such as the `current` symlink; consider an explicit active-version pointer, copying or a verified junction scheme. Handle reparse points, case sensitivity, reserved file names, drive letters, Chinese characters/spaces, long paths and cross-drive moves.
- [ ] Reference the bundled Python when creating venvs; installation steps use the complete offline wheelhouse, avoiding dependence on system Python, PATH or a user-preinstalled pip.
- [ ] Implement start/stop/status/doctor/logs/configure/uninstall, listening on localhost by default; configure corresponding rules only when the user needs LAN access, keeping Windows' own software sources and proxy configuration.
- [ ] Running EXE/DLLs on Windows may lock files: switch versions after shutdown with checksums and rollback; uninstall preserves data; define upgrade/data-migration boundaries clearly.
- [ ] The download entry verifies tag, platform, size and SHA-256; safe extraction handles Windows path rules. Offline package imports undergo the same verification.
- [ ] Only after the GitHub Release is published, add the Windows option to the website selector, the Chinese and English READMEs and the PowerShell installation instructions; do not announce download addresses that do not exist yet.

## Repositories involved and release boundaries

| Repository/group | First-batch work | Deliverable |
| --- | --- | --- |
| Semantic-Framework, semantic-deployment | Windows processes, locks, paths, backends and tests | Server/CLI/Pilot/supervisor `.exe` |
| AbilityFramework | MSVC/xmake, system and network interfaces, lifecycle | EXE, necessary DLLs, tests and load reports |
| Ability-SDK-Python, ability-scaffold | Lifecycle and launch templates | Universal wheels/templates and Windows tests |
| r1pro-ability, ability-runtime | 7 native entry points, bundle paths/platform | Windows Ability packages, bundle |
| robot-sdk, robot-skill | ABI, URDF/collision, worker/Skill installation tests | Reusable Python packages; revised releases when necessary |
| mujoco-runtime | Dependency constraints, startup and GLFW rendering validation | Runtime wheel, validation report |
| semantic-web, semantic-docs, mujoco-asset | Keep `auto`, verify static asset paths, update documentation | Verified universal static assets; existing Releases reusable |
| pinocchio | Windows native dependency chain and wheel packaging | cp313 Windows wheel, dependency package/manifest |
| Existing assimp, tinyxml2, qhull, zlib forks | Add Windows builds when the dependency chain needs them | DLLs/development prefixes or wheels |
| Eigen, Boost, EigenPy, Coal, URDFDOM/headers, console_bridge, OctoMap | Pin sources and build order; the organization currently has no separate repositories under these names | Can be built by Pinocchio CI first; adopt into forks when patches need independent maintenance or a separate Release |
| ruckig, mujoco forks | Prefer reusing upstream Windows wheels; add processes only when patches/self-publishing are needed | Windows artifacts at pinned versions |
| quick-start | Offline installer, aggregated Release, website | Complete Windows installation package |

Suggested build order: base C/C++ dependencies → EigenPy/Coal/URDF → Pinocchio wheel → Robot dependency verification;
the Framework/deployment and AbilityFramework platform interfaces can proceed in parallel; assemble the installer once the above conditions are met.
Not every dependency needs a new fork, and not every universal wheel/asset needs to be republished.

## CI, acceptance and delivery stages

- [ ] Use pinned GitHub standard Windows runner images and toolchains for builds, unit tests, math/physics tests and offline-installation checks; avoid depending on `windows-latest` drift. [Runner specifications](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- [ ] Run graphics tests on a separate runner with a real Windows desktop and graphics drivers; success on a normal hosted runner cannot substitute for GPU/desktop validation. An existing 9700X + RTX 5060/5060 Ti Windows host is a candidate validation machine; actual results are subject to measurement.
- [ ] CI cleans/isolates pre-installed Python, Conda, compilers and DLL search paths, then installs the actual release ZIP; verify installation under conditions where downloading dependencies is not allowed.
- [ ] Create a depalletizing project from the scene catalog; wait for scene running, Runtime ready of `r1_pro_tote_gripper-1`, 7 Abilities healthy, Pilot online, and 3 Skills installed/enabled.
- [ ] Report physics stepping, Runtime ready, RGB/depth rendering and business tasks separately; do not substitute an HTTP health check for a full startup.
- [ ] Verify graceful release, repeated start/stop, failure diagnostics, concurrent installation, port conflicts, timeouts and abnormal process exit; after stopping, no own child processes remain and no other Python/applications are killed by mistake.
- [ ] Verify paths with Chinese characters and spaces, normal-user privileges, offline reinstallation, configuration/data retention, uninstall and necessary rollback.
- [ ] The release process creates a draft first, uploads and verifies assets, then goes public; supports idempotent recovery after network failures. Preserve sources, dependency locks, SHA256SUMS, DLL load reports and the full verification report.
- [ ] Keep regression for Linux glibc, musl and macOS to ensure the platform split did not change existing install/stop behavior.

| Stage | Completion criteria |
| --- | --- |
| A: base libraries and executables | Pinocchio math/URDF/collision tests pass; Framework, supervisor and AbilityFramework build and run on Windows |
| B: local project closed loop | Three-layer startup ready, 7 Abilities / 3 Skills normal, no residue after safe scene stop |
| C: installer preview | The actual offline ZIP passes install/reinstall/uninstall on a clean Windows 11; verification report published |
| D: graphics validation and formal distribution | The promised graphics-card/desktop combinations pass; add MSI/EXE packaging, code signing, Start Menu/uninstall registration as needed |

Stages A/B have passed; the full offline ZIP verification on a Windows Server 2022 standard runner has also passed, covering Chinese paths, 7 Abilities / 3 Skills / Pilot, restart after port reconfiguration, graceful release, local restart and data-preserving uninstall. Robot, Runtime and dynamically created Skill venvs share the CPython 3.13.15 base runtime. `windows-v*` tags trigger the same verification and publish the ZIP, SHA256SUMS and the report. Physical Windows 11 machines, GPU rendering and signing/MSI remain follow-up work.
