"""Local capability declarations; no privilege probes or elevation."""
import datetime
import json
import os
from pathlib import Path
import platform
import shutil
import tempfile
import uuid

STATES = {'true': 'root existente (declarado)', 'false': 'sem root (declarado)',
          'unable': 'root indisponível ou não confirmado'}


def identity(home=None):
    home = Path.home() if home is None else Path(home)
    path = home / '.local/state/nexus/device-id'
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('x') as f:
            f.write(uuid.uuid4().hex)
        path.chmod(0o600)
    except FileExistsError:
        pass
    return path.read_text().strip()


def read(base, home=None):
    device_id = identity(home)
    path = Path(base) / 'config/device.json'
    try:
        data = json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        data = {}
    valid = data.get('device_id') == device_id and data.get('root') in STATES
    return dict(schema=1, device_id=device_id, root=data['root'] if valid else 'unable',
                source=data.get('source', 'não declarado') if valid else 'não declarado neste dispositivo',
                verified=False, root_execution_authorized=False,
                system=platform.system(), architecture=platform.machine(),
                process_euid=os.geteuid() if hasattr(os, 'geteuid') else None)


def declare(base, state, home=None, source='usuário: /root'):
    if state not in STATES:
        raise ValueError('Use /root true, /root false ou /root unable')
    base = Path(base)
    path = base / 'config/device.json'
    data = read(base, home)
    data.update(root=state, source=source, updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    if path.exists():
        old = json.loads(path.read_text())
        if old.get('root') == state and old.get('device_id') == data['device_id']:
            return data
        backup = base / 'backups' / ('device-' + uuid.uuid4().hex + '.json')
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.device-')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp): os.unlink(temp)
    return data


def context(base, home=None):
    data = read(base, home)
    return ('Ambiente local informado pelo Nexus: root=' + data['root'] + ' (' + STATES[data['root']] + '). '
            'Fonte: declaração local, sem teste de su. A declaração descreve disponibilidade, '
            'não concede autorização para usar root nem muda permissões. As restrições da tarefa continuam válidas.')
