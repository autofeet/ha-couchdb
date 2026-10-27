import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'scripts' / 'check_upstream.py'


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SOURCE.exists(), 'Upstream checker is missing')
        spec = importlib.util.spec_from_file_location('updater', SOURCE)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def tag(self, name, architectures=('amd64', 'arm64')):
        return {'name': name, 'images': [{'architecture': a, 'os': 'linux'} for a in architectures]}

    def test_chooses_latest_stable_same_major_with_both_architectures(self):
        tags = [self.tag(v) for v in ['3', 'latest', '3.5', '3.5.3', '3.5.4-rc1', '3.5.4-nouveau', '4.0.0', '3.5.4', '3.5.2.1']]
        tags.append(self.tag('3.6.0', ('amd64',)))
        self.assertEqual(self.module.choose_release(tags, '3.5.3'), '3.5.4')

    def test_ignores_equal_and_older_versions(self):
        self.assertIsNone(self.module.choose_release([self.tag('3.5.3'), self.tag('3.5.2.1')], '3.5.3'))

    def test_accepts_four_component_releases(self):
        self.assertEqual(self.module.choose_release([self.tag('3.5.2.1')], '3.5.2'), '3.5.2.1')


if __name__ == '__main__':
    unittest.main()
