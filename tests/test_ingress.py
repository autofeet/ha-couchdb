import base64
import importlib.util
from pathlib import Path
import unittest


class IngressConfigurationTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'couchdb' / 'configure.py'
        spec = importlib.util.spec_from_file_location('configure', path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.options = {'username': 'sync_admin', 'password': 'test-only%quote"password'}

    def test_only_supervisor_with_identified_ha_session_can_use_ingress(self):
        self.assertTrue(hasattr(self.module, 'render_ingress_config'), 'Ingress adapter is missing')
        configuration = self.module.render_ingress_config(self.options)
        self.assertIn('listen 8099;', configuration)
        self.assertIn('allow 172.30.32.2;', configuration)
        self.assertIn('deny all;', configuration)
        self.assertIn('if ($http_x_remote_user_id = "") { return 403; }', configuration)

    def test_authentication_stays_in_server_configuration(self):
        self.assertTrue(hasattr(self.module, 'render_ingress_config'), 'Ingress adapter is missing')
        configuration = self.module.render_ingress_config(self.options)
        encoded = base64.b64encode(b'sync_admin:test-only%quote"password').decode()
        self.assertIn(f'proxy_set_header Authorization "Basic {encoded}";', configuration)
        self.assertNotIn(self.options['password'], configuration)
        self.assertIn('proxy_hide_header Set-Cookie;', configuration)
        self.assertIn('proxy_set_header Cookie "";', configuration)


if __name__ == '__main__':
    unittest.main()
