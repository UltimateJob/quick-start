# Aliyun OSS publishing

[English](OSS.md) | [简体中文](OSS.zh-CN.md)

Real download root path: `https://insightos-artifacts.oss-cn-shanghai.aliyuncs.com/semantic`.
Endpoint: `https://oss-cn-shanghai.aliyuncs.com`; region: `cn-shanghai`.

The credential configuration lives outside the repository: `~/.config/semantic-artifacts/oss.env` (directory 0700, file 0600).
The client only parses KEY=value and does not execute shell; it rejects in-repository credentials, symlinked credentials and files with overly broad permissions.
Do not put AccessKeys into command arguments, READMEs, install scripts or release archives.

## Initial release record

The following is the historical record of the first public release, .3; for the current release version and the latest acceptance results see [VERIFICATION.md](VERIFICATION.md).

Version `0.5.0-dev.20260910.3`, 362387241 bytes, SHA256:
`ea6874612f8ac957adea6d2de18a4a6563b8a0acac67a7c042f88f1f18ba7fa8`.

```text
semantic/
├── install.sh
├── channels/stable.json
└── releases/0.5.0-dev.20260910.3/linux-x86_64/
    ├── semantic-0.5.0-dev.20260910.3-linux-x86_64.tar.gz
    ├── semantic-0.5.0-dev.20260910.3-linux-x86_64.tar.gz.sha256
    ├── manifest.json
    └── release.json
```

At the user's explicit request, this batch of six objects was changed from private to **public-read (anonymously readable, writes require authorization)**.
The Bucket's original public-read setting was not changed, and no other versions or objects were touched. The original artifact content and the internal-only /
license-pending markers were not changed; authorizing public read does not mean the third-party asset license review has been completed.

## Public installation entry point for China users

```bash
curl -fsSL https://insightos-artifacts.oss-cn-shanghai.aliyuncs.com/semantic/install.sh | \
  bash -s -- --yes --install-system-deps
```

You may append `--dir /absolute/path` or port parameters. No AccessKey, signed ticket or GitHub access is needed;
an ordinary public URL has no one-hour signature expiry. The global GitHub Releases entry point is not configured yet.

## Client

Uses the official OSS Python V2 SDK (version 1.4.0 in this verification), run only on the build/release machine:

```bash
# Only check Bucket permissions
uv run --no-project --with alibabacloud-oss-v2==1.4.0 \
  python artifacts/oss_client.py check

# Verify and publicly upload the given version, updating the stable channel last
uv run --no-project --with alibabacloud-oss-v2==1.4.0 \
  python artifacts/oss_client.py publish --version 0.5.0-dev.20260910.3 --allow-public-internal-assets

# Re-issue the ticket after expiry without re-uploading the installation package
uv run --no-project --with alibabacloud-oss-v2==1.4.0 \
  python artifacts/oss_client.py ticket --version 0.5.0-dev.20260910.3
```

Configuration fields: OSS_REGION, OSS_ENDPOINT, OSS_BUCKET, OSS_PREFIX, OSS_DOWNLOAD_BASE,
OSS_ACCESS_MODE, OSS_SIGNED_URL_TTL, OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET.
Use `--config /path-outside-repo/oss.env` to switch configurations.

Uploads use a file whitelist and do not recursively upload artifacts or the workspace. Local SHA256/size are verified before upload,
and the remote length, SHA256 metadata and object ACL are checked after upload. Same-version different-content overwrites are rejected; identical content is verified then skipped.
Only install.sh / stable.json carrying this client's management marker may be updated. Before updating, the old file is read and verified via a GET ETag conditional,
backed up to `~/.config/semantic-artifacts/backups/` (0600) outside the repository, and written only after re-checking the ETag.
OSS PutObject does not support the `If-Match` conditional write this client attempted (it actually returns 400 NotImplemented);
so this is not an atomic CAS. This machine serializes publishing with a file lock; multi-machine publishing must still be serialized by operations scheduling.
For the interface parameters see the [official OSS PutObject documentation](https://www.alibabacloud.com/help/zh/oss/developer-reference/putobject).
Each run by default writes a log without credentials or signed URLs to `~/.config/semantic-artifacts/logs/` (0600).
It does not automatically upload configurations, signed tickets, logs or source code, and does not modify the Bucket ACL.

## Optional private one-click installation (no longer the current default entry point)

On a private-mode release or an explicit ticket command, the client generates two files outside the repository:

- `~/.config/semantic-artifacts/download/download.json`: time-limited GET URL, version, SHA256, expiry time.
- `~/.config/semantic-artifacts/download/install-current.sh`: reads the ticket, downloads and verifies the entry point, then runs the installation.

```bash
bash "$HOME/.config/semantic-artifacts/download/install-current.sh" --yes
# You may further add --dir /absolute/path, --install-system-deps, ports and other install options.
```

The default validity is 3600 seconds. The installation target machine needs no AccessKey; the ticket and entry point must be delivered to the target machine by secure means,
and on that machine either regenerate the correct local ticket path or run directly:

```bash
bash install.sh --ticket /absolute/path/download.json --yes
```

The install.sh here must come from a trusted source; the generated install-current.sh verifies the entry point's SHA256 first.
A ticket carries temporary download permission, and its holder can download the artifact before it expires; treat it as a secret file — do not commit it to Git or upload it to the Bucket.
The entry point does not pass the long-term AccessKey to the target machine. Tickets must be re-issued after long-term key rotation.

The out-of-repo configuration OSS_ACCESS_MODE has been changed to public-read. To subsequently publish artifacts still marked internal-only,
you must still explicitly pass `--allow-public-internal-assets`. The client does not silently migrate existing objects' ACLs during a normal upload;
the ACL migration of these six objects was a separate operation after the user's explicit authorization.

Official references: [OSS Python V2 SDK](https://www.alibabacloud.com/help/en/oss/developer-reference/2-0-manual-preview-version/),
[time-limited signed download](https://www.alibabacloud.com/help/en/oss/developer-reference/download-an-object-using-a-signed-url-generated-with-oss-sdk-for-python-v2).

## Verification record

- The artifact, checksum files, both version manifests, the stable channel and install.sh have been changed from private to public-read;
  anonymous HTTPS read verification passed. The ACL operation log is outside the repository at `logs/oss-public-read-tkl1w6k8.log`.
- Downloaded the entire archive through the real signed entry point; SHA256 and per-file verification passed; initialization of a new directory, the Python environment,
  and the Native MuJoCo scene smoke passed. This run used --no-start; Server/Web or a real Robot was not started.
- The test instance was cleaned up by the uninstaller after verification; no existing deployment was involved.
- Long-term credentials were never copied into the source tree or the release whitelist; temporary tickets are also stored only outside the repository.
