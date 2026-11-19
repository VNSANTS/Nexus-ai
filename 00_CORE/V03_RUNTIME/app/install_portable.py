"""Install a reviewed runtime from a library on another device. No downloads or elevation.

Run: python /PATH/NEXUS_MIND/00_CORE/V03_RUNTIME/app/install_portable.py --library /PATH/NEXUS_MIND
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import re
import shutil
import sys


def digest(data): return hashlib.sha256(data).hexdigest()


def beneath(root, relative):
    path = root / relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Caminho inseguro: ' + str(relative))
    return path


def install(library, home):
    library, home = Path(library).resolve(), Path(home).resolve()
    runtime = library / '00_CORE/V03_RUNTIME'
    dest = home / 'nexus-mind'
    launcher = home / '.local/bin/nexus'
    if dest.exists() or launcher.exists():
        raise ValueError('Instalação existente preservada. Use um destino novo; nenhuma sobrescrita permitida.')
    marker = json.loads((library / '.nexus-v03-library.json').read_text())
    manifest = json.loads((runtime / 'SHA256.json').read_text())
    required = ['app/nexus.py', 'app/terminal_ui.py', 'app/device.py', 'app/terminal_actions.py',
                'app/device_control.py',
                'app/slash_commands.py', 'app/slash_reference.json',
                'app/command_input.py', 'app/routing.py', 'workspace/AGENTS.md', 'portable-skills.json']
    if any(name not in manifest for name in required): raise ValueError('Runtime portátil incompleto')
    # Validate everything before creating the destination. Checksums detect damage, not malicious authorship.
    for name, expected in manifest.items():
        if digest(beneath(runtime, name).read_bytes()) != expected:
            raise ValueError('Integridade inválida: ' + name)
    skills = json.loads((runtime / 'portable-skills.json').read_text())
    for item in skills:
        raw = beneath(library, item['relative_source']).read_bytes()
        if digest(raw) != item['sha256']: raise ValueError('Skill alterada: ' + item['name'])
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}',item['name']):
            raise ValueError('Nome de skill inválido')
    instructions = (runtime / 'workspace/AGENTS.md').read_text()
    # Discovery paths are local; never reuse authentication, active cache, root state or queues.
    old = '/data/data/com.termux/files/home/.local/bin/nexus'
    instructions = instructions.replace(old, str(launcher))
    dest.mkdir(parents=True, exist_ok=False)
    for folder in ['app', 'config', 'cache', 'state/work', 'backups', 'reports', 'workspace']:
        (dest / folder).mkdir(parents=True, exist_ok=True)
    for name in manifest:
        if (name.startswith('app/') and name != 'app/setup_v03.py') or name.startswith(('tests/','plugins/')) or name == 'README.md':
            out = beneath(dest, name); out.parent.mkdir(parents=True, exist_ok=True)
            with out.open('xb') as f: f.write(beneath(runtime, name).read_bytes())
    (dest / 'workspace/AGENTS.md').write_text(instructions)
    for name in ['IDENTITY.snapshot.md', 'INDEX.snapshot.md']:
        src = runtime / 'workspace' / name
        if src.is_file(): shutil.copy2(src, dest / 'workspace' / name)
    (dest / 'config/library.json').write_text(json.dumps(dict(schema=1, id=marker['id'], path=str(library), backend='filesystem'), indent=2)+'\n')
    catalog = []
    for item in skills:
        item = dict(item)
        source = beneath(library, item.pop('relative_source'))
        target = dest / 'workspace/.agents/skills' / item['name'] / 'SKILL.md'
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
        item.update(source=str(source), path=str(target)); catalog.append(item)
    (dest / 'config/skills.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+'\n')
    launcher.parent.mkdir(parents=True, exist_ok=True)
    shell = shutil.which('sh')
    if not shell: raise ValueError('Shell sh ausente')
    with launcher.open('x') as f:
        f.write('#!'+shell+'\nexec '+shlex.quote(sys.executable)+' '+shlex.quote(str(dest/'app/nexus.py'))+' "$@"\n')
    launcher.chmod(0o700)
    # New identity lives outside the copied runtime; no previous device declaration is inherited.
    sys.path.insert(0, str(dest / 'app'))
    import device
    device.declare(dest, 'unable', home, source='instalação nova; declaração necessária')
    return dict(installed=str(dest), launcher=str(launcher), root='unable',
                codex_available=bool(shutil.which('codex')), library=str(library),
                note='Execute nexus sync e nexus doctor. Login existente não é copiado. Nenhum pacote instalado.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', required=True, type=Path)
    parser.add_argument('--home', type=Path, default=Path.home())
    args = parser.parse_args()
    try: print(json.dumps(install(args.library, args.home), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError) as error: parser.exit(1, str(error)+'\n')


if __name__ == '__main__': main()
