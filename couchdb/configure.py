"""Adapt HA options and persistent storage, then use the official entry point."""
import configparser
import io
import json
import os
from pathlib import Path
import re
import sys


def render_config(options, existing=''):
    username = options.get('username', '')
    password = options.get('password', '')
    if not isinstance(username, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', username):
        raise ValueError('Username must start with a letter and contain only letters, digits, _ or -.')
    if (not isinstance(password, str) or not password or password != password.strip()
            or any(ord(c) < 32 or ord(c) == 127 for c in password)
            or password.startswith(('-pbkdf2', '-hashed-'))):
        raise ValueError('Set a nonempty password without control characters, edge whitespace or reserved hash prefixes.')

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
    # Credentials are already supplied through the protected configuration file.
    os.environ.pop('COUCHDB_USER', None)
    os.environ.pop('COUCHDB_PASSWORD', None)
    os.execv('/docker-entrypoint.sh', ['/docker-entrypoint.sh', *sys.argv[1:]])


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, configparser.Error) as error:
        print(f'CouchDB startup failed ({type(error).__name__}). Check HA options and persistent storage; no credential values are logged.', file=sys.stderr)
        sys.exit(1)
