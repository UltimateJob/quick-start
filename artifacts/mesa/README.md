# Optional musl Mesa EGL runtime

[English](README.md) | [简体中文](README.zh-CN.md)

The original installer sets `MUJOCO_GL=egl` and uses the host system's EGL. A
system can provide EGL through Mesa drivers for Intel/AMD, or through NVIDIA's
vendor implementation; EGL is not the same thing as Mesa.

This directory provides a standalone musl Mesa build and a Python launch entry
point, wired into the installer's explicit `--musl` option. The default install
path remains glibc; see [Optional musl package](../musl/README.md) for Release
assembly and verification.

## Drivers and runtime

By default Mesa 25.2.7 is built with `llvmpipe,iris,crocus,radeonsi,nouveau`
enabled:

| GPU / use case | Mesa driver | Requirements |
| --- | --- | --- |
| CPU software rendering | llvmpipe | musl LLVM and other runtime libraries |
| Intel | iris / crocus | Supported model; host kernel driver, firmware, and DRM device permissions available |
| AMD | radeonsi | Supported model; host amdgpu/radeon driver, firmware, and DRM device permissions available |
| NVIDIA open-source path | nouveau | Host uses Nouveau; model, firmware, and performance must be validated separately |
| NVIDIA proprietary driver | System EGL with glibc Python | Not part of this musl Mesa build; glibc user-space drivers cannot be loaded directly into a musl process |

Mesa matches drivers to the actual device; `GALLIUM_DRIVER` is not forced by
brand. Nouveau cannot take over a device in use by the NVIDIA proprietary
kernel driver; this tool does not install or replace kernel drivers. This
component provides OpenGL/EGL rendering only; it does not include Vulkan, CUDA,
OpenCL, or GPU physics compute backends.

## Build

Download the [official Mesa 25.2.7 source](https://archive.mesa3d.org/mesa-25.2.7.tar.xz),
verify the SHA-256 checksum
`b40232a642011820211aab5a9cdf754e106b0bce15044bc4496b0ac9615892ad`,
then extract it to `mesa-25.2.7/` under the working directory. Run the
following commands from that working directory:

```sh
docker build -t insightos-mesa-musl:25.2.7 /path/to/quick-start/artifacts/mesa
docker run --rm --network=none --cpus=6 --memory=14g \
  -v "$PWD:/work" \
  -e MESA_SOURCE=/work/mesa-25.2.7 -e MESA_OUTPUT=/work/output \
  insightos-mesa-musl:25.2.7
```

`output` must not exist. Three compile/test jobs are used by default; set
`MESA_JOBS` to change this. `MESA_DRIVERS` explicitly selects the driver list
to build; llvmpipe should always be kept. The output includes `prefix/` plus
configure, compile, and upstream test logs. The base image is pinned by digest
and APK packages use the Alpine-configured mirrors; APK versions are not all
locked, so the actual version manifest must be retained and byte-for-byte
reproducibility is not claimed.

The prefix still depends on dynamic libraries such as LLVM, libdrm, and libelf.
Run in the same build environment:

```sh
python collect-runtime.py /work/output/prefix /work/output/runtime
```

This script checks ELF GLIBC symbol dependencies and collects external musl
libraries for local offline verification. The release process uses the
[locked dependency Release](../musl/releases.json) with its licenses, source
correspondence, and release manifest; this collection tool is kept for local
experiments. A static ELF dependency audit cannot replace actually loading
hardware drivers and verifying rendering.

## Selecting a backend and launching

Run `launch.py` with the **target application's own Python** so that probing
and the application use the same interpreter. The corresponding MuJoCo, NumPy,
PyOpenGL, and other dependencies must be installed for that interpreter first.

```sh
/path/to/musl/python artifacts/mesa/launch.py \
  --profile auto --mesa-prefix /path/to/output/prefix \
  --mesa-runtime /path/to/output/runtime --check

/path/to/musl/python artifacts/mesa/launch.py \
  --profile auto --mesa-prefix /path/to/output/prefix \
  --mesa-runtime /path/to/output/runtime \
  --report /path/to/render-report.json -- -m your_runtime_module
```

Everything after `--` is Python arguments; do not write the Python executable
again.

| profile | Behavior |
| --- | --- |
| `auto` | musl: iterates Mesa EGL devices, preferring the first successful hardware rendering, falling back to llvmpipe on failure; glibc: uses the system EGL |
| `mesa-gpu` | Requires musl Mesa hardware rendering to succeed; errors out otherwise — software rendering is not accepted as a stand-in for a GPU |
| `software` | Uses musl Mesa llvmpipe |
| `system` | Uses the system EGL and the user's existing vendor configuration, reporting the actual software/hardware rendering result |

With multiple GPUs, use `--device N` to specify the **EGL enumeration index**,
which is not the same as a CUDA index or PCI address. When a device is
specified there is no automatic fallback to another device or to software
rendering; do not combine with `software`. `system` mode preserves the host
vendor library configuration; bundled Mesa mode clears conflicting driver
override variables. The library search order is Mesa prefix, the application's
existing `LD_LIBRARY_PATH`, then the Mesa-collected external dependencies, so
that shared library versions already pinned by the application (such as zlib)
are preserved. The configuration should be chosen before the application
starts; restart the process to switch — it cannot be switched in a process that
has already imported MuJoCo.

Each candidate device completes RGB/depth rendering in an independent
subprocess, recording the OpenGL vendor, renderer, version, actual library
paths, and failure reasons. A single probe times out after 30 seconds. The
`software` field in the output indicates that a software renderer such as
llvmpipe/softpipe was detected; hardware acceleration is not inferred from
`MUJOCO_GL=egl`.

When testing AMD/Intel in a container, additionally pass through an accessible
`/dev/dri` device; a container without the device is used to verify software
fallback. Regular users also need the corresponding render/video group
permissions on the host.

## Local verification (2026-09-11)

| Check | Result |
| --- | --- |
| Source build of all five Gallium drivers | Succeeded; Mesa upstream tests 72 passed, 0 failed |
| Backend selection and dependency priority tests | 9 passed |
| Mesa dynamic dependency audit | 18 ELFs with no GLIBC symbol version requirements; 13 external musl libraries collected |
| AMD real-machine headless rendering | Ryzen 9 9950X iGPU, radeonsi, OpenGL 4.6; RGB/depth/physics checks passed |
| Automatic fallback without GPU | llvmpipe, OpenGL 4.5; RGB/depth/physics checks passed |
| Single-Python joint test | Both rendering modes passed the joint MuJoCo 3.4.0, Pinocchio 3.9.0, Coal 3.0.2, Ruckig 0.19.4 checks |

The joint test used a fresh, network-disconnected Python 3.13 Alpine container
with NumPy 2.3.5; no host graphics libraries were mounted, and the AMD test
only passed through the corresponding DRM device. The actually loaded Mesa
paths were checked, and Assimp, Qhull, TinyXML2, and zlib were verified to load
from the project's published Release directory. Intel and Nouveau currently
only have source-build and upstream test results — **not yet verified on real
hardware**. The NVIDIA proprietary EGL path was not covered by this round of
verification and has not become a musl-compatible path.

The full local source build reused the existing MuJoCo musl toolchain to
supply Intel compile dependencies; the standalone Dockerfile in this directory
has completed image build and a Meson configuration check with the same
configuration. The Mesa prefix is about 47 MiB and the collected external
dependencies about 177 MiB, still dynamically linked. The first joint test
found Mesa's zlib overriding the version pinned by the application; after
adjusting the load order both modes passed re-testing. These component tests
do not mean the full installer, all business scenarios, or GPU performance
acceptance is complete.

## References

- [Mesa EGL driver architecture](https://docs.mesa3d.org/egl.html)
- [Mesa driver environment variables](https://docs.mesa3d.org/envvars.html)
- [NVIDIA proprietary driver system requirements](https://download.nvidia.com/XFree86/Linux-x86_64/580.76.05/README/minimumrequirements.html)

## Reproduce from source and Releases

See the [three-platform build guide](../../README.build.md) for complete local/CI commands, pinned versions, output paths and all component/dependency repository recipes.
