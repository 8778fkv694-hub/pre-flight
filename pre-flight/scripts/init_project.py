#!/usr/bin/env python3
"""Preview or create an SDLC document skeleton in a new, empty directory."""
import argparse
from datetime import date
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--target', required=True)
    ap.add_argument('--project-name', required=True)
    ap.add_argument('--adapters', default='agents', help='agents,claude,gemini or none')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    target = Path(a.target).expanduser().absolute()
    if target.is_symlink():
        ap.error('Target must not be a symlink')
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        ap.error('Target must be absent or empty; inspect existing projects manually')
    name = a.project_name.strip()
    if not name or any(c in name for c in '\r\n\x00'):
        ap.error('Project name must be a non-empty single line')
    names = {'agents': 'AGENTS.md', 'claude': 'CLAUDE.md', 'gemini': 'GEMINI.md'}
    selected = [x.strip() for x in a.adapters.split(',')]
    if selected == ['none']:
        selected = []
    if any(x not in names for x in selected):
        ap.error('Unknown adapter; use agents,claude,gemini or none')
    source = Path(__file__).resolve().parents[1] / 'assets/project-template'
    files = {}
    for p in sorted(source.rglob('*.md')):
        files[p.relative_to(source)] = p.read_text(encoding='utf-8').replace('{{PROJECT_NAME}}', name).replace('{{DATE}}', date.today().isoformat())
    for adapter in set(selected):
        files[Path(names[adapter])] = '# Project entry / 项目入口\n\nRead [AGENT.md](AGENT.md) for shared rules and [STATUS.md](STATUS.md) for current state before working.\n开始前读取 AGENT.md 与 STATUS.md；规则只维护在 AGENT.md。\n'
    if not a.apply:
        print('DRY RUN — no files written: ' + str(target))
        for p in sorted(files):
            print(str(p))
        return
    target.mkdir(parents=True, exist_ok=True)
    # Refuse an unexpectedly populated destination immediately before writing.
    if any(target.iterdir()):
        ap.error('Target changed since inspection; refusing to write')
    for rel, content in files.items():
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('x', encoding='utf-8') as stream:
            stream.write(content)
    print('Created %d files in %s; application not implemented or verified.' % (len(files), target))


if __name__ == '__main__':
    main()
