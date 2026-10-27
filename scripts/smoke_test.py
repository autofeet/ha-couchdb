"""Exercise the real image; run on a Linux Docker host with disposable volumes."""
import argparse
import base64
import json
import secrets
import subprocess
import tempfile
import time
import urllib.error
import urllib.request


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('image')
    args = parser.parse_args()
    suffix = secrets.token_hex(5)
    name = f'ha-couchdb-test-{suffix}'
    volume = f'ha-couchdb-test-{suffix}'
    username, password = 'test_admin', secrets.token_urlsafe(24)
    url = ''

    def request(path, method='GET', body=None, authenticated=True, headers=None):
        headers = dict(headers or {})
        if authenticated:
            token = base64.b64encode(f'{username}:{password}'.encode()).decode()
            headers['Authorization'] = 'Basic ' + token
        payload = None if body is None else json.dumps(body).encode()
        if payload is not None:
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(url + path, data=payload, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status, response.read(), response.headers
        except urllib.error.HTTPError as error:
            return error.code, error.read(), error.headers

    def set_options():
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as handle:
            json.dump({'username': username, 'password': password}, handle)
            handle.flush()
            docker('run', '--rm', '--user', '0', '--entrypoint', 'cp',
                   '-v', f'{volume}:/data', '-v', f'{handle.name}:/options.json:ro',
                   args.image, '/options.json', '/data/options.json')

    def start():
        nonlocal url
        docker('run', '-d', '--name', name, '-v', f'{volume}:/data',
               '-p', '127.0.0.1::5984', args.image)
        port = docker('port', name, '5984/tcp').rsplit(':', 1)[1]
        url = f'http://127.0.0.1:{port}'
        last_status, last_databases = None, []
        for _ in range(60):
            try:
                status, payload, _ = request('/_all_dbs')
                last_status = status
                if status == 200:
                    last_databases = json.loads(payload)
                # CouchDB single_node creates these two databases. The optional
                # global changes database is not needed by LiveSync.
                if status == 200 and {'_users', '_replicator'} <= set(json.loads(payload)):
                    return
            except (OSError, ValueError):
                pass
            time.sleep(1)
        raise AssertionError(f'CouchDB not ready: HTTP={last_status}, databases={last_databases}')

    docker('volume', 'create', volume)
    try:
        set_options()
        start()
        assert request('/_all_dbs', authenticated=False)[0] == 401
        assert request('/vault', 'PUT')[0] == 201
        assert request('/vault/note', 'PUT', {'text': 'persistent note'})[0] == 201
        assert request('/vault/note', authenticated=False)[0] == 401
        status, _, headers = request('/vault', 'OPTIONS', authenticated=False, headers={
            'Origin': 'app://obsidian.md',
            'Access-Control-Request-Method': 'PUT',
            'Access-Control-Request-Headers': 'authorization,content-type',
        })
        assert status in (200, 204), f'Preflight status: {status}'
        assert headers.get('Access-Control-Allow-Origin') == 'app://obsidian.md'
        assert headers.get('Access-Control-Allow-Credentials') == 'true'
        assert request('/_node/_local/_config/custom/retained', 'PUT', 'keep-me')[0] == 200

        # Recreate rather than merely restart: image updates replace containers.
        docker('stop', '-t', '120', name)
        docker('rm', name)
        start()
        assert json.loads(request('/vault/note')[1])['text'] == 'persistent note'
        assert json.loads(request('/_node/_local/_config/custom/retained')[1]) == 'keep-me'

        docker('stop', '-t', '120', name)
        docker('rm', name)
        old_username, old_password = username, password
        username, password = 'rotated_admin', secrets.token_urlsafe(24)
        set_options()
        start()
        assert request('/vault/note')[0] == 200
        username, password = old_username, old_password
        assert request('/vault/note')[0] == 401
        processes = docker('top', name, '-eo', 'pid,uid,args')
        assert any(len(line.split()) > 2 and line.split()[1] == '5984' and 'beam.smp' in line for line in processes.splitlines()), 'Erlang must run as CouchDB uid 5984'
        print('PASS: auth, CORS, system DBs, container replacement, retained config and credential rotation')
    except Exception:
        # Never dump configuration or HA options into CI logs.
        print('Container test failed; inspect the failed assertion. Credentials are not logged.')
        logs = subprocess.run(['docker', 'logs', '--tail', '60', name], capture_output=True, text=True)
        print((logs.stdout + logs.stderr).replace(password, '[redacted]'))
        raise
    finally:
        subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['docker', 'volume', 'rm', volume], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == '__main__':
    main()
