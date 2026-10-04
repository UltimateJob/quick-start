# Copyright 2026 InsightOS
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import hashlib
import importlib.util
import json

def digest_of(body):
    """Digest of an in-memory payload, so tests can build a self-consistent manifest."""
    return hashlib.sha256(body).hexdigest()

from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('artifact_extension', ROOT/'artifacts/runtime/extension.py')
extension = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extension)

MANIFEST = {
    'schema_version': 1,
    'id': 'libero',
    'title': 'LIBERO 仿真场景',
    'version': '0.1.0',
    'compatible_base': '>=0.5.0',
    'runtime': {
        'installation_id': 'local-libero-robosuite-1.4',
        'endpoint': 'http://127.0.0.1:8092',
        'pack': {'url': 'https://example.invalid/libero.runtime.tar.zst', 'sha256': 'a'*64, 'size': 1932735283},
    },
    'components': [
        {'role': 'robot_skill', 'id': 'vla-manipulation',
         'url': 'https://example.invalid/vla-manipulation.zip', 'sha256': 'b'*64, 'size': 11264},
        {'role': 'scene_catalog', 'id': 'libero-scenes',
         'url': 'https://example.invalid/libero-scenes.zip', 'sha256': 'c'*64, 'size': 250609664,
         'previews': {'default_scenes': ['libero-spatial-0']}},
        {'role': 'robot_base', 'id': 'franka-libero-robot',
         'url': 'https://example.invalid/franka-libero-robot.zip', 'sha256': 'd'*64, 'size': 3113851289},
        {'role': 'robot_ability', 'id': 'franka-ability',
         'url': 'https://example.invalid/franka-ability.zip', 'sha256': 'e'*64, 'size': 2899102924},
        {'role': 'model', 'id': 'franka-smolvla-model',
         'url': 'https://example.invalid/franka-smolvla-model.zip', 'sha256': 'f'*64, 'size': 3435973836},
    ],
}


def manifest(**overrides):
    value = json.loads(json.dumps(MANIFEST))
    value.update(overrides)
    return json.dumps(value)


class ManifestParsingTests(unittest.TestCase):
    def test_valid_manifest_is_normalized_in_install_order(self):
        parsed = extension.parse(manifest())
        self.assertEqual(parsed['id'], 'libero')
        self.assertEqual([c['role'] for c in parsed['components']],
                         ['scene_catalog', 'robot_base', 'robot_ability', 'model', 'robot_skill'])
        self.assertEqual(parsed['runtime']['pack']['size'], 1932735283)

    def test_runtime_is_listed_before_components(self):
        parsed = extension.parse(manifest())
        labels = [label for label, _ in extension.render(parsed)]
        self.assertLess(labels.index('Runtime 包'), labels.index('scene_catalog'))
        self.assertLess(labels.index('scene_catalog'), labels.index('robot_skill'))

    def test_missing_schema_version_is_rejected(self):
        value = json.loads(manifest())
        del value['schema_version']
        with self.assertRaisesRegex(extension.ManifestError, 'schema_version'):
            extension.parse(json.dumps(value))

    def test_wrong_schema_version_is_rejected(self):
        with self.assertRaisesRegex(extension.ManifestError, 'schema_version'):
            extension.parse(manifest(schema_version=2))

    def test_unknown_component_role_is_rejected(self):
        value = json.loads(manifest())
        value['components'][0]['role'] = 'unknown'
        with self.assertRaisesRegex(extension.ManifestError, 'role 不在允许'):
            extension.parse(json.dumps(value))

    def test_base_role_is_required(self):
        value = json.loads(manifest())
        value['components'] = [c for c in value['components'] if c['role'] != 'robot_base']
        with self.assertRaisesRegex(extension.ManifestError, '基座产物'):
            extension.parse(json.dumps(value))

    def test_duplicate_component_is_rejected(self):
        value = json.loads(manifest())
        value['components'].append(dict(value['components'][0]))
        with self.assertRaisesRegex(extension.ManifestError, '重复声明'):
            extension.parse(json.dumps(value))

    def test_artifact_without_digest_is_rejected(self):
        value = json.loads(manifest())
        del value['runtime']['pack']['sha256']
        with self.assertRaisesRegex(extension.ManifestError, 'sha256'):
            extension.parse(json.dumps(value))

    def test_artifact_without_size_is_rejected(self):
        value = json.loads(manifest())
        value['components'][0]['size'] = 0
        with self.assertRaisesRegex(extension.ManifestError, 'size'):
            extension.parse(json.dumps(value))

    def test_invalid_digest_is_rejected(self):
        value = json.loads(manifest())
        value['components'][0]['sha256'] = 'nothex'
        with self.assertRaisesRegex(extension.ManifestError, 'sha256 格式'):
            extension.parse(json.dumps(value))

    def test_non_http_artifact_url_is_rejected(self):
        value = json.loads(manifest())
        value['components'][0]['url'] = 'ftp://example.invalid/x.zip'
        with self.assertRaisesRegex(extension.ManifestError, 'http'):
            extension.parse(json.dumps(value))

    def test_runtime_installation_id_cannot_collide_with_base(self):
        for identifier in ('native-mujoco', 'base'):
            value = json.loads(manifest())
            value['runtime']['installation_id'] = identifier
            with self.subTest(identifier=identifier), self.assertRaisesRegex(extension.ManifestError, '标识'):
                extension.parse(json.dumps(value))

    def test_oversized_artifact_is_rejected(self):
        value = json.loads(manifest())
        value['components'][0]['size'] = 13 * 1024**3
        with self.assertRaisesRegex(extension.ManifestError, '超出上限'):
            extension.parse(json.dumps(value))

    def test_bad_prerequisite_kind_is_rejected(self):
        value = json.loads(manifest())
        value['prerequisites'] = [{'kind': 'magic', 'text': '扫码安装'}]
        with self.assertRaisesRegex(extension.ManifestError, 'prerequisites'):
            extension.parse(json.dumps(value))

    def test_bad_port_range_is_rejected(self):
        for ports in ([[0, 18199]], [[18200, 18199]], [['a', 'b']]):
            with self.subTest(ports=ports), self.assertRaisesRegex(extension.ManifestError, '整数对'):
                extension.parse(manifest(ports=ports))

    def test_valid_ports_and_prerequisites_are_accepted(self):
        parsed = extension.parse(manifest(ports=[[18100, 18199]],
            prerequisites=[{'kind': 'probe', 'text': '本机已导入引擎镜像', 'check': 'docker image inspect x'},
                           {'kind': 'user_action', 'text': '数据集需单独取得'}]))
        self.assertEqual(parsed['ports'], [[18100, 18199]])
        self.assertEqual(len(parsed['prerequisites']), 2)

    def test_invalid_gpu_requirement_is_rejected(self):
        with self.assertRaisesRegex(extension.ManifestError, 'gpu'):
            extension.parse(manifest(host_requirements={'gpu': 'sometimes'}))

    def test_invalid_json_is_rejected(self):
        with self.assertRaisesRegex(extension.ManifestError, 'JSON'):
            extension.parse('{not json')

    def test_non_object_manifest_is_rejected(self):
        with self.assertRaisesRegex(extension.ManifestError, '必须是 JSON 对象'):
            extension.parse('[]')

    def test_manifest_id_must_match_request(self):
        parsed = extension.parse(manifest())
        self.assertEqual(parsed['id'], 'libero')


class ChannelTests(unittest.TestCase):
    def test_channel_url_encodes_and_preserves_slash(self):
        self.assertEqual(extension.channel_url('https://oss.invalid/semantic/', 'extensions', 'libero'),
                         'https://oss.invalid/semantic/extensions/libero')

    def test_manifest_url_shape(self):
        self.assertEqual(
            extension.manifest_url('https://oss.invalid/semantic', 'libero', '0.1.0'),
            'https://oss.invalid/semantic/extensions/libero/0.1.0/extension.json')

    def test_explicit_version_wins_over_pointer(self):
        with patch.object(extension, 'stable_pointer', return_value='9.9.9') as pointer:
            self.assertEqual(extension.resolve_version('https://oss.invalid', 'libero', '0.1.0'), '0.1.0')
            pointer.assert_not_called()

    def test_unreachable_pointer_is_reported(self):
        with patch.object(extension, 'stable_pointer', return_value=None):
            with self.assertRaisesRegex(extension.ManifestError, '无法从通道解析'):
                extension.resolve_version('https://oss.invalid', 'libero')

    def test_unreachable_pointer_returns_none(self):
        with patch.object(extension.urllib.request, 'urlopen', side_effect=OSError('no network')):
            self.assertIsNone(extension.stable_pointer('https://oss.invalid', 'libero'))

    def test_blank_pointer_is_rejected(self):
        with patch.object(extension.urllib.request, 'urlopen') as urlopen:
            urlopen.return_value.__enter__.return_value = FakeResponse(json.dumps({'version': '  '}))
            self.assertIsNone(extension.stable_pointer('https://oss.invalid', 'libero'))

    def test_manifest_download_404_names_the_version(self):
        error = extension.urllib.error.HTTPError('url', 404, 'Not Found', {}, None)
        with patch.object(extension.urllib.request, 'urlopen', side_effect=error):
            with self.assertRaisesRegex(extension.ManifestError, '通道上没有'):
                extension.load_manifest('https://oss.invalid', 'libero', '0.1.0')

    def test_manifest_id_mismatch_is_rejected(self):
        with patch.object(extension, 'resolve_version', return_value='0.1.0'), \
             patch.object(extension.urllib.request, 'urlopen',
                          return_value=FakeResponse(json.dumps({**json.loads(manifest()), 'id': 'isaac'})
                                       .encode())):
            with self.assertRaisesRegex(extension.ManifestError, '不一致'):
                extension.load_manifest('https://oss.invalid', 'libero')


class FakeResponse:
    """Minimal context-manager stream: ``read()`` drains a fixed body, like a socket."""

    def __init__(self, body=b''):
        self.body = body if isinstance(body, bytes) else body.encode()
        self.offset = 0

    def read(self, amount=-1):
        if amount is None or amount < 0:
            amount = len(self.body)
        block, self.offset = self.body[self.offset:self.offset + amount], self.offset + max(amount, 0)
        return block

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        return False


class Runaway(FakeResponse):
    """A stream that always has one more block, to prove the size ceiling engages."""

    def read(self, amount=-1):
        return b'x' * (1024 * 1024)


class VerifyTests(unittest.TestCase):
    """The digest that is checked must be the one the manifest declares."""

    def parsed(self, declared=b'payload'):
        """Build a manifest whose declared digests and sizes match ``declared``."""
        value = json.loads(manifest())
        for artifact in [value['runtime']['pack'], *value['components']]:
            artifact['size'] = len(declared)
            artifact['sha256'] = digest_of(declared)
        return extension.parse(json.dumps(value))

    def test_verify_reports_one_row_per_artifact(self):
        with patch.object(extension, '_download', side_effect=write(b'payload')), \
             patch.object(extension, 'Progress'):
            rows = extension.verify(self.parsed(), quiet=True)
        self.assertEqual(len(rows), 6)
        self.assertEqual({row[0] for row in rows},
                         {'local-libero-robosuite-1.4', 'scene_catalog/libero-scenes',
                          'robot_base/franka-libero-robot', 'robot_ability/franka-ability',
                          'model/franka-smolvla-model', 'robot_skill/vla-manipulation'})
        self.assertTrue(all(row[1] == 'ok' for row in rows))

    def test_verify_truncated_artifact_is_rejected(self):
        with patch.object(extension, '_download', side_effect=write(b'paylo')), \
             patch.object(extension, 'Progress'):
            with self.assertRaisesRegex(extension.ManifestError, 'size-mismatch'):
                extension.verify(self.parsed(), quiet=True)

    def test_verify_substituted_artifact_of_equal_size_is_rejected(self):
        with patch.object(extension, '_download', side_effect=write(b'payloaz')), \
             patch.object(extension, 'Progress'):
            with self.assertRaisesRegex(extension.ManifestError, 'sha256-mismatch'):
                extension.verify(self.parsed(), quiet=True)

    def test_verify_download_failure_names_the_artifact(self):
        with patch.object(extension, '_download', side_effect=OSError('connection reset')), \
             patch.object(extension, 'Progress'):
            with self.assertRaisesRegex(extension.ManifestError, 'connection reset'):
                extension.verify(self.parsed(), quiet=True)

    def test_one_artifact_result_names_expected_and_actual_size(self):
        parsed = self.parsed()
        with patch.object(extension, '_download', side_effect=write(b'paylo')):
            state, detail = extension._verify_one(parsed['runtime']['pack'])
        self.assertEqual(state, 'size-mismatch')
        self.assertIn('期望 7', detail)
        self.assertIn('实际 5', detail)


def write(body):
    """A ``_download`` stand-in that stages ``body`` at the destination."""
    def download(url, destination):
        destination.write_bytes(body)
        return len(body)
    return download


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.temporary = __import__('tempfile').TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.target = Path(self.temporary.name)/'pack.zip'

    def test_download_refuses_runaway_size(self):
        with patch.object(extension.urllib.request, 'urlopen', return_value=Runaway()), \
             patch.object(extension, 'ARTIFACT_LIMIT', 1024):
            with self.assertRaisesRegex(extension.ManifestError, '上限'):
                extension._download('https://example.invalid/x.zip', self.target)

    def test_download_writes_streamed_bytes(self):
        with patch.object(extension.urllib.request, 'urlopen', return_value=FakeResponse(b'hello')):
            self.assertEqual(extension._download('https://example.invalid/x.zip', self.target), 5)
        self.assertEqual(self.target.read_bytes(), b'hello')


class EntryTests(unittest.TestCase):
    def test_list_without_index_reports_unavailable(self):
        args = __import__('types').SimpleNamespace(extension_action='list', id=None, base_url='https://oss.invalid',
                                                   version=None, quiet=False)
        with patch.object(extension.urllib.request, 'urlopen', side_effect=OSError('no network')):
            self.assertEqual(extension.entry(args), 1)

    def test_show_prints_summary(self):
        args = __import__('types').SimpleNamespace(extension_action='show', id='libero',
                                                   base_url='https://oss.invalid', version='0.1.0', quiet=False)
        with patch.object(extension, 'load_manifest', return_value=extension.parse(manifest())), \
             patch('builtins.print') as show:
            self.assertEqual(extension.entry(args), 0)
        self.assertTrue(any('LIBERO 仿真场景' in str(call) for call in show.call_args_list))

    def test_install_and_remove_are_declared_but_not_yet_supported(self):
        for action in ('install', 'remove'):
            args = __import__('types').SimpleNamespace(extension_action=action, id='libero',
                                                       base_url='https://oss.invalid', version=None, quiet=False)
            with self.subTest(action=action), self.assertRaises(SystemExit):
                extension.entry(args)


class CheckedInManifestTests(unittest.TestCase):
    """The committed template must keep parsing as the validator tightens."""

    def test_libero_manifest_parses(self):
        parsed = extension.parse((ROOT/'extensions/libero/extension.json').read_text())
        self.assertEqual(parsed['id'], 'libero')
        self.assertEqual(parsed['runtime']['installation_id'], 'local-libero-robosuite-1.4')

    def test_libero_manifest_order_is_runtime_then_components(self):
        parsed = extension.parse((ROOT/'extensions/libero/extension.json').read_text())
        self.assertEqual([c['role'] for c in parsed['components']],
                         ['scene_catalog', 'robot_base', 'robot_ability', 'model', 'robot_skill'])

    def test_libero_manifest_carries_a_license_to_accept(self):
        parsed = extension.parse((ROOT/'extensions/libero/extension.json').read_text())
        self.assertTrue(parsed['license'].strip())

    def test_libero_manifest_declares_no_gpu_requirement(self):
        parsed = extension.parse((ROOT/'extensions/libero/extension.json').read_text())
        self.assertEqual(parsed['host_requirements']['gpu'], 'optional')


if __name__ == '__main__':
    unittest.main()
