#!/usr/bin/env python3
"""Read-only host comparison and explicitly selected BTDD installation.

No network, configuration discovery, project writes, or automatic semantic judgments.
The project lock supplies local provenance, not independent release authentication.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid

ORIGIN = '.playbook-origin.json'
OWNER = 'ai-native/bigital-agent-playbook'
SOURCE_REPOS = frozenset({OWNER, 'bigital/ai-engineering/bigital-agent-playbook'})


class AdoptionError(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(value):
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False).encode())


def safe_path(path):
    """Reject symlink traversal before reading or writing a managed tree."""
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        if part.is_symlink():
            raise AdoptionError(f'symlink path: {part}')
    return path


def inventory(path):
    safe_path(path)
    if not path.exists():
        return {}
    if not path.is_dir():
        raise AdoptionError(f'not a directory: {path}')
    result = {}
    for entry in sorted(path.rglob('*')):
        if entry.is_symlink() or (not entry.is_dir() and not entry.is_file()):
            raise AdoptionError(f'unsafe Skill entry: {entry}')
        if entry.is_file():
            if entry.stat().st_size > 2_000_000:
                raise AdoptionError(f'oversized Skill entry: {entry}')
            result[entry.relative_to(path).as_posix()] = digest(entry.read_bytes())
    return result


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise AdoptionError('invalid Playbook version')
    return tuple(map(int, value.split('.')))


def candidate(project):
    project = safe_path(project)
    lock_path = safe_path(project / '.seed-lock.json')
    lock = json.loads(lock_path.read_text())
    if not isinstance(lock, dict):
        raise AdoptionError('invalid project lock')
    version(lock.get('seed_version'))
    if 'hosted_format' in lock:
        if (type(lock['hosted_format']) is not int or lock['hosted_format'] != 1
                or lock.get('distribution_status') != 'stable'
                or lock.get('source_tag') != 'v' + lock['seed_version']
                or lock.get('source_repo', OWNER) not in SOURCE_REPOS):
            raise AdoptionError('invalid hosted Playbook lock provenance')
    elif lock.get('source_repo') not in SOURCE_REPOS:
        raise AdoptionError('project lock is not Playbook-owned')
    if not re.fullmatch(r'[0-9a-f]{40}', lock.get('source_commit', '')):
        raise AdoptionError('project source commit unavailable')
    files = inventory(project / '.playbook/skills/btdd')
    if 'SKILL.md' not in files or ORIGIN in files:
        raise AdoptionError('project BTDD candidate missing or contains reserved metadata')
    records = lock.get('installed_files', [])
    if not isinstance(records, list):
        raise AdoptionError('invalid project installed files')
    for prefix in ('.playbook/skills/btdd/', '.agents/skills/btdd/'):
        selected = [r for r in records if r.get('target_name', '').startswith(prefix)]
        expected = {r['target_name'][len(prefix):]: r.get('source_sha256') for r in selected}
        if len(expected) != len(selected) or expected != files:
            raise AdoptionError('project BTDD inventory differs from lock')
        if any(r.get('target_sha256') != r.get('source_sha256') for r in selected):
            raise AdoptionError('project BTDD retained local changes')
        if inventory(project / prefix) != files:
            raise AdoptionError('project BTDD projection drift')
    return {'owner': OWNER, 'skill': 'btdd', 'seed_version': lock['seed_version'],
            'source_commit': lock['source_commit'], 'files': files}


def instruction_source(path):
    path = safe_path(path)
    return {'path': str(path), 'sha256': digest(path.read_bytes()) if path.is_file() else None,
            'semantic_status': 'not_assessed'}


def check(project, global_root, instructions=(), also_roots=()):
    project = safe_path(project)
    global_root = safe_path(global_root)
    # Global installation must never target a project projection or a plugin cache.
    if global_root == project or project in global_root.parents or global_root in project.parents:
        raise AdoptionError('global root overlaps project')
    if 'plugins' in global_root.parts or 'cache' in global_root.parts:
        raise AdoptionError('plugin/cache root is not a personal Skill target')
    wanted = candidate(project)
    destination = global_root / 'btdd'
    current = inventory(destination)
    metadata = None
    if ORIGIN in current:
        try:
            metadata = json.loads((destination / ORIGIN).read_text())
        except (ValueError, OSError):
            pass
    actual = {k: v for k, v in current.items() if k != ORIGIN}
    managed = (isinstance(metadata, dict) and metadata.get('owner') in SOURCE_REPOS
               and metadata.get('skill') == 'btdd' and metadata.get('files') == actual
               and isinstance(metadata.get('source_commit'), str)
               and re.fullmatch(r'[0-9a-f]{40}', metadata['source_commit'])
               and isinstance(metadata.get('seed_version'), str)
               and re.fullmatch(r'\d+\.\d+\.\d+', metadata['seed_version']))
    if not destination.exists():
        status = 'absent'
    elif actual == wanted['files']:
        status = 'matching' if managed else 'matching_unmanaged'
    elif managed:
        current_version = version(metadata.get('seed_version'))
        next_version = version(wanted['seed_version'])
        status = ('managed_upgrade_available' if next_version > current_version else
                  'downgrade_blocked' if next_version < current_version else 'same_version_conflict')
    else:
        status = 'unmanaged_or_modified'
    others = []
    for other in also_roots:
        other = safe_path(other)
        if other == global_root:
            continue
        for name in ('btdd', 'test-driven-development'):
            path = other / name
            if path.exists() or path.is_symlink():
                others.append({'path': str(path), 'files': inventory(path)})
    legacy = global_root / 'test-driven-development'
    if legacy.exists() or legacy.is_symlink():
        others.append({'path': str(legacy), 'files': inventory(legacy)})
    report = {'schema_version': 1, 'project': str(project), 'global_root': str(global_root),
              'candidate': wanted, 'current_files': current, 'status': status,
              'other_copies': others, 'instructions': [instruction_source(p) for p in instructions],
              'provenance': 'local_project_lock_not_live_release_verification'}
    report['fingerprint'] = fingerprint(report)
    return report


def install(project, global_root, *, expected, user_host=False, replace_unmanaged=False,
            instructions=(), also_roots=()):
    if not user_host or not expected:
        raise AdoptionError('install requires confirmed user host and reviewed --expected fingerprint')
    report = check(project, global_root, instructions, also_roots)
    if report['fingerprint'] != expected:
        raise AdoptionError('state changed since review; check again')
    status = report['status']
    if report['other_copies']:
        raise AdoptionError('duplicate or legacy Skill copies require explicit resolution before installation')
    if status in ('same_version_conflict', 'downgrade_blocked'):
        raise AdoptionError(status)
    if status == 'unmanaged_or_modified' and not replace_unmanaged:
        raise AdoptionError('personal or modified Skill requires reviewed --replace-unmanaged selection')
    if status in ('matching', 'matching_unmanaged'):
        return {**report, 'action': 'noop', 'discovery': 'reload_and_verify'}
    global_root = safe_path(global_root)
    global_root.mkdir(parents=True, exist_ok=True)
    destination = global_root / 'btdd'
    lock_dir = global_root / '.btdd-install-lock'
    try:
        lock_dir.mkdir()
    except FileExistsError as exc:
        raise AdoptionError('another BTDD installation is active; inspect stale lock manually') from exc
    backup = None
    try:
        if check(project, global_root, instructions, also_roots)['fingerprint'] != expected:
            raise AdoptionError('state changed before installation')
        with tempfile.TemporaryDirectory(prefix='.btdd-stage-', dir=global_root.parent) as stage:
            staged = Path(stage) / 'btdd'
            staged.mkdir()
            for relative in report['candidate']['files']:
                source = safe_path(Path(project) / '.playbook/skills/btdd' / relative)
                target = staged / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
            if inventory(staged) != report['candidate']['files']:
                raise AdoptionError('candidate changed during staging')
            (staged / ORIGIN).write_text(json.dumps(report['candidate'], indent=2) + '\n')
            if check(project, global_root, instructions, also_roots)['fingerprint'] != expected:
                raise AdoptionError('state changed during staging')
            # From the first rename onwards, every failure belongs to this transaction.
            moved_original = False
            reserved_inode = None
            staged_inode = staged.stat().st_ino
            try:
                if destination.exists():
                    backup_root = safe_path(global_root.parent / 'playbook-skill-backups')
                    backup_root.mkdir(exist_ok=True)
                    backup = backup_root / ('btdd-' + uuid.uuid4().hex)
                    destination.rename(backup)
                    moved_original = True
                    if inventory(backup) != report['current_files']:
                        raise AdoptionError('global Skill changed during swap')
                # Never replace a directory created by another writer after the check.
                destination.mkdir()
                reserved_inode = destination.stat().st_ino
                os.replace(staged, destination)
                expected_files = {**report['candidate']['files'], ORIGIN: digest((destination / ORIGIN).read_bytes())}
                if inventory(destination) != expected_files:
                    raise AdoptionError('post-write readback failed')
                if json.loads((destination / ORIGIN).read_text()) != report['candidate']:
                    raise AdoptionError('post-write provenance mismatch')
            except Exception as exc:
                if not moved_original and reserved_inode is None:
                    raise
                try:
                    safe_path(destination)
                    if destination.exists():
                        if reserved_inode is None or destination.stat().st_ino not in (reserved_inode, staged_inode):
                            raise AdoptionError('destination now belongs to another writer')
                        shutil.rmtree(destination)
                    if moved_original:
                        backup.rename(destination)
                except Exception as recovery_error:
                    raise AdoptionError(f'recovery blocked; original retained at {backup}: {recovery_error}') from exc
                raise
        return {**report, 'action': 'installed', 'backup': str(backup) if backup else None,
                'discovery': 'reload_and_verify'}
    finally:
        lock_dir.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('check', 'install'))
    parser.add_argument('--project', type=Path, default=Path.cwd())
    parser.add_argument('--global-root', type=Path, default=Path(os.environ.get('CODEX_HOME', Path.home()/'.codex'))/'skills')
    parser.add_argument('--also-root', action='append', type=Path, default=[])
    parser.add_argument('--instruction', action='append', type=Path, default=[])
    parser.add_argument('--expected')
    parser.add_argument('--user-host', action='store_true')
    parser.add_argument('--replace-unmanaged', action='store_true')
    args = parser.parse_args()
    try:
        if args.action == 'check':
            if args.expected or args.user_host or args.replace_unmanaged:
                raise AdoptionError('installation options are not valid with check')
            result = check(args.project, args.global_root, args.instruction, args.also_root)
        else:
            result = install(args.project, args.global_root, expected=args.expected, user_host=args.user_host,
                             replace_unmanaged=args.replace_unmanaged, instructions=args.instruction, also_roots=args.also_root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (AdoptionError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
