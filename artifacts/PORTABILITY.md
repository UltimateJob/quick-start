# Static artifacts and Linux distribution adaptation

[English](PORTABILITY.md) | [简体中文](PORTABILITY.zh-CN.md)

## This delivery

Internal artifact: `0.5.0-dev.20260910.3`, size 362387241 bytes.

SHA256: `ea6874612f8ac957adea6d2de18a4a6563b8a0acac67a7c042f88f1f18ba7fa8`.

This version replaces all application-native programs; the old dynamic programs are no longer copied into the Bundle. The source workspace, existing services,
the original repositories' `.output` and the xmake configuration were all left unchanged; the build was done in `artifacts/.build/`.

| Program | Build method | ELF check |
| --- | --- | --- |
| AbilityFramework | Original project `fwk-static` + third-party dependencies built statically from source, glibc toolchain | No PT_INTERP / DT_NEEDED |
| semantic-server | CGO + musl-gcc + `musl,netgo,osusergo` + external static linking | No PT_INTERP / DT_NEEDED |
| semantic / semantic-pilot / semantic-robot-instance | Same as above | No PT_INTERP / DT_NEEDED |
| semantic-web-gateway | `CGO_ENABLED=0` | No PT_INTERP / DT_NEEDED |
| uv | Kept the dynamic release version | Directly references at most GLIBC_2.17 |

The actual Go build parameters:

```bash
CGO_ENABLED=1 CC=musl-gcc go build -trimpath \
  -tags musl,netgo,osusergo \
  -ldflags '-linkmode external -extldflags "-static"' \
  -o /path/to/semantic-server ./cmd/semantic-server
```

`go-fitz v1.24.15` provides musl MuPDF static libraries, so there is no need to remove PDF functionality, nor to rely on
an older-glibc container to solve the Server's linkage problem. The `CGO_ENABLED=0` path was not chosen:
in that mode this version of go-fitz uses purego/dlopen, which does not mean there are no native dynamic-library dependencies.
`probes/pdf_static.go` actually tests generating a PDF, extracting text and rendering pages — not just running `--help`.

## Compatibility scope and verification

- Ubuntu 24.04 x86_64 host: full isolated installation of the new package, Web/API login, MuJoCo scene smoke,
  publication of three exact Skill versions, curl-pipe reinstall, password preservation and test-service shutdown all passed.
- Fedora 42 clean container: dnf auto-installation of dependencies and the full flow above passed.
- Debian 12 (glibc 2.36) clean container: apt auto-installation of dependencies and the full flow above passed.
- Debian 11 / glibc 2.31 container: the static Server's startup help, PDF text/rendering passed;
  AbilityFramework actual startup, resource API and embedded Web UI passed.
- Alpine 3.20: the static AbilityFramework version command and static MuPDF text/rendering passed;
  **this does not mean the whole Python/MuJoCo runtime stack supports Alpine**.
- The Debian 11 full-installation test was blocked by expired official bullseye-security metadata; reproduced over both HTTP/HTTPS.
  Validity checks were not disabled, signature verification was not disabled, and the host's mirror sources were not modified.
- Command generation, distribution detection and error handling for yum, pacman and zypper have unit tests;
  real-installation acceptance on those distributions has not been completed yet.

The current manifest's glibc 2.28 is the target baseline of the Python/Wheel stack, derived from the existing manylinux Wheels
and uv's compatibility requirements — not a promise that "all glibc >= 2.28 systems have been tested". The Python interpreter,
libstdc++/OpenMP, graphics drivers and Wheels all importing/starting successfully is what counts as usable; the installation flow performs these checks.
Only x86_64 packages are provided so far; no ARM64 artifact has been published. Robot/physical-hardware tasks and GPU rendering require separate acceptance.

## System dependency policy

The installer reads the ID/ID_LIKE of `/etc/os-release` and checks that the corresponding commands exist. Only an explicit
`--install-system-deps` invokes root/sudo installation. The target machine must still have bash and Python 3.10+ prepared first;
the curl-pipe entry point needs curl.

| Manager | Corresponding dependencies |
| --- | --- |
| apt-get | ca-certificates, zstd, libstdc++6, libgcc-s1, libgomp1, libegl1, libgl1, libgl1-mesa-dri |
| dnf / yum | ca-certificates, zstd, libstdc++, libgcc, libgomp, mesa-libEGL, mesa-libGL, mesa-dri-drivers |
| pacman | ca-certificates, zstd, gcc-libs, libglvnd, mesa |
| zypper | ca-certificates, zstd, libstdc++6, libgcc_s1, libgomp1, libEGL1, libGL1, Mesa-dri |

There is no automatic replacement of the system glibc, no addition of third-party repositories, no disabling of signature checks and no full-system upgrade.
Arch uses `pacman -S --needed` with the existing sync database, and the administrator must ensure the system is properly updated first;
it will not run `-Sy`, which would cause a partial upgrade, nor run `-Syu` on its own.
References: [Arch system maintenance](https://wiki.archlinux.org/title/System_maintenance),
[Fedora Mesa package](https://packages.fedoraproject.org/pkgs/mesa/),
[manylinux compatibility specification](https://github.com/pypa/manylinux).

## Reproducible checks

```bash
python -B artifacts/build_native.py
python -B artifacts/probes/ability_http.py artifacts/.build/native-static/AbilityFramework
python -B -m unittest discover -s tests -q
python -B artifacts/test_container.py --distro fedora \
  --package artifacts/releases/0.5.0-dev.20260910.3/linux-x86_64/semantic-0.5.0-dev.20260910.3-linux-x86_64.tar.gz
```

The container tests support `debian11`, `debian12` and `fedora`, and use one-shot containers by default — no host port,
device or Docker socket mapping, and no privileged/host-network. Logs and results are saved in
`.build/container-*/`. The Debian test containers use HTTPS addresses of the same official sources; the installer itself does not change sources.

This round's success reports: `.build/smoke-fawmicr0/smoke-report.json`,
`.build/container-fedora-njby9jeu/semantic/smoke-report.json`,
`.build/container-debian12-ro9_9p2c/semantic/smoke-report.json`.

Native build logs and ELF reports are in `.build/native-static/`; the archive contains `native-linkage.json`
and per-file SHA256. Static compilation does not remove the need to keep applying third-party security patches; rebuild and redistribute with each version.
