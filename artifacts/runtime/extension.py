# Copyright 2026 InsightOS
# SPDX-License-Identifier: Apache-2.0
"""Extension scene manifest: parse, verify and list what an extension needs.

An extension scene (LIBERO today, Isaac later) is an optional side-payload installed
*after* the base environment. It is never folded into the immutable base release:
the base payload is an exact verified file set, and the extension artifacts are an
order of magnitude larger (LIBERO is about 10.4 GB against 345 MiB).

See docs/extensions.md for the full design.

The manifest carries one role per artifact. A role decides where an artifact lands:

    runtime        local ``semantic install runtime --pack`` execution
    scene_catalog  Server component install
    robot_base     Server component install
    robot_ability  Server component install
    model          Server component install
    robot_skill    Server component install

Runtime goes first and the components follow in a fixed order: the Bundle is the
base that ability, model and skill are inserted into.

This module is deliberately dependency-free apart from the standard library and
``install_support``, and it must not import ``installer``: ``installer`` imports it.
"""

import hashlib
import json
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from install_support import Progress

SCHEMA_VERSION = 1

# One artifact may legitimately be huge; keep a ceiling so a bad manifest cannot
# fill the disk before the digest check runs.
ARTIFACT_LIMIT = 12 * 1024**3

COMPONENT_ORDER = ('scene_catalog', 'robot_base', 'robot_ability', 'model', 'robot_skill')
ROLES = ('runtime', *COMPONENT_ORDER)
# Roles whose bundle is the base the remaining components are inserted into.
BASE_ROLES = ('robot_base',)
PREREQUISITE_KINDS = ('probe', 'user_action')

MANIFEST_NAME = 'extension.json'
STABLE_POINTER = 'stable.json'


class ManifestError(ValueError):
    """A manifest is unusable; the message names the offending field."""


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as f:
        while block := f.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f'{field} 必须是非空字符串')
    return value


def _checksum(record, field):
    if not isinstance(record, dict):
        raise ManifestError(f'{field} 必须是对象')
    value = _text(record.get('sha256'), f'{field}.sha256').lower()
    if len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ManifestError(f'{field}.sha256 格式不正确')
    size = record.get('size')
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise ManifestError(f'{field}.size 必须是非零整数')
    if size > ARTIFACT_LIMIT:
        raise ManifestError(f'{field}.size 超出上限')
    return value, size


def _artifact(record, field):
    source = _text(record.get('url'), f'{field}.url')
    if urllib.parse.urlsplit(source).scheme not in ('https', 'http'):
        raise ManifestError(f'{field}.url 只支持 http(s)')
    checksum, size = _checksum(record, field)
    artifact = {'url': source, 'sha256': checksum, 'size': size}
    if 'license' in record:
        artifact['license'] = _text(record['license'], f'{field}.license')
    return artifact


def parse(text):
    """Validate a manifest and return it with the install order applied."""
    try:
        manifest = json.loads(text)
    except json.JSONDecodeError as error:
        raise ManifestError(f'清单不是合法 JSON: {error}') from None
    if not isinstance(manifest, dict):
        raise ManifestError('清单必须是 JSON 对象')

    version = manifest.get('schema_version')
    if version != SCHEMA_VERSION:
        raise ManifestError(f'清单 schema_version 必须是 {SCHEMA_VERSION}')

    identifier = _text(manifest.get('id'), 'id')
    title = _text(manifest.get('title'), 'title')
    if not all(c.islower() or c.isdigit() or c == '-' for c in identifier) or identifier.startswith('-'):
        raise ManifestError('id 只能是小写字母、数字与连字符')
    compatible = manifest.get('compatible_base')
    if not isinstance(compatible, str) or not compatible.strip():
        raise ManifestError('compatible_base 必须是非空字符串')

    runtime = manifest.get('runtime')
    if not isinstance(runtime, dict):
        raise ManifestError('runtime 段缺失')
    endpoints = runtime.get('endpoint')
    if not isinstance(endpoints, str) or not endpoints.startswith(('http://', 'https://')):
        raise ManifestError('runtime.endpoint 必须是 http(s) 地址')
    pack = _artifact(runtime.get('pack') or {}, 'runtime.pack')
    installation_id = _text(runtime.get('installation_id'), 'runtime.installation_id')
    if installation_id in ('native-mujoco', 'base'):
        raise ManifestError('runtime.installation_id 不能占用基础 Runtime 的标识')

    components, seen, roles = [], set(), set()
    raw_components = manifest.get('components')
    if not isinstance(raw_components, list) or not raw_components:
        raise ManifestError('components 必须是非空数组')
    for index, record in enumerate(raw_components):
        field = f'components[{index}]'
        role = _text(record.get('role'), f'{field}.role')
        if role not in ROLES or role == 'runtime':
            raise ManifestError(f'{field}.role 不在允许的取值内: {" ".join(ROLES)}')
        identifier_text = _text(record.get('id'), f'{field}.id')
        component = dict(_artifact(record, field), role=role, id=identifier_text,
                         previews=_previews(record.get('previews'), f'{field}.previews'))
        key = (role, identifier_text)
        if key in seen:
            raise ManifestError(f'{field} 重复声明 {role}/{identifier_text}')
        seen.add(key)
        roles.add(role)
        components.append(component)
    missing = [role for role in BASE_ROLES if role not in roles]
    if missing:
        raise ManifestError('components 缺少基座产物: ' + ', '.join(missing))
    components.sort(key=lambda item: COMPONENT_ORDER.index(item['role']))

    requirements = manifest.get('host_requirements') or {}
    if not isinstance(requirements, dict):
        raise ManifestError('host_requirements 必须是对象')
    gpu = requirements.get('gpu', 'optional')
    if gpu not in ('required', 'optional', 'forbidden'):
        raise ManifestError('host_requirements.gpu 只能是 required/optional/forbidden')

    prerequisites = manifest.get('prerequisites') or []
    if not isinstance(prerequisites, list):
        raise ManifestError('prerequisites 必须是数组')
    for index, record in enumerate(prerequisites):
        kind = _text((record or {}).get('kind'), f'prerequisites[{index}].kind')
        if kind not in PREREQUISITE_KINDS:
            raise ManifestError(f'prerequisites[{index}].kind 只能是 {" ".join(PREREQUISITE_KINDS)}')
        _text((record or {}).get('text'), f'prerequisites[{index}].text')

    ports = manifest.get('ports') or []
    if not isinstance(ports, list) or any(
            not isinstance(item, list) or len(item) != 2
            or any(not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535 for port in item)
            or item[1] < item[0] for item in ports):
        raise ManifestError('端口段必须是 [起始, 结束] 整数对，且范围合法')

    return dict(manifest,
                id=identifier, title=title,
                runtime=dict(runtime, pack=pack, installation_id=installation_id, endpoint=endpoints),
                components=components, prerequisites=prerequisites, ports=ports,
                host_requirements=dict(requirements, gpu=gpu))


def _previews(value, field):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ManifestError(f'{field} 必须是对象')
    scenes = value.get('default_scenes', [])
    if not isinstance(scenes, list) or any(not isinstance(item, str) or not item for item in scenes):
        raise ManifestError(f'{field}.default_scenes 必须是字符串数组')
    return dict(value, default_scenes=scenes)


def channel_url(base, *parts):
    """Join a channel base URL with path segments, keeping the query string."""
    base = base.rstrip('/') + '/'
    return urllib.parse.urljoin(base, '/'.join(urllib.parse.quote(p, safe='') for p in parts))


def stable_pointer(base, identifier):
    """The mutable ``stable.json`` for an extension; ``None`` when unreachable."""
    url = channel_url(base, 'extensions', identifier, STABLE_POINTER)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'Accept': 'application/json'}), timeout=30) as response:
            pointer = json.load(response)
    except (urllib.error.URLError, OSError, ValueError):
        return None
    version = (pointer or {}).get('version') if isinstance(pointer, dict) else None
    return version if isinstance(version, str) and version.strip() else None


def resolve_version(base, identifier, version=None):
    """Version to use: explicit request, else the channel pointer, else fail."""
    if version:
        return version
    version = stable_pointer(base, identifier)
    if not version:
        raise ManifestError('无法从通道解析 {} 的版本，请显式指定 version'.format(identifier))
    return version


def manifest_url(base, identifier, version):
    return channel_url(base, 'extensions', identifier, version, MANIFEST_NAME)


def load_manifest(base, identifier, version=None):
    """Download and parse an extension manifest. Download only; no artifacts yet."""
    version = resolve_version(base, identifier, version)
    url = manifest_url(base, identifier, version)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'Accept': 'application/json'}), timeout=30) as response:
            text = response.read().decode('utf-8')
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise ManifestError('通道上没有 {} {} 的清单'.format(identifier, version)) from None
        raise ManifestError('下载清单失败: HTTP {}'.format(error.code)) from None
    except (urllib.error.URLError, OSError) as error:
        raise ManifestError('连接通道失败: {}'.format(error)) from None
    manifest = parse(text)
    if manifest['id'] != identifier:
        raise ManifestError('清单 id({}) 与请求的 ({}) 不一致'.format(manifest['id'], identifier))
    return manifest


def render(manifest, base=None):
    """Human-readable summary; ``base`` adds the resolved download URL per artifact."""
    rows = [('扩展', manifest['title']), ('标识', manifest['id']),
            ('版本', manifest['version']), ('兼容基础版本', manifest['compatible_base']),
            ('Runtime', manifest['runtime']['installation_id']), ('Runtime 入口', manifest['runtime']['endpoint']),
            ('GPU', manifest['host_requirements']['gpu'])]
    pack = manifest['runtime']['pack']
    rows.append(('Runtime 包', _describe(pack, base)))
    for component in manifest['components']:
        rows.append((component['role'], f"{component['id']}  {_describe(component, base)}"))
    if manifest['ports']:
        rows.append(('端口段', ', '.join(f'{first}-{last}' for first, last in manifest['ports'])))
    prerequisites = manifest['prerequisites']
    if prerequisites:
        rows.append(('前置条件', '; '.join(f"{item.get('kind')}: {item.get('text')}" for item in prerequisites)))
    return rows


def _describe(artifact, base=None):
    text = f"{artifact['size'] / 1024**2:.1f} MiB  sha256={artifact['sha256'][:12]}…"
    return text + '  ' + artifact['url']


def verify(manifest, quiet=False):
    """Download every artifact and check its digest and size. Nothing is installed.

    Returns one ``(name, state, detail)`` row per artifact and raises on the first
    failure, so a caller can record the rows and still stop the install.
    """
    artifacts = [(manifest['runtime']['installation_id'], manifest['runtime']['pack'])]
    artifacts += [(f"{item['role']}/{item['id']}", item) for item in manifest['components']]
    rows, failures = [], []
    progress = None if quiet else Progress([name for name, _ in artifacts])
    try:
        for name, artifact in artifacts:
            if progress:
                progress.next(name)
            state, detail = _verify_one(artifact)
            rows.append((name, state, detail))
            if state != 'ok':
                failures.append(name)
    finally:
        if progress:
            progress.finish()
    if failures:
        raise ManifestError('存在校验失败的产物: ' + ', '.join(f'{name}: {state} ({detail})'
                           for (name, state, detail) in rows if name in failures))
    return rows


def _verify_one(artifact):
    url, expected, size = artifact['url'], artifact['sha256'], artifact['size']
    try:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/Path(urllib.parse.urlsplit(url).path).name
            _download(url, target)
            if target.stat().st_size != size:
                return 'size-mismatch', f'期望 {size} 实际 {target.stat().st_size}'
            actual = digest(target)
            if actual != expected:
                return 'sha256-mismatch', f'期望 {expected[:12]}… 实际 {actual[:12]}…'
            return 'ok', f'{size / 1024**2:.1f} MiB'
    except ManifestError as error:
        return 'download-failed', str(error)
    except (urllib.error.HTTPError, OSError) as error:
        return 'download-failed', str(error)


def _download(url, destination):
    """Stream ``url`` to ``destination``, stopping before a runaway manifest fills the disk."""
    received = 0
    with urllib.request.urlopen(urllib.request.Request(url), timeout=60) as response, destination.open('wb') as target:
        while block := response.read(1024 * 1024):
            received += len(block)
            if received > ARTIFACT_LIMIT:
                raise ManifestError(f'下载体积超过上限 {ARTIFACT_LIMIT / 1024**3:.1f} GiB')
            target.write(block)
    return received


def entry(args):
    """``semanticctl extension`` dispatch."""
    if args.extension_action not in ('list', 'show', 'verify'):
        raise SystemExit(f'尚未支持: extension {args.extension_action} (见 docs/extensions.md 的分阶段实施建议)')
    if args.extension_action != 'list' and not args.id:
        raise SystemExit(f'extension {args.extension_action} 需要扩展 id，例如 libero')
    if args.extension_action == 'list':
        base = args.base_url.rstrip('/')
        try:
            with urllib.request.urlopen(urllib.request.Request(channel_url(base, 'extensions', 'index.json'),
                        headers={'Accept': 'application/json'}), timeout=30) as response:
                index = json.load(response)
        except (urllib.error.URLError, OSError, ValueError):
            index = None
        if not isinstance(index, dict) or not index:
            print(f'通道 {base} 没有可用的扩展目录 (extensions/index.json)')
            return 1
        for identifier, item in sorted(index.items()):
            version = (item or {}).get('version') if isinstance(item, dict) else None
            print(f"{identifier}\t{(item or {}).get('title', '')}\t{version if isinstance(version, str) else '?'}")
        return 0
    manifest = load_manifest(args.base_url, args.id, args.version)
    if args.extension_action == 'show':
        for label, value in render(manifest):
            print(f'{label}: {value}')
        return 0
    if args.extension_action == 'verify':
        for name, state, detail in verify(manifest, quiet=args.quiet):
            print(f'{state}\t{name}\t{detail}')
        print(f'已校验 {len(manifest["components"]) + 1} 个产物。')
        return 0
    raise SystemExit(f'尚未支持: extension {args.extension_action}')


def register(parser):
    commands = parser.add_parser('extension', help='扩展场景: 清单查看与产物校验')
    commands.add_argument('extension_action', choices=['list', 'show', 'verify', 'install', 'remove'])
    commands.add_argument('id', nargs='?', help='扩展标识，例如 libero')
    commands.add_argument('--base-url', dest='base_url', default='https://oss.example.com/semantic',
                          help='发布通道地址')
    commands.add_argument('--version', help='覆盖 stable.json 指向的版本')
    commands.add_argument('--quiet', action='store_true')
    commands.set_defaults(extension=entry)
    return commands
