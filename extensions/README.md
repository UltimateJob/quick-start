# Extension scenarios

**English** | [简体中文](README.zh-CN.md)

A base installation only prepares the base workspace. An **extension scenario** is a separate
payload published alongside—not inside—the immutable base artifacts; the installer pulls it on
demand once the base environment is ready. That keeps tens of gigabytes of downloads away from
people who do not need a scenario.

This directory is the entry point for extension scenarios. Each scenario has a **user manual**
built along the same path:

```text
① Environment preparation (prerequisites that cannot ship in a package)
② Install into the framework (install.sh --extension <id> or semanticctl extension install)
③ Reproduce in the web Studio (screenshots with red boxes around the controls to click)
```

## Scenarios

| Scenario | id | Contents | Manual |
|---|---|---|---|
| LIBERO | `libero` | robosuite 1.4, Franka and SmolVLA; six artifacts, about 11.5 GB | [libero/README.md](libero/README.md) |
| BEHAVIOR (Isaac Sim) | `isaac` | OmniGibson 3.9.2, R1 Pro and π0.5; six artifacts, about 99 MB, plus a 31 GB engine image and the licensed dataset you provide | [isaac/README.md](isaac/README.md) |

The two manuals are independent. **Read section 1 of the BEHAVIOR manual first** — its engine
image, licensed dataset and π0.5 policy service are not shipped in any package, and nothing runs
without them. The LIBERO artifacts are self-contained; following the manual is enough.

## How to enter

From the command line (the same entry script as the base install; it continues automatically once
the base environment finishes):

```bash
curl -fsSL https://semantic.insightos.cn/install.sh | bash -s -- \
  --extension libero --extension-project <PROJECT-ID> --install-system-deps
```

With a base environment already installed, the bundled manager can drive extensions on its own:

```bash
semanticctl extension list                 # list known extensions
semanticctl extension show libero          # view the manifest: artifacts, sizes, order, license
semanticctl extension verify libero        # download and verify only, no install (troubleshooting / acceptance)
semanticctl extension install libero --project <PROJECT-ID>
semanticctl extension remove libero
```

> **`semanticctl` is not on your PATH by default.** When the base install finishes it only prints
> `export SEMANTIC_HOME=<install-dir>` and `export PATH="$SEMANTIC_HOME/bin:$PATH"` and tells you to
> put those two lines in `~/.bashrc` / `~/.zshrc`. Before using a bare `semanticctl` in a **new
> terminal**, export both (the default install dir is `~/.local/share/semantic`; use your actual dir
> when you passed `--dir`), or call the absolute path
> `~/.local/share/semantic/bin/semanticctl`. Every `semanticctl` command below assumes this.

`--source oss|github` selects the channel (default `oss`). The manifest and its version pointer
always come from OSS; the GitHub Release is a mirror. Three LIBERO artifacts exceed the 2 GiB
per-asset GitHub limit and **fall back to OSS automatically** when you use the GitHub channel.

The source-build path (TUI stage 8) and the prebuilt channel **share one manifest**; only the
artifact source differs: the TUI builds from upstream sources locally, the prebuilt channel
downloads verified artifacts. Use the TUI when you need to change component versions; use
`--extension` when you only want to run the scenario.

## Three shared web steps

Installation only lands the artifacts in the framework. **After it completes you must still do the
same three things in Studio**, or the scene never enters the project and the robot never comes
online. Each step maps one-to-one onto the same numbered subsection in each scenario manual
(LIBERO §3.1–3.3, BEHAVIOR §3.1–3.3); LIBERO is used as the example below, so for scenario-specific
values (robot model, scene card, model version, ports) follow that scenario's manual.

### ① Scene configuration → add a compatible scene (manual §3.1)

Installation only registers the scene in the **scene catalog**; it is not added to the project
automatically, so add it once by hand:

1. In Studio, open **Scene → Project scenes** on the left and click **Add** (or **Browse scenes**
   when the panel is empty):

   ![Add in the project scenes panel](images/libero/step-1-scene-panel.png)

2. In the **Add compatible scene** dialog, search or scroll to the card you want, click it (multiple
   selection is allowed), then click **Add to Project**:

   ![Select a scene card and Add to Project](images/libero/step-2-add-scene.png)

**Done when**: back under **Project scenes** the scene is listed and its runtime row shows the right
runtime — `LIBERO / LIBERO-Pro` for LIBERO, `BEHAVIOR / OmniGibson` for BEHAVIOR. Do not generate
previews for everything: without limiting the scene, previews are generated for every initial state,
which is very slow. When free VRAM is below 6144 MiB the installer **automatically** skips previews;
to control it yourself, pass `--no-previews` to `semanticctl extension install`.

### ② Project content → bind the ability and model (manual §3.2)

Installation **imports** the ability and model into the project but **does not bind them to the
robot**. Without binding, the ability stays in `Standby` (`abilityPort: 0`) until it times out, the
Pilot stays `offline`, and the device page shows no executable robot.

1. In Studio, open **Project → Import project content** and scroll the dialog to the **Robot and
   model configuration** section at the bottom:

   ![Robot and model configuration in Import project content](images/common/step-2-bind.png)

2. On a robot card, click **Select ability / model** (to make the current choice the default for
   future robots instead, click **Set project default** in the top right);
3. In the dialog choose, in order, **robot model** → **ability (one implementation per role)** →
   **policy model**, then click **Save binding**;
4. Back on that robot's card, click **Apply now / retry** — this **stops and restarts that robot's
   components once** (the scene keeps its current state), so confirm the robot is idle first.

**Done when**: the card's "pending configuration" and "running model" agree and it no longer sits in
`Standby`. A project default only applies to **future first-time bindings**; each robot's own choice
is stored independently.

### ③ Device centre → add a Pilot (manual §3.3)

**Device centre** is the global view of robots, and a fresh environment has an empty device list.
Note that **"Add Pilot" does not add a robot directly**: it only mints a one-time join code, and the
robot is registered only after you run the launcher on the **robot host** and the launcher exchanges
that code for a credential — this is the "once you have the code, how does the robot get added?"
part.

1. Open **Device centre** from the top menu and click **Add Pilot**:

   ![Click Add Pilot in the device centre](images/common/step-3-devices.png)

2. The dialog shows a **one-time join code** (6 digits, valid about 5 minutes, claimable only once)
   and a launcher command; click **Copy command** to take both (do not commit the join code or the
   credential afterwards to a repository):

   ![Copy the one-time join code and launcher command](images/common/step-4-add-pilot.png)

3. On the **robot host**, run that command in the foreground and keep it running (replace
   `<robot-id>` with the actual robot):

   ```bash
   semantic-robot-instance start --config /etc/semantic/robots/<robot-id>/robot-deployment.yaml --join-code <JOIN-CODE>
   ```

   The launcher discovers the Server over the LAN (mDNS service `_semantic-server._tcp`; mDNS is
   often unavailable on container networks, so you may append
   `--server-http http://<server>:<server-http-port> --server-ws ws://<server>:<server-ws-port>/ws/pilot`,
   ports per the scenario's port table), exchanges the join code for that Pilot's dedicated credential
   and stores it on the robot host (in the instance directory's `connection.yaml`, mode `0600`), then
   starts **AbilityFramework → the seven ability classes → Pilot** in order, after which the Server
   reconciles and dispatches the expected robot skill.

4. Back in the dialog, click **Done** — it only closes the dialog; pairing completed the moment the
   launcher claimed the join code. After a moment the robot should appear in the device list with
   connection **online**.

Restarting the robot afterwards **no longer needs a join code** (the credential is already on the
robot host):

```bash
semantic-robot-instance start --config /etc/semantic/robots/<robot-id>/robot-deployment.yaml
```

> **Pilot online ≠ robot executable.** If the Pilot shows online but the robot is not executable,
> keep checking the expected/actual state of AbilityFramework, the seven ability classes and the robot
> skill, plus project occupancy — do not watch only the Pilot heartbeat.

## Directory convention (when adding a scenario)

An extension scenario is one versioned directory, `extensions/<id>/`:

```text
extensions/<id>/extension.json     # manifest source, parsed directly by the installer
extensions/<id>/README.md          # user manual (English)
extensions/<id>/README.zh-CN.md    # user manual (Simplified Chinese)
extensions/images/<id>/*.png       # screenshots used by the manual
```

`extension.json` decides *which artifacts are installed, where they land, in what order and what
prerequisites exist*; the manual covers *what the human must do first and how to accept the result
in the web Studio*. To add a scenario, follow the shape of these two files — no installer code
change is needed, because `semanticctl extension` reads the manifest by id and the channel layout
and verification discipline are identical for every scenario.

> **Read [`../docs/extensions.md`](../docs/extensions.md) before changing fields.** The manifest
> constraints are not style preferences: `semanticctl extension verify` checks them byte for byte
> (SHA-256, size, and the exact file set inside a package). The release flow
> (`build_extension.py` / `publish_extension.py`, the `extensions` section of `repo-versions.json`,
> and the OSS mutable allow-list) is documented there too.

## License

LIBERO and BEHAVIOR / OmniGibson are upstream third-party assets redistributed through this channel
under authorization. Datasets are obtained separately by the user under the upstream license
(**non-commercial academic research only**) and are not redistributed here; "downloadable" does not
mean freely redistributable. Per-scenario license terms are in each manual's License section.
