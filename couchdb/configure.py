"""Adapt HA options and persistent storage, then use the official entry point."""
import base64
import configparser
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def render_config(options, existing=''):
    username = options.get('username', '')
    password = options.get('password', '')
    if not isinstance(username, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', username):
        raise ValueError('Username must start with a letter and contain only letters, digits, _ or -.')
    if (not isinstance(password, str) or not password or password != password.strip()
            or any(ord(c) < 32 or ord(c) == 127 for c in password)
            or password.startswith(('-pbkdf2', '-hashed-', ';'))
            or re.search(r'\s;', password)):
        raise ValueError('Set a nonempty password without control characters, edge whitespace, INI comment syntax or reserved hash prefixes.')

    config = configparser.ConfigParser(interpolation=None, delimiters=('=',), strict=False)
    config.optionxform = str
    config.read_string(existing)
    managed = {
        'couchdb': {
            'database_dir': '/data/couchdb',
            'view_index_dir': '/data/couchdb',
            'single_node': 'true',
            'max_document_size': '50000000',
        },
        'chttpd': {
            'bind_address': '0.0.0.0', 'port': '5984',
            'require_valid_user': 'true', 'enable_cors': 'true',
            'max_http_request_size': '4294967296',
        },
        'chttpd_auth': {'require_valid_user': 'true'},
        'httpd': {'WWW-Authenticate': 'Basic realm="couchdb"'},
        'cors': {
            'credentials': 'true',
            'origins': 'app://obsidian.md,capacitor://localhost,http://localhost',
            'methods': 'GET, PUT, POST, HEAD, DELETE',
            'headers': 'accept, authorization, content-type, origin, referer',
        },
    }
    for section, values in managed.items():
        if not config.has_section(section):
            config.add_section(section)
        config[section].update(values)
    # The HA options are authoritative for the single instance administrator.
    config.remove_section('admins')
    config['admins'] = {username: password}
    output = io.StringIO()
    config.write(output)
    return output.getvalue()


def render_ingress_config(options):
    # Only the HA-authenticated Supervisor connection may receive this identity.
    render_config(options)
    credentials = f"{options['username']}:{options['password']}".encode()
    authorization = base64.b64encode(credentials).decode('ascii')
    return '''worker_processes 1;
pid /run/ha-couchdb-nginx.pid;
error_log /dev/stderr warn;
events { worker_connections 128; }
http {
    access_log off;
    client_max_body_size 0;
    server {
        listen 8099;
        server_name _;
        allow 172.30.32.2;
        deny all;
        if ($http_x_remote_user_id = "") { return 403; }
        location / {
            proxy_pass http://127.0.0.1:5984;
            proxy_http_version 1.1;
            proxy_set_header Host $http_host;
            proxy_set_header Authorization "Basic ''' + authorization + '''";
            proxy_set_header Cookie "";
            proxy_set_header Connection "";
            proxy_hide_header Set-Cookie;
            proxy_hide_header WWW-Authenticate;
            proxy_hide_header X-Frame-Options;
            add_header X-Frame-Options SAMEORIGIN always;
            proxy_redirect ~^(/.*)$ $http_x_ingress_path$1;
            proxy_read_timeout 3600s;
            proxy_buffering off;
        }
    }
}
'''


def main():
    data = Path('/data')
    options = json.loads((data / 'options.json').read_text())
    configuration = data / 'local.d' / 'docker.ini'
    existing = configuration.read_text() if configuration.exists() else ''
    rendered = render_config(options, existing)
    for directory in (data / 'couchdb', data / 'local.d'):
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chown(directory, 5984, 5984)
        os.chmod(directory, 0o700)
    temporary = configuration.with_suffix('.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as handle:
        handle.write(rendered)
    os.chown(temporary, 5984, 5984)
    temporary.replace(configuration)
    ingress = Path('/run/ha-couchdb-nginx.conf')
    fd = os.open(ingress, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as handle:
        handle.write(render_ingress_config(options))
    subprocess.run(['nginx', '-c', str(ingress)], check=True)
    # Credentials are already supplied through the protected configuration file.
    os.environ.pop('COUCHDB_USER', None)
    os.environ.pop('COUCHDB_PASSWORD', None)
    os.execv('/docker-entrypoint.sh', ['/docker-entrypoint.sh', *sys.argv[1:]])


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, configparser.Error, subprocess.CalledProcessError) as error:
        print(f'CouchDB startup failed ({type(error).__name__}). Check HA options and persistent storage; no credential values are logged.', file=sys.stderr)
        sys.exit(1)
