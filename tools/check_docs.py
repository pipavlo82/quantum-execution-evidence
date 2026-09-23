"""Offline documentation inventory, links, references and frozen-byte checks.

This maintainer gate is Git-bound, outside the frozen runtime profile inventories.
It validates finite documented contracts; it does not prove prose semantics.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'docs/documentation-audit.json'


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def anchors(text):
    result, seen = set(), {}
    for title in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', text, re.M):
        slug = re.sub(r'[^\w\- ]', '', title.lower()).replace(' ', '-')
        index = seen.get(slug, 0)
        seen[slug] = index + 1
        result.add(slug + (f'-{index}' if index else ''))
    return result


def run():
    manifest = json.loads(MANIFEST.read_bytes())
    expected = manifest['documents']
    actual = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')
                    if p.is_file() and '.git' not in p.parts
                    and (p.suffix.lower() == '.md' or p.name.upper().startswith('README')))
    need(actual == sorted(expected), 'DOCUMENT_INVENTORY_CHANGED')
    links, references, commands = 0, 0, set()
    for name in actual:
        raw = (ROOT / name).read_bytes()
        text = raw.decode('utf-8')
        if expected[name]['disposition'] == 'updated' or name == 'docs/DOCUMENTATION_AUDIT.md':
            need(b'\r' not in raw, 'DOCUMENT_NOT_LF:' + name)
        for target in re.findall(r'\[[^\]\n]+\]\(([^)\n]+)\)', text):
            parts = urlsplit(target)
            if parts.scheme or parts.netloc:
                continue
            path = ((ROOT / name).parent / unquote(parts.path)).resolve() if parts.path else ROOT / name
            need(path.is_relative_to(ROOT) and path.exists(), f'BROKEN_LINK:{name}:{target}')
            if parts.fragment:
                need(path.is_file() and unquote(parts.fragment) in anchors(path.read_text(encoding='utf-8')),
                     f'BROKEN_ANCHOR:{name}:{target}')
            links += 1
        # Code-formatted repository paths are root-relative. Upstream vendor
        # prose intentionally uses paths in the original repository instead.
        if not name.startswith('vendor/'):
            for ref in re.findall(r'`((?:qev|profiles|fixtures|tools|docs|vendor)/[^`\s]+)`', text):
                need((ROOT / ref).exists(), f'BROKEN_CODE_REFERENCE:{name}:{ref}')
                references += 1
            commands.update(re.findall(r'python(?: -B)?(?: -O)? -m ([\w.]+)(?: ([a-z][\w-]*))?', text))

    for module, command in sorted(commands):
        need((ROOT / (module.replace('.', '/') + '.py')).exists()
             or (ROOT / module.replace('.', '/') / '__main__.py').exists()
             or module == 'unittest', 'CLI_MODULE:' + module)
        if module == 'qev':
            source = (ROOT / 'qev/__main__.py').read_text(encoding='utf-8')
            need(repr(command) in source, 'CLI_SUBCOMMAND:' + command)
        if module in ('qev.cross_cli', 'qev.moth_rvr_cli'):
            need(command in ('demo', 'replay', 'sources'), 'CROSS_CLI_SUBCOMMAND:' + command)

    from qev import sources, source_inventory
    from qev.cross_provider import FILES, check_sources
    source_result = sources.validate()
    need(sources.successful(source_result), 'MAIN_SOURCE_LOCK')
    check_sources()
    from qev import moth_rvr
    moth_rvr.check_sources()
    counts = manifest['counts']
    need(len(moth_rvr.FILES) == counts['mothRvrFiles'], 'MOTH_RVR_SOURCE_COUNT')
    need(len(source_inventory.LOCAL_FILES) == counts['localFiles'], 'LOCAL_COUNT')
    need(len(source_inventory.ALL_VENDOR_FILES) == counts['vendorFiles'], 'VENDOR_COUNT')
    need(len(FILES) == counts['crossFiles'], 'CROSS_COUNT')
    reference_rows = json.loads((ROOT / 'docs/reference-pins.json').read_bytes())['records']
    need(len(reference_rows) == counts['referenceRecords'], 'REFERENCE_COUNT')
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), top_level_dir=str(ROOT))
    need(suite.countTestCases() == counts['tests'], 'TEST_COUNT')

    for filename, profile_id in manifest['profileIds'].items():
        need(json.loads((ROOT / filename).read_bytes())['profileId'] == profile_id, 'PROFILE_ID:' + filename)

    dependencies = 0
    def walk(value):
        nonlocal dependencies
        if isinstance(value, dict):
            if 'path' in value and 'sha256' in value:
                path = ROOT / value['path']
                need(path.is_file() and sha(path.read_bytes()) == value['sha256'],
                     'PROFILE_DEPENDENCY:' + value['path'])
                dependencies += 1
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    for filename in manifest['profileIds']:
        walk(json.loads((ROOT / filename).read_bytes()))

    frozen = manifest['frozenFiles']
    need(len(frozen) == counts['frozenFiles'], 'FROZEN_COUNT')
    for name, digest in frozen.items():
        need(sha((ROOT / name).read_bytes()) == digest, 'FROZEN_BYTES:' + name)

    workflow = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
    steps = re.findall(r'^      - name: (.+)$', workflow, re.M)
    need(steps == manifest['ciSteps'], 'CI_STEP_INVENTORY')
    need('python: ["3.12", "3.13"]' in workflow and "bun-version: '1.3.14'" in workflow
         and 'node-version: "22"' in workflow, 'CI_RUNTIME_MATRIX')
    need('python -B -m tools.check_docs' in workflow, 'DOCS_NOT_IN_CI')
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    for token in ('**293 tests**', '**47 kills**', '**214 local + 28 vendored files**', '**8 files**', '**13 files**'):
        need(token in readme, 'README_COUNT:' + token)
    for name, digest in manifest['legalFiles'].items():
        need(sha((ROOT / name).read_bytes()) == digest, 'LEGAL_FILE:' + name)
    license_text = (ROOT / 'LICENSE').read_text(encoding='utf-8')
    notice_text = (ROOT / 'NOTICE').read_text(encoding='utf-8')
    package_text = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
    licensing_text = (ROOT / 'LICENSING.md').read_text(encoding='utf-8')
    need('Apache License\nVersion 2.0, January 2004' in license_text, 'ROOT_LICENSE_NOT_APACHE_2_0')
    need('Copyright 2026 Pavlo Tvardovskyi' in notice_text, 'NOTICE_COPYRIGHT')
    need('license = { file = "LICENSE" }' in package_text
         and 'license-status = "apache-2.0"' in package_text, 'PACKAGE_LICENSE_METADATA')
    for token in ('preserved historical evidence', 'not relicensed', 'vendor/semantic-abi/',
                  'vendor/rvr-v0/', 'vendor/receiptos-v0/', 'vendor/tsei-v0/'):
        need(token in licensing_text, 'LICENSING_SCOPE:' + token)
    tracked = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, check=True,
                             stdout=subprocess.PIPE).stdout.decode().split('\0')
    allowed = set(frozen) | set(manifest['mutableFiles']) | set(manifest['auditFiles']) | set(manifest['featureFiles'])
    need(set(filter(None, tracked)) <= allowed, 'UNREVIEWED_TRACKED_FILE')
    for name in manifest['mutableFiles'] + manifest['auditFiles'] + manifest['featureFiles']:
        need(b'\r' not in (ROOT / name).read_bytes(), 'EDITED_FILE_NOT_LF:' + name)
    return {'status': 'PASS', 'documents': len(actual), 'internalLinks': links,
            'codePathReferences': references, 'cliModuleCommandPairs': len(commands),
            'profileDependencyPins': dependencies, 'frozenFiles': len(frozen),
            'ciSteps': len(steps), 'counts': counts,
            'scope': 'Offline finite consistency; no external URL liveness or upstream re-audit'}


if __name__ == '__main__':
    try:
        result, code = run(), 0
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as exc:
        result, code = {'status': 'FAIL', 'reason': str(exc)}, 1
    sys.stdout.write(json.dumps(result, sort_keys=True, indent=2) + '\n')
    sys.exit(code)
