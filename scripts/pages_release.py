#!/usr/bin/env python3
"""Persist verified Pages snapshots and coordinate a serialized deployment transaction.

Only trusted main-branch code runs this module. Releases hold bytes; the fixed
pages-state release is the commit record. A pending record blocks new publishing
after runner termination until the explicit `active` recovery operation runs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

import pages_snapshot as snapshot
import publish_site
import site_checks

BASE_URL = 'https://sona201.github.io/'
STATE_TAG = 'pages-state'
MAX_ARCHIVE = 1024 * 1024 * 1024
TERMINAL = {'succeed', 'deployment_failed', 'deployment_content_failed', 'deployment_cancelled', 'deployment_lost'}
BEGIN_STEP = 'Persist the pending deployment transaction'
DEPLOY_STEPS = ('Deploy candidate through official GitHub Pages action',
                'Restore the previous complete site through GitHub Pages')


class ReleaseError(ValueError):
    pass


class SafeRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        url = urlsplit(newurl)
        if url.username or url.password or url.port not in {None, 443} or url.scheme != 'https' or url.hostname not in {'api.github.com', 'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}:
            raise ReleaseError('Unexpected GitHub asset redirect')
        result = super().redirect_request(req, fp, code, msg, headers, newurl)
        if result is not None and url.hostname != urlsplit(req.full_url).hostname:
            result.remove_header('Authorization')
        return result


class GitHub:
    def __init__(self, repo=None, token=None):
        self.repo = repo or os.environ['GITHUB_REPOSITORY']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', self.repo):
            raise ReleaseError('Invalid repository name')
        self.token = token or os.environ['GH_TOKEN']
        self.opener = build_opener(SafeRedirects())

    def _request(self, path, method='GET', data=None, accept='application/vnd.github+json', content_type='application/json'):
        if path.startswith('https://'):
            url = urlsplit(path)
            if url.username or url.password or url.port not in {None, 443} or url.hostname != 'uploads.github.com' or not url.path.startswith('/repos/' + self.repo + '/releases/'):
                raise ReleaseError('Unexpected release upload URL')
        elif path.startswith('/') and not path.startswith('//'):
            path = 'https://api.github.com/repos/' + self.repo + path
        else:
            raise ReleaseError('Invalid GitHub API path')
        headers = {'Authorization': 'Bearer ' + self.token, 'Accept': accept,
                   'Content-Type': content_type, 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'blog-pages-release'}
        return self.opener.open(Request(path, data=data, method=method, headers=headers), timeout=60)

    def request(self, path, method='GET', data=None):
        with self._request(path, method, None if data is None else json.dumps(data).encode()) as response:
            body = response.read(8 * 1024 * 1024)
        return json.loads(body) if body else None

    def download(self, asset, destination):
        if type(asset.get('id')) is not int or type(asset.get('size')) is not int or not 0 < asset['size'] <= MAX_ARCHIVE:
            raise ReleaseError('Invalid release asset size or ID')
        size = 0
        with self._request('/releases/assets/' + str(asset['id']), accept='application/octet-stream') as response, destination.open('xb') as output:
            while block := response.read(1024 * 1024):
                size += len(block)
                if size > asset['size'] or size > MAX_ARCHIVE:
                    raise ReleaseError('Release asset exceeds expected size')
                output.write(block)
        if size != asset['size']:
            raise ReleaseError('Truncated release asset')

    def upload(self, release, path):
        url = release['upload_url'].split('{', 1)[0] + '?name=' + quote(path.name)
        with self._request(url, 'POST', path.read_bytes(), content_type='application/octet-stream') as response:
            return json.load(response)


def read_json(path):
    return publish_site.load_json(path)


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    temporary.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def output(**values):
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            for key, value in values.items():
                stream.write(f'{key}={str(value).lower() if isinstance(value, bool) else value}\n')


def check_pointer(pointer):
    if not isinstance(pointer, dict) or not re.fullmatch(r'pages-snapshot-[A-Za-z0-9-]+', pointer.get('tag', '')):
        raise ReleaseError('Invalid snapshot pointer')
    if type(pointer.get('release_id')) is not int or not re.fullmatch(r'[0-9a-f]{64}', pointer.get('manifest_sha256', '')):
        raise ReleaseError('Invalid snapshot release ID or manifest digest')
    return pointer


def load_state(client):
    release = client.request('/releases/tags/' + STATE_TAG)
    state = json.loads(release['body'])
    if type(state.get('schema_version')) is not int or state['schema_version'] != 1:
        raise ReleaseError('Unsupported Pages state')
    check_pointer(state.get('active'))
    if state.get('pending') is not None and not isinstance(state['pending'], dict):
        raise ReleaseError('Invalid pending transaction')
    return release, state


def write_state(client, release, state):
    client.request('/releases/' + str(release['id']), 'PATCH', {'body': json.dumps(state, sort_keys=True), 'make_latest': 'false'})


def download_snapshot(client, pointer, destination, downloads):
    check_pointer(pointer)
    release = client.request('/releases/' + str(pointer['release_id']))
    if release['tag_name'] != pointer['tag']:
        raise ReleaseError('Snapshot tag changed')
    assets = {entry['name']: entry for entry in release['assets']}
    if len(assets) != len(release['assets']) or not {'site.zip', 'snapshot.json'} <= set(assets):
        raise ReleaseError('Missing or duplicate snapshot assets')
    downloads.mkdir(parents=True, exist_ok=False)
    manifest = downloads / 'snapshot.json'
    client.download(assets['snapshot.json'], manifest)
    if digest(manifest) != pointer['manifest_sha256']:
        raise ReleaseError('Snapshot manifest digest mismatch')
    archive = downloads / 'site.zip'
    client.download(assets['site.zip'], archive)
    snapshot.extract_archive(archive, manifest, destination, allow_legacy=pointer.get('allow_legacy', False))


def upload_snapshot(client, site, work, tag, *, allow_legacy=False):
    bundle = work / 'bundle'
    bundle.mkdir()
    snapshot.make_archive(site, bundle / 'site.zip', bundle / 'snapshot.json', allow_legacy=allow_legacy)
    # Tags always point at trusted default-branch code, never PR code.
    trusted_sha = client.request('/branches/main')['commit']['sha']
    metadata = {'schema_version': 1, 'manifest_sha256': digest(bundle / 'snapshot.json'), 'allow_legacy': allow_legacy}
    release = client.request('/releases', 'POST', {'tag_name': tag, 'target_commitish': trusted_sha,
        'name': tag, 'body': json.dumps(metadata, sort_keys=True), 'draft': False, 'prerelease': True, 'make_latest': 'false'})
    for path in [bundle / 'site.zip', bundle / 'snapshot.json']:
        client.upload(release, path)
    return {'tag': tag, 'release_id': release['id'], **metadata}


def pointer_for_tag(client, tag):
    if not re.fullmatch(r'pages-snapshot-[A-Za-z0-9-]+', tag):
        raise ReleaseError('Expected a pages-snapshot-* release tag')
    release = client.request('/releases/tags/' + tag)
    metadata = json.loads(release['body'])
    if metadata.get('verified') is not True:
        raise ReleaseError('Rollback target must be a verified snapshot')
    return check_pointer({'tag': tag, 'release_id': release['id'], **metadata})


def verified_release(client, pointer):
    release = client.request('/releases/' + str(pointer['release_id']))
    body = json.loads(release['body'])
    if body['manifest_sha256'] != pointer['manifest_sha256']:
        raise ReleaseError('Snapshot metadata changed')
    body['verified'] = True
    client.request('/releases/' + str(release['id']), 'PATCH', {'body': json.dumps(body, sort_keys=True), 'make_latest': 'false'})


def fetch_public(path, *, timeout=15):
    url = BASE_URL + path
    opener = build_opener(site_checks.SameArtifactRedirects(site_checks.SiteURLs(BASE_URL)))
    with opener.open(Request(url, headers={'Cache-Control': 'no-cache'}), timeout=timeout) as response:
        return response.read(8 * 1024 * 1024)


def verify_tree(site, pointer, *, timeout=300, attempts=30):
    deadline = time.monotonic() + timeout
    info = snapshot.validate(site, allow_legacy=pointer.get('allow_legacy', False))
    def remaining():
        seconds = deadline - time.monotonic()
        if seconds <= 0:
            raise ReleaseError('Whole-site verification budget expired')
        return seconds
    if not pointer.get('legacy_marker'):
        expected = (site / snapshot.GENERATION_FILE).read_bytes()
        for attempt in range(attempts):
            try:
                if fetch_public(snapshot.GENERATION_FILE + '?snapshot=' + pointer['tag'], timeout=min(15, remaining())) == expected:
                    break
            except (OSError, ValueError):
                pass
            if attempt + 1 == attempts:
                raise ReleaseError('Remote whole-site generation did not match')
            time.sleep(min(10, remaining()))
    with tempfile.TemporaryDirectory(prefix='pages-verify-') as temporary:
        root = Path(temporary)
        for number in [None] + sorted(info['previews'], key=int):
            component = root / ('production' if number is None else str(number))
            snapshot.component_copy(site, component, pr_number=None if number is None else int(number))
            url = BASE_URL if number is None else BASE_URL + f'previews/pr-{number}/'
            if (component / 'build-info.json').exists():
                site_checks.verify_site(component, url, attempts=attempts, total_timeout=remaining())
            elif number is None and pointer.get('allow_legacy'):
                if hashlib.sha256(fetch_public('?legacy=' + pointer['tag'], timeout=min(15, remaining()))).hexdigest() != digest(component / 'index.html'):
                    raise ReleaseError('Legacy homepage differs from saved snapshot')
            else:
                raise ReleaseError('Component lacks build identity')


def legacy_checkout(commit, destination):
    commit = publish_site.full_sha(commit)
    repo = Path(__file__).resolve().parent.parent
    publish_site.git(repo, 'fetch', '--no-tags', 'origin', 'refs/heads/master:refs/remotes/origin/master')
    if publish_site.git(repo, 'merge-base', '--is-ancestor', commit, 'refs/remotes/origin/master', check=False).returncode:
        raise ReleaseError('Legacy rollback commit is not in preserved master history')
    destination.mkdir()
    for entry in publish_site.git(repo, 'ls-tree', '-r', '-z', commit, raw=True).split(b'\0'):
        if not entry:
            continue
        metadata, raw_name = entry.split(b'\t', 1)
        mode, kind, blob = metadata.decode().split()
        name = raw_name.decode('utf-8')
        path = publish_site.relative_path(name, allow_previews=True)
        if path.parts[0] == 'previews':
            continue
        if kind != 'blob' or mode not in {'100644', '100755'}:
            raise ReleaseError('Legacy history contains nonregular files')
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(publish_site.git(repo, 'cat-file', 'blob', blob, raw=True))


def prepare(args, client):
    work = args.work
    work.mkdir(parents=True, exist_ok=False)
    release, state = load_state(client)
    recovering = args.kind == 'rollback' and args.target == 'active'
    if state.get('pending') and not recovering:
        raise ReleaseError('An interrupted transaction is pending. Run Blog rollback with deployment_commit=active.')
    if recovering and state.get('pending'):
        confirm_pending_deployment_stopped(client, state['pending'])
    base = state['active']
    download_snapshot(client, base, work / 'previous', work / 'download-previous')
    if not recovering:
        verify_tree(work / 'previous', base, timeout=90, attempts=3)
    site = args.site
    identity = None
    pr_number = None
    if args.context:
        context = read_json(args.context)
        if context['action'] != args.kind:
            raise ReleaseError('Publication context does not match operation')
        if args.kind in {'production', 'preview'}:
            identity = {'source_sha': context['source_sha'], 'run_id': context['build_id'],
                        'kind': args.kind, 'base_url': context['base_url']}
        pr_number = int(context['pr_number']) if context.get('pr_number') else None
    if args.kind == 'rollback':
        if args.target == 'active':
            site = work / 'previous'
        elif re.fullmatch(r'[0-9a-fA-F]{40}', args.target or ''):
            site = work / 'rollback-target'
            legacy_checkout(args.target, site)
        else:
            pointer = pointer_for_tag(client, args.target or '')
            site = work / 'rollback-target'
            download_snapshot(client, pointer, site, work / 'download-target')
    run_id = os.environ['GITHUB_RUN_ID']
    attempt = os.environ['GITHUB_RUN_ATTEMPT']
    if not run_id.isdigit() or not attempt.isdigit():
        raise ReleaseError('Invalid workflow run identity')
    tag = f'pages-snapshot-{run_id}-{attempt}'
    allow_legacy = bool(base.get('allow_legacy')) or args.kind == 'rollback'
    snapshot.compose(work / 'previous', work / 'site', kind=args.kind, snapshot_id=tag,
                     site=site, identity=identity, pr_number=pr_number, allow_legacy=allow_legacy)
    candidate = upload_snapshot(client, work / 'site', work, tag, allow_legacy=allow_legacy)
    transaction = {'schema_version': 1, 'id': tag, 'kind': args.kind, 'base': base,
        'candidate': candidate, 'state_release_id': release['id'], 'run_id': run_id,
        'run_attempt': attempt, 'workflow_sha': os.environ['GITHUB_SHA'],
        'pr_number': pr_number, 'base_url': BASE_URL + f'previews/pr-{pr_number}/' if args.kind == 'preview' else BASE_URL,
        'verified': False, 'restored': False, 'recovering_pending': state.get('pending') if recovering else None}
    save_json(work / 'transaction.json', transaction)
    output(snapshot_id=tag, recovery_needed=False)


def begin(work, client):
    tx = read_json(work / 'transaction.json')
    release, state = load_state(client)
    if state['active'] != tx['base'] or release['id'] != tx['state_release_id']:
        raise ReleaseError('Active snapshot changed before deployment')
    if state.get('pending') != tx.get('recovering_pending'):
        raise ReleaseError('Another pending transaction exists')
    state['pending'] = {key: tx[key] for key in ('id', 'base', 'candidate', 'run_id', 'run_attempt', 'workflow_sha')}
    write_state(client, release, state)


def current_transaction(work, client):
    tx = read_json(work / 'transaction.json')
    release, state = load_state(client)
    if release['id'] != tx['state_release_id'] or state['active'] != tx['base'] or (state.get('pending') or {}).get('id') != tx['id']:
        raise ReleaseError('The transaction no longer owns Pages state')
    return tx, release, state


def commit(work, client):
    tx, release, state = current_transaction(work, client)
    if tx.get('verified') is not True:
        raise ReleaseError('Cannot commit a snapshot without online verification')
    verified_release(client, tx['candidate'])
    state.update(active=tx['candidate'], pending=None)
    write_state(client, release, state)
    tx['committed'] = True
    save_json(work / 'transaction.json', tx)


def abort(work, client):
    tx, release, state = current_transaction(work, client)
    if tx.get('restored') is not True:
        raise ReleaseError('Cannot clear pending before verifying restoration')
    state['pending'] = None
    # The restored baseline now has its generation marker, including bootstrap.
    state['active'] = {key: value for key, value in state['active'].items() if key != 'legacy_marker'}
    write_state(client, release, state)
    tx['aborted'] = True
    save_json(work / 'transaction.json', tx)


def wait_terminal(client, workflow_sha, *, cancel=False, timeout=120):
    publish_site.full_sha(workflow_sha)
    path = '/pages/deployments/' + workflow_sha
    deadline = time.monotonic() + timeout
    cancellation_sent = False
    while time.monotonic() < deadline:
        result = client.request(path)
        if result.get('status') in TERMINAL:
            return result['status']
        if cancel and not cancellation_sent:
            client.request(path + '/cancel', 'POST')
            cancellation_sent = True
        time.sleep(5)
    raise ReleaseError('Could not confirm the Pages deployment terminated; pending state retained')


def confirm_no_deployment_started(client, pending, run):
    """Use the original attempt's explicit skipped steps, never a 404 alone."""
    run_id = str(pending['run_id'])
    attempt = str(pending.get('run_attempt', ''))
    if (not re.fullmatch(r'[1-9][0-9]*', attempt)
            or run.get('id') != int(run_id) or run.get('run_attempt') != int(attempt)):
        raise ReleaseError('Cannot bind the interrupted transaction to the current run attempt')
    jobs, seen, total = [], set(), None
    # Read every page before deciding: a later page can contain another transaction.
    for page in range(1, 11):
        result = client.request(f'/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100&page={page}')
        count, batch = result.get('total_count'), result.get('jobs')
        if (type(count) is not int or not 0 < count <= 1000
                or not isinstance(batch, list) or not 0 < len(batch) <= 100
                or (total is not None and total != count)):
            raise ReleaseError('Incomplete or inconsistent interrupted-attempt jobs')
        total = count
        for job in batch:
            if (not isinstance(job, dict) or type(job.get('id')) is not int
                    or job['id'] in seen or job.get('run_id') != int(run_id)
                    or ('run_attempt' in job and job['run_attempt'] != int(attempt))
                    or job.get('status') != 'completed'):
                raise ReleaseError('Interrupted-attempt jobs do not match the completed run')
            seen.add(job['id'])
            jobs.append(job)
        if len(jobs) == total:
            break
        if len(jobs) > total or len(batch) != 100:
            raise ReleaseError('Incomplete or inconsistent interrupted-attempt jobs')
    else:
        raise ReleaseError('Too many interrupted-attempt jobs to verify safely')
    transactions = [job for job in jobs if job.get('name') in {'publish / transaction', 'rollback / transaction'}]
    if len(transactions) != 1 or not isinstance(transactions[0].get('steps'), list):
        raise ReleaseError('Cannot identify one interrupted Pages transaction job')
    steps = transactions[0]['steps']
    selected = []
    for name in (BEGIN_STEP, *DEPLOY_STEPS):
        matches = [step for step in steps if isinstance(step, dict) and step.get('name') == name]
        if len(matches) != 1 or type(matches[0].get('number')) is not int:
            raise ReleaseError('Missing or ambiguous Pages transaction step evidence')
        selected.append(matches[0])
    begin, deploy, restore = selected
    if (not 0 < begin['number'] < deploy['number'] < restore['number']
            or begin.get('status') != 'completed'
            or begin.get('conclusion') not in {'success', 'failure', 'cancelled', 'timed_out'}
            or any(step.get('status') != 'completed' or step.get('conclusion') != 'skipped'
                   for step in (deploy, restore))):
        raise ReleaseError('A Pages deployment may have started; pending state retained')
    # Do not borrow skipped steps from a rerun, including a rerun begun during pagination.
    current = client.request('/actions/runs/' + run_id)
    if (current.get('id') != int(run_id) or current.get('run_attempt') != int(attempt)
            or current.get('status') != 'completed'):
        raise ReleaseError('The interrupted workflow changed while checking deployment evidence')


def confirm_pending_deployment_stopped(client, pending):
    run_id = str(pending.get('run_id', ''))
    if not re.fullmatch(r'[1-9][0-9]*', run_id):
        raise ReleaseError('Invalid interrupted workflow identity')
    workflow_sha = publish_site.full_sha(pending['workflow_sha'])
    run = client.request('/actions/runs/' + run_id)
    if run.get('status') != 'completed':
        raise ReleaseError('The interrupted workflow is still active')
    try:
        deployment = client.request('/pages/deployments/' + workflow_sha)
    except HTTPError as error:
        if error.code != 404:
            raise
        error.close()
        confirm_no_deployment_started(client, pending, run)
        return
    if deployment.get('status') not in TERMINAL:
        # A later lookup/cancellation failure is ambiguous, not proof of absence.
        wait_terminal(client, workflow_sha, cancel=True)


def quiesce(work, client, deployment_status='', deployment_outcome=''):
    tx = read_json(work / 'transaction.json')
    release, state = load_state(client)
    if state['active'] == tx['candidate'] and state.get('pending') is None:
        # commit PATCH succeeded but its response was lost; don't undo it.
        output(recovery_needed=False)
        return
    if state['active'] != tx['base']:
        raise ReleaseError('Another snapshot is active; refusing recovery')
    pending = state.get('pending')
    if pending is None:
        if deployment_outcome not in {'', 'skipped'}:
            raise ReleaseError('Deployment ran without pending ownership')
        output(recovery_needed=False)
        return
    if pending.get('id') != tx['id']:
        raise ReleaseError('Another transaction owns pending state')
    if deployment_outcome not in {'', 'skipped'} and deployment_status != 'succeed':
        status = wait_terminal(client, tx['workflow_sha'], cancel=True)
        if status == 'succeed':
            expected = (work / 'site' / snapshot.GENERATION_FILE).read_bytes()
            observed = fetch_public(snapshot.GENERATION_FILE + '?snapshot=' + tx['id'])
            if observed != expected:
                raise ReleaseError('Deployment success may belong to an earlier run with the same SHA; pending state retained')
    output(recovery_needed=True)


def verify(work, client, *, previous=False):
    tx, release, state = current_transaction(work, client)
    pointer = dict(tx['base'] if previous else tx['candidate'])
    # After a restore the uploaded archive includes a generation marker.
    pointer.pop('legacy_marker', None)
    verify_tree(work / ('previous' if previous else 'site'), pointer)
    tx['restored' if previous else 'verified'] = True
    save_json(work / 'transaction.json', tx)


def bootstrap(args, client):
    try:
        load_state(client)
    except HTTPError as error:
        if error.code != 404:
            raise
    else:
        raise ReleaseError('Pages state already exists; bootstrap is one-time only')
    args.work.mkdir(parents=True, exist_ok=False)
    info = read_json(args.site / 'build-info.json') if (args.site / 'build-info.json').exists() else None
    tag = 'pages-snapshot-bootstrap-' + publish_site.full_sha(args.legacy_commit)
    shutil.copytree(args.site, args.work / 'site')
    save_json(args.work / 'site' / snapshot.GENERATION_FILE, {'schema_version': 1, 'snapshot_id': tag})
    snapshot.validate(args.work / 'site', allow_legacy=info is None)
    pointer = upload_snapshot(client, args.work / 'site', args.work, tag, allow_legacy=info is None)
    pointer['legacy_marker'] = True
    verify_tree(args.work / 'site', pointer)
    verified_release(client, pointer)
    trusted_sha = client.request('/branches/main')['commit']['sha']
    client.request('/releases', 'POST', {'tag_name': STATE_TAG, 'target_commitish': trusted_sha,
        'name': 'Pages verified deployment state', 'draft': False, 'prerelease': True,
        'make_latest': 'false', 'body': json.dumps({'schema_version': 1, 'active': pointer, 'pending': None}, sort_keys=True)})
    print(json.dumps({'bootstrap': pointer}))


def summary(work):
    path = work / 'transaction.json'
    tx = read_json(path) if path.exists() else {}
    lines = ['## Pages publication', '', f"Snapshot: `{tx.get('id', 'preparation failed')}`",
             f"Previous: `{tx.get('base', {}).get('tag', '')}`", f"Operation: {tx.get('kind', '')}",
             f"Verified: {tx.get('verified', False)}; restored: {tx.get('restored', False)}; committed: {tx.get('committed', False)}",
             '', 'Site: ' + tx.get('base_url', BASE_URL), '', 'Rollback: run Blog rollback with a verified pages-snapshot-* tag or an old master commit. Use active to recover an interrupted transaction.']
    result = '\n'.join(lines) + '\n'
    print(result)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
            stream.write(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ['prepare', 'begin', 'verify', 'commit', 'abort', 'quiesce', 'summary', 'bootstrap']:
        command = commands.add_parser(name)
        command.add_argument('--work', type=Path, required=True)
        if name == 'prepare':
            command.add_argument('--kind', required=True, choices=['production', 'preview', 'cleanup', 'rollback'])
            command.add_argument('--site', type=Path)
            command.add_argument('--context', type=Path)
            command.add_argument('--target')
        if name == 'verify':
            command.add_argument('--previous', action='store_true')
        if name == 'quiesce':
            command.add_argument('--deployment-status', default='')
            command.add_argument('--deployment-outcome', default='')
        if name == 'bootstrap':
            command.add_argument('--site', type=Path, required=True)
            command.add_argument('--legacy-commit', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'summary':
            summary(args.work)
            return 0
        client = GitHub()
        if args.command in {'prepare', 'bootstrap'}:
            globals()[args.command](args, client)
        elif args.command == 'verify':
            verify(args.work, client, previous=args.previous)
        elif args.command == 'quiesce':
            quiesce(args.work, client, args.deployment_status, args.deployment_outcome)
        else:
            globals()[args.command](args.work, client)
        return 0
    except HTTPError as error:
        print(f'GitHub request failed (HTTP {error.code}); no credentials or response body logged.', file=sys.stderr)
    except (ValueError, OSError, KeyError) as error:
        print(str(error), file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
