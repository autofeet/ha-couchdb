"""Check official Docker Hub tags and prepare a reviewable HA app update."""
import argparse
import json
import os
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def version_tuple(value):
    parts = tuple(int(v) for v in value.split('.'))
    return parts + (0,) * (4 - len(parts))


def choose_release(tags, current):
    candidates = []
    for tag in tags:
        name = tag['name']
        if not re.fullmatch(r'\d+\.\d+\.\d+(?:\.\d+)?', name):
            continue
        if name.split('.')[0] != current.split('.')[0] or version_tuple(name) <= version_tuple(current):
            continue
        architectures = {image['architecture'] for image in tag.get('images', []) if image.get('os') == 'linux'}
        if {'amd64', 'arm64'} <= architectures:
            candidates.append(name)
    return max(candidates, key=version_tuple) if candidates else None


def fetch_tags():
    url = 'https://hub.docker.com/v2/repositories/library/couchdb/tags?page_size=100&ordering=last_updated'
    tags = []
    # Stable tags can appear after many variant tags. Bound pagination explicitly.
    for _ in range(5):
        request = urllib.request.Request(url, headers={'User-Agent': 'ha-couchdb-updater'})
        with urllib.request.urlopen(request, timeout=30) as response:
            page = json.load(response)
        tags.extend(page['results'])
        url = page.get('next')
        if not url:
            break
        if not url.startswith('https://hub.docker.com/v2/repositories/library/couchdb/tags?'):
            raise ValueError('Unexpected Docker Hub pagination URL')
    return tags


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    dockerfile = ROOT / 'couchdb' / 'Dockerfile'
    source = dockerfile.read_text()
    current = re.search(r'^FROM couchdb:([0-9.]+)$', source, re.M).group(1)
    newest = choose_release(fetch_tags(), current)
    print(json.dumps({'current': current, 'new': newest}))
    if not newest or not args.apply:
        return
    dockerfile.write_text(source.replace(f'FROM couchdb:{current}\n', f'FROM couchdb:{newest}\n'))
    configuration = ROOT / 'couchdb' / 'config.yaml'
    configuration.write_text(re.sub(r'^version: "[^"]+"$', f'version: "{newest}-1"', configuration.read_text(), flags=re.M))
    changelog = ROOT / 'couchdb' / 'CHANGELOG.md'
    changelog.write_text(f'## {newest}-1\n\n- Update the official CouchDB base image from {current} to {newest}.\n- Review container CI and back up before upgrading.\n\n' + changelog.read_text())
    if output := os.environ.get('GITHUB_OUTPUT'):
        with open(output, 'a') as handle:
            handle.write(f'new_version={newest}\n')


if __name__ == '__main__':
    main()
