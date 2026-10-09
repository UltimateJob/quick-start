# Verification of this release package

[English](VERIFICATION.md) | [简体中文](VERIFICATION.zh-CN.md)

- Current static artifact: `0.5.0-dev.20260910.11`; acceptance of the latest uninstall/terminal-occupancy fixes is at the end of this document; for the static-linkage baseline see [PORTABILITY.md](PORTABILITY.md).
- Current unit tests: 149 passed; the .11 full installation and CLI uninstall passed in an isolated Debian 12 container. Ubuntu 24.04 and Fedora 42 were verified on earlier versions.
- The earlier .6 website curl-pipe download, progress, LAN configuration and interactive cancellation verified; the website's four screen-size layouts, copy buttons and script hashes passed.
- Historical OSS release: version `.3` and the install entry point were uploaded to insightos-artifacts / the semantic prefix;
  initially published as private; the signed entry-point real download, SHA256, initialization and MuJoCo smoke passed.
  The user then explicitly authorized public read: the six release objects were changed to public-read; the Bucket and other objects were not modified;
  anonymous GET of the entry point/manifest/checksum files returns 200, Range GET of the installation package returns 206 with the correct total size, and the curl-pipe help command passed.
  Credentials/signed tickets live only outside the repository (0600); an actual credential scan of 52 candidate source files passed. See [OSS.md](OSS.md) for details.
- The new install.sh embeds an offline uninstaller — no need to rebuild or download old artifacts. 20 new uninstall tests cover data preservation,
  purge, dry-run, path/mount-point protection, active-process blocking, PID reuse, stop timeout, the install lock and pipeline invocation.
- Full uninstall integration verification: create an isolated instance with the `.3` artifact → default uninstall → same-version reinstall (database and password preserved)
  → pipeline purge — passed. Only the test instance was deleted; results and logs are at
  `.build/uninstall-smoke-zog3zn25/report.json`, `.build/uninstall-smoke-zog3zn25/smoke.log`.

The following preserves the historical verification record of the previous dynamic artifact and does not represent the current download channel:

- Historical internal version: `0.5.0-dev.20260910.2`
- Historical file: `releases/0.5.0-dev.20260910.2/linux-x86_64/semantic-0.5.0-dev.20260910.2-linux-x86_64.tar.gz`
- Size: 360705196 bytes (about 344 MiB)
- SHA256: `557cfb48a0d0d5068dc770d19fc52d9e10ea023a247864a581735d2b6a8dafd8`
- Environment: Ubuntu 24.04 x86_64; dedicated install directory, dedicated ports; not a clean-VM test.

## Passed

- 70 Python regression tests, including checksum corruption, out-of-bounds archives, symlinks, pipeline arguments, password-file
  permissions, PID-reuse protection, and ports in TIME_WAIT not being misjudged as listening conflicts.
- Go Web gateway tests: static files, SPA routing, HTTP/WS route proxying, hidden-file protection.
- `bash -n artifacts/install.sh`, `git diff --check`.
- Actually completed a full installation from a local archive, rebuilt the Robot Python environment and imported the Ability dependencies.
- `semantic runtime install` completed a Native MuJoCo real-scene smoke with the official Pack.
- The new Server initialized a dedicated database and random password; logged in through the Web same-origin proxy.
- Published and queried grasp-object 0.4.23, semantic-navigation 0.4.7, place-object 0.4.42.
- Actually executed `curl | bash` against a local HTTP mirror: re-download, SHA256 verification, unpacking and repeated installation.
- Repeated same-version installation preserves the password; at the end of the test only the Server/Web created by the test installer were stopped.

The detailed test report is at the machine-ignored directory `.build/smoke-jggxasvv/smoke-report.json`; logs and the newly created
test database also remain in that dedicated directory. The existing source workspace's 8080/3000 services were not stopped or replaced.

## Not claimed as done

No verification of apt auto-installing dependencies on another clean OS; no public HTTPS hosting, no code-hosting-platform Release
upload, no cross-version data migration, no systemd boot startup, no LLM invocation, no Robot grasping task, and no full physical-product acceptance.
Asset licensing still needs review; the release package is for internal deployment only. No existing Git tag was moved.

The first version used the Runtime repo's old authoring sample; real testing exposed a `pose` field compatibility issue; it has been switched to
a source scene template of the Framework's current schema. The old test package is isolated in `.build/` and is not in the final release directory.
# 2026-09-10: LAN and installation experience (.6)

- Released version: `0.5.0-dev.20260910.6`; package SHA-256: `27731775192b55212fd76b1a5ccdd514fe0862588b7c0ccfe22f8b6e99e5eb3e`.
- `python -B -m unittest discover -s tests`: 131 passed.
- Python 3.10 artifact-related tests: 71 passed, including passwords written only to the terminal in a real PTY, never to redirected output.
- Full installation in an isolated Debian 12 container, health checks, Web SPA, login API, 3 Skill versions, MuJoCo scene smoke and idempotent reinstall passed.
- Both the .6 new instance and the .4 old instance verified `--configure-existing` switching to LAN and back to loopback; the API was requested through the real NIC IP after the Web gateway.
- The old-instance test confirmed the business version, `files.json` and admin password remain unchanged; no database was upgraded or migrated.
- Desktop files pass `desktop-file-validate`; tests cover Chinese desktop paths, instance paths containing spaces, not overwriting modified/symlinked entries, and uninstall cleaning only unmodified entries.
- Automatically skipped when there is no desktop environment; no real-browser click testing was performed on a user's actual desktop, and desktop environments may require "Allow launching".
- The PNG is SHA-256-identical to the user's original image; the three ASCII outline sizes and terminal-cell line wrapping passed tests.
- Container test logs: `.build/container-debian12-i47jhhzl/container.log` (.6), `.build/container-debian12-nrr3gd__/container.log` (.4 + .6 management tools).
- The internal .5 candidate was intercepted by the container test (importing a helper module produced an unlisted pycache) and was not released; .6 disables bytecode writing and adds a regression test.

## 2026-09-10: Form hierarchy and refresh (.8)

- Release package SHA-256: `3b42b709e9f64271515648ab12a1fa5f8212f121319cd72a2d882cf62d298a2b`.
- 136 unit tests passed; 19 experience tests passed under Python 3.10.
- A real 80×24 PTY verified that after success only the welcome page, the terminal inline password, category colors and old-task clearing are shown.
- Covered Chinese label/continuation-line alignment, wrapping at 19/31/39/63/79 columns, compact small icons, failed tasks retained, and NO_COLOR / dumb / redirected degradation.
- Does not send CSI 3J and does not clear the shell history scrollback; only the current viewport is refreshed on interactive terminals.
- .8 Debian 12 container verification of full installation, SPA/login, MuJoCo smoke, Skill versions, idempotent reinstall and LAN/loopback management switching passed.
- Container log: `.build/container-debian12-mlxfgikw/container.log`.
- All three management modules in the release archive match the tested workspace source; non-interactive logs contain no passwords.
- The OSS default channel and semantic.insightos.cn have been updated to .8; the online script hash, page resources, four browser layouts and the website's real pipeline configuration form/cancel verification passed.

## 2026-09-10: sudo authorization before progress refresh (.9)

- Release package: 362899026 bytes, SHA-256 `50be9a117ee0899759bfd1ffde3606a0a00f4f5c2781230486c94f47b41a3999`.
- Full unit tests: 142 passed; Python 3.10 artifact-related tests: 82 passed.
- A real 80×24 controlling terminal + piped stdin, using a fake sudo that neither elevates nor runs a real package manager, verified:
  the authorization prompt precedes the progress refresh, the password is neither echoed nor logged, failed authentication does not enter dependency installation, and subsequent commands carry `sudo -n`.
- Unit tests cover root / already-cached authorization skipping, missing sudo, no controlling terminal, permission-check timeout, authorization preceding panel creation,
  START log flushing before subcommand launch, and failure return-code recording. The development machine's real sudo cache was not cleared.
- An isolated Debian 12 container completed a real system-dependency installation (root branch), full deployment, MuJoCo scene smoke,
  SPA/API login, three Skill versions, idempotent reinstall and LAN / loopback management switching.
- Container log: `.build/container-debian12-wisdsysz/container.log`; the dependency log confirms the permission and command were recorded before apt-get started.
- The three management modules in the archive match the tested source; `bash -n artifacts/install.sh` and `git diff --check` passed.
- work22's real PAM / sudo policy and user password entry still need the user to retest; its original panel.py processes were not touched.
- The OSS default channel and the website version have been updated to .9; the website script matches the local SHA-256, and the four browser layouts and resource checks passed.
  The website's real `curl | bash` completed the .9 download, verification, configuration form and cancellation in a PTY, without starting local system-dependency installation.
  The pre-update website backup is at the server `semantic-site/backup.sudo.7tbEi0kx`.

## 2026-09-10: Text welcome page, LAN by default and Web port configuration (.10)

- Release package: 362898683 bytes; SHA-256 `9d859153eb614b517c7005fbc9edf113df63ac187cc1227afdfbd706ca7cf482`.
- 145 unit tests passed; 85 Python 3.10 artifact-related tests passed; bash syntax and diff whitespace checks passed.
- The terminal welcome page no longer loads/draws the ASCII art; the 80×24 text layout and the original desktop PNG icon regression passed.
- New installations default the Web listen address to 0.0.0.0, actually verified that the API can be requested via loopback and the container NIC IP without passing --lan.
  API/WS remain local-only; an explicit --web-host overrides the default, and old instances without network parameters keep their original configuration.
- configure supports --web-port; invalid/duplicate/occupied ports are rejected before the existing Web is stopped.
- Debian 12 actually tested full installation, MuJoCo smoke, login/Skills, reinstall; then switching LAN / loopback and the new Web port.
- Separately verified a .9 business instance using the .10 management tools to switch network and port; the original business version, files.json, password and Server process identity were all preserved.
- Two sets of logs: `.build/container-debian12-bhh6mzfl/container.log` (.10 new installation),
  `.build/container-debian12-a356174a/container.log` (.9 + .10 management tools).
- The three management modules in the release archive match the tested source. Pre-update site backup: `semantic-site/backup.textlan.Zemrv67Q`.
- The OSS channel and website updated to .10; the online script hash matches the workspace. The four browser layouts and resource security checks passed.
  After the website's real curl-pipe download/verification, the configuration form shows `0.0.0.0:3000` by default; the test cancelled at the confirmation and did not modify the development machine's system.

## 2026-09-10: Deleted terminal working directory wrongly blocking uninstall (.11)

- User process information confirmed: the blocking PID is Bash, whose cwd is the instance logs directory and already deleted — not Robot/Runtime.
- The fix checks the inode link count: a deleted cwd does not block uninstall; instance executables/command arguments still in use by processes are not ignored.
  Real directories (including ones whose names end in ` (deleted)`) remain protected, with the PID, process name, reason and cd operation shown.
- 149 unit tests passed; 89 Python 3.10 artifact tests passed; a real Bash stays alive in a deleted cwd,
  the test instance is still uninstallable, and no signal was sent to that Bash. Real directories and still-running instance programs correctly block deletion.
- Added semanticctl uninstall / --dry-run / --yes / --purge; status explicitly shows Server/Web and other occupants.
  Terminal failure output states a concise reason, with the full traceback kept in the external 0600 uninstall log.
- Full container installation, MuJoCo, Skills, Web login, idempotent reinstall and network/port configuration passed; log
  `.build/container-debian12-to9tg1j_/container.log`.
- Then, as UID 1000, ran the installed semanticctl's status, uninstall --dry-run and uninstall --yes on that test instance,
  confirming the programs were deleted while the database and password stayed unchanged. Only the test instance programs generated this time were cleaned up; configuration/data/logs remain in the test directory, and the programs can be restored by reinstalling the same version.
- Release package 362898821 bytes, SHA-256 `3f37f29a1820a2231dc2c800f8568b8b4a407c9d01be9a81debc2a58270f6bf5`.
  The three management modules in the package and the uninstaller embedded in the entry point match the workspace source; bash syntax and diff whitespace checks passed.
- The OSS channel, website script and version have been updated to .11; the four browser layout/resource checks passed; the online script is byte-identical to the local one.
  Using the script downloaded from the website, a pipeline uninstall was executed against the isolated fixture with a real Bash kept in a deleted cwd: uninstall succeeded, the Bash stayed alive,
  and the test data was preserved. No processes or instances of work22 were touched. The pre-update website backup is `semantic-site/backup.uninstall.WcPuxtbi`.
