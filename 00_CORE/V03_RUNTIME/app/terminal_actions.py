"""Explicit terminal actions never pass through an AI or capture their output."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess

CODEX_COMMANDS = ('agents', 'exec', 'review', 'login', 'logout', 'mcp', 'plugin',
    'app-server', 'remote-control', 'completion', 'update', 'doctor', 'sandbox',
    'debug', 'apply', 'resume', 'queue', 'archive', 'delete', 'migrate-rollouts',
    'unarchive', 'fork', 'cloud', 'exec-server', 'features', 'help')


def wait(argv, cwd):
    child = subprocess.Popen(argv, cwd=cwd)
    try:
        return child.wait()
    except KeyboardInterrupt:
        # Foreground terminal already sends SIGINT to both parent and child.
        try:
            child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            child.terminate()
            try: child.wait(timeout=2)
            except subprocess.TimeoutExpired: child.kill(); child.wait()
        raise


class Actions:
    def __init__(self, cwd):
        self.cwd = Path(cwd)

    def native_git_diff(self, cwd):
        git=shutil.which('git')
        if not git:raise ValueError('git não está instalado')
        return wait([git, '--no-pager', 'diff', '--no-ext-diff', '--no-textconv'], cwd)

    def shell(self, command):
        command = command.strip()
        if not command:
            raise ValueError('Use !comando, por exemplo !pwd. !cd CAMINHO muda a pasta do terminal.')
        # A plain cd updates only this terminal session. Compound syntax goes to the shell.
        parts = shlex.split(command)
        if parts and parts[0] == 'cd' and len(parts) <= 2 and not any(c in command for c in ';|&><`$\n'):
            dest = Path(os.path.expanduser(parts[1])) if len(parts) == 2 else Path.home()
            dest = (self.cwd / dest).resolve() if not dest.is_absolute() else dest.resolve()
            if not dest.is_dir(): raise ValueError('Pasta não encontrada: ' + str(dest))
            self.cwd = dest
            return 0
        shell = os.environ.get('SHELL') or shutil.which('sh')
        return wait([shell, '-c', command], self.cwd)

    def native(self, program, arguments, base, roots):
        executable = shutil.which(program)
        if executable is None:
            raise ValueError(program + ' não está instalado neste dispositivo. Nenhum comando executado.')
        args = shlex.split(arguments)
        if program == 'codex' and not args:
            args = ['--no-daemon', '--sandbox', 'workspace-write', '--ask-for-approval', 'on-request']
            for root in roots: args += ['--add-dir', root]
        # argv passthrough covers the installed CLI, including flags; never eval or shell=True.
        return wait([executable] + args, Path(base) / 'workspace')
