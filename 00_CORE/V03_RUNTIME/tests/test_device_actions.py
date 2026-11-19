import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'app'))
import device
import install_portable
import nexus as memory
import terminal_actions as actions
import terminal_ui as ui
from test_terminal_ui import FakeRPC


class DeviceActionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.base = self.root/'internal'
        for folder in ['config', 'cache', 'workspace']:(self.base/folder).mkdir(parents=True)
        self.home = self.root/'home'
    def tearDown(self):self.temp.cleanup()
    def test_true_false_unable_persist_and_back_up(self):
        for state in ['true', 'false', 'unable']:
            device.declare(self.base, state, self.home)
            data = device.read(self.base, self.home)
            self.assertEqual(data['root'], state)
            self.assertFalse(data['verified']); self.assertFalse(data['root_execution_authorized'])
        self.assertEqual(len(list((self.base/'backups').glob('device-*.json'))), 2)
    def test_another_device_does_not_inherit_root(self):
        device.declare(self.base, 'true', self.home)
        self.assertEqual(device.read(self.base, self.root/'other-home')['root'], 'unable')
    def test_invalid_state_does_not_change_config(self):
        device.declare(self.base, 'false', self.home)
        before = (self.base/'config/device.json').read_bytes()
        with self.assertRaises(ValueError):device.declare(self.base, 'enable', self.home)
        self.assertEqual(before, (self.base/'config/device.json').read_bytes())
    def test_shell_pipeline_and_status(self):
        runner = actions.Actions(self.root)
        self.assertEqual(runner.shell("printf 'nexus' | tr a-z A-Z > result.txt"), 0)
        self.assertEqual((self.root/'result.txt').read_text(), 'NEXUS')
        self.assertEqual(runner.shell('exit 7'), 7)
    def test_cd_persists_only_in_terminal(self):
        before = Path.cwd(); runner = actions.Actions(self.root)
        (self.root/'with space').mkdir()
        runner.shell("cd 'with space'");runner.shell('pwd > path.txt')
        self.assertEqual((self.root/'with space/path.txt').read_text().strip(), str(self.root/'with space'))
        self.assertEqual(Path.cwd(), before)
    def test_shell_bypasses_agent_and_preserves_pending(self):
        with patch.object(memory,'BASE',self.base), contextlib.redirect_stdout(io.StringIO()):
            chat = ui.Terminal(FakeRPC)
            try:
                chat.pending = 'fala pendente'
                chat.command('!printf ok > test.txt')
                self.assertEqual((self.base/'workspace/test.txt').read_text(), 'ok')
                self.assertIsNone(chat.rpc);self.assertEqual(chat.pending, 'fala pendente')
            finally:chat.close()
    def test_native_all_arguments_are_literal_and_absence_explicit(self):
        runner = actions.Actions(self.root)
        with patch.object(actions.shutil,'which',return_value='/native/codex'), patch.object(actions,'wait',return_value=0) as wait:
            runner.native('codex', 'exec "$(do-not-execute)" --json', self.base, [])
            self.assertEqual(wait.call_args.args[0], ['/native/codex','exec','$(do-not-execute)','--json'])
        with patch.object(actions.shutil,'which',return_value=None):
            with self.assertRaisesRegex(ValueError,'não está instalado'):runner.native('claude','',self.base,[])
    def test_root_change_reaches_next_model_turn_without_restarting(self):
        with patch.object(memory,'BASE',self.base), contextlib.redirect_stdout(io.StringIO()):
            (self.base/'config/library.json').write_text(json.dumps({'id':'test','path':str(self.root/'absent')}))
            (self.base/'config/skills.json').write_text('[]')
            chat = ui.Terminal(FakeRPC)
            try:
                for state in ['false','true','unable']:
                    chat.command('/root '+state);chat.ask('oi')
                turns = [p for m,p in chat.rpc.calls if m=='turn/start']
                for state,turn in zip(['false','true','unable'], turns):
                    self.assertIn('root='+state,turn['input'][-1]['text'])
                    self.assertIn('não concede autorização',turn['input'][-1]['text'])
                self.assertEqual([m for m,p in chat.rpc.calls].count('thread/start'),1)
            finally:chat.close()
    def test_portable_install_rebuilds_paths_and_refuses_overwrite(self):
        source = Path(__file__).resolve().parents[1]
        card = self.root/'NEXUS_MIND';runtime = card/'00_CORE/V03_RUNTIME';runtime.mkdir(parents=True)
        (card/'.nexus-v03-library.json').write_text('{"id":"portable-test"}')
        files = ['app/nexus.py','app/terminal_ui.py','app/device.py','app/terminal_actions.py',
                 'app/command_input.py','app/routing.py','app/device_control.py','app/slash_commands.py','app/slash_reference.json','workspace/AGENTS.md']
        manifest = {}
        for name in files:
            raw = (source/name).read_bytes();target = runtime/name;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(raw);manifest[name]=install_portable.digest(raw)
        raw = b'[]';(runtime/'portable-skills.json').write_bytes(raw);manifest['portable-skills.json']=install_portable.digest(raw)
        (runtime/'SHA256.json').write_text(json.dumps(manifest))
        report=install_portable.install(card,self.home)
        dest=self.home/'nexus-mind';cfg=json.loads((dest/'config/library.json').read_text())
        self.assertEqual(cfg['path'],str(card));self.assertEqual(device.read(dest,self.home)['root'],'unable')
        self.assertTrue(Path(report['launcher']).is_file());self.assertFalse((dest/'cache/search.sqlite3').exists())
        with self.assertRaisesRegex(ValueError,'existente preservada'):install_portable.install(card,self.home)
        (runtime/'app/device.py').write_text('corrupted')
        with self.assertRaisesRegex(ValueError,'Integridade inválida'):install_portable.install(card,self.root/'third-home')
        self.assertFalse((self.root/'third-home/nexus-mind').exists())


if __name__=='__main__':unittest.main(verbosity=2)
