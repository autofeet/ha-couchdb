import configparser
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'couchdb' / 'configure.py'


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SOURCE.exists(), 'HA configuration adapter is missing')
        spec = importlib.util.spec_from_file_location('configure', SOURCE)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.options = {'username': 'sync_admin', 'password': 'test-only-long-password'}

    def parse(self, text):
        config = configparser.ConfigParser(interpolation=None)
        config.read_string(text)
        return config

    def test_sets_persistent_storage_and_livesync_settings(self):
        config = self.parse(self.module.render_config(self.options))
        self.assertEqual(config['couchdb']['database_dir'], '/data/couchdb')
        self.assertEqual(config['couchdb']['view_index_dir'], '/data/couchdb')
        self.assertEqual(config['couchdb']['single_node'], 'true')
        self.assertEqual(config['chttpd']['require_valid_user'], 'true')
        self.assertEqual(config['chttpd']['enable_cors'], 'true')
        self.assertEqual(config['cors']['origins'], 'app://obsidian.md,capacitor://localhost,http://localhost')

    def test_rotation_replaces_old_admin_and_preserves_runtime_settings(self):
        existing = '[admins]\nold_admin = old-password\n[chttpd_auth]\nsecret = keep-me\n[custom]\nvalue = 100%\n'
        config = self.parse(self.module.render_config(self.options, existing))
        self.assertEqual(dict(config['admins']), {'sync_admin': self.options['password']})
        self.assertEqual(config['chttpd_auth']['secret'], 'keep-me')
        self.assertEqual(config['custom']['value'], '100%')

    def test_rejects_invalid_values_without_leaking_them(self):
        invalid = [('', 'secret'), ('admin', ''), ('admin\n[bad]', 'secret'),
                   ('admin', 'secret\ninjection'), ('admin', ' secret'),
                   ('admin', '-pbkdf2:not-a-password'), ('admin', 'abc\x00def')]
        for username, password in invalid:
            with self.subTest(username=username):
                with self.assertRaises(ValueError) as raised:
                    self.module.render_config({'username': username, 'password': password})
                if password:
                    self.assertNotIn(password, str(raised.exception))

    def test_password_special_characters_are_not_interpolated(self):
        self.options['password'] = 'valid%pass;word=with#symbols'
        config = self.parse(self.module.render_config(self.options))
        self.assertEqual(config['admins']['sync_admin'], self.options['password'])


if __name__ == '__main__':
    unittest.main()
