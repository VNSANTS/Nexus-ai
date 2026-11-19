import contextlib
import io
import json
from pathlib import Path
import sys
from unittest.mock import patch
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from command_input import COMMANDS, Composer, UNAVAILABLE
import nexus as memory
import slash_commands as slash
import terminal_ui as ui
import test_terminal_ui as fixtures
import test_command_input as editor_tests
from test_terminal_ui import FakeRPC


class SlashTests(unittest.TestCase):
    setUp = fixtures.UITests.setUp
    tearDown = fixtures.UITests.tearDown
    primary_turn = fixtures.UITests.primary_turn


def test_menu(self):
    names=[c.name for c in COMMANDS]
    self.assertEqual(len(names),len(set(names)))
    self.assertNotIn('/codex exec',names)
    for name in ['/model','/clear','/compact','/plan','/memory','/permissions','/usage','/help','/quit']:
        model=Composer();model.insert(name)
        self.assertIn(name,[c.name for c in model.matches()])
        self.assertEqual(model.key('ENTER'),name)
SlashTests.test_direct_menu=test_menu


def test_model_editor(self):
    text=editor_tests.PtyTests.run_editor(self,b'model\r')
    self.assertIn("RESULT='/model'",text)
SlashTests.test_real_terminal_model_command=test_model_editor


def test_model(self):
    with patch('builtins.input',return_value='gpt-6.1-terra'):self.chat.command('/model')
    with patch.object(self.chat,'classify_route',side_effect=AssertionError('Modelo manual não precisa de classificador')):
        self.chat.ask('oi')
    self.assertEqual(self.primary_turn()['model'],'gpt-6.1-terra')
    self.chat.command('/model auto');self.chat.ask('oi')
    turns=[p for m,p in self.chat.rpc.calls if m=='turn/start']
    self.assertEqual(turns[-1]['model'],'gpt-6-luna')
    with self.assertRaises(ValueError):self.chat.command('/model invented')
SlashTests.test_model_picker_and_auto=test_model


def test_plan(self):
    self.chat.command('/plan');self.chat.ask('oi')
    self.assertTrue(self.chat.plan_mode)
    self.assertEqual(self.primary_turn()['sandboxPolicy'],{'type':'readOnly'})
    self.assertIn('Não implemente',self.primary_turn()['input'][0]['text'])
    with patch('builtins.input',side_effect=AssertionError('Leitura não autoriza escrita')):
        self.chat.server_request({'id':11,'method':'item/commandExecution/requestApproval','params':{'command':'example'}})
    self.assertEqual(self.chat.rpc.sent[-1]['result']['decision'],'decline')
    self.chat.command('/plan off');self.assertFalse(self.chat.plan_mode)
SlashTests.test_plan_readonly_and_approval=test_plan


def test_permissions(self):
    self.chat.command('/permissions read-only');self.chat.ask('oi')
    self.assertEqual(self.primary_turn()['sandboxPolicy'],{'type':'readOnly'})
    with self.assertRaises(ValueError):self.chat.command('/permissions danger-full-access')
    self.chat.command('/permissions workspace-write');self.assertEqual(self.chat.permission_mode,'workspace-write')
SlashTests.test_session_permissions=test_permissions


def test_effort(self):
    self.chat.command('/effort high');self.chat.ask('oi')
    self.assertEqual(self.primary_turn()['effort'],'high')
    self.chat.command('/effort auto');self.assertIsNone(self.chat.effort_override)
SlashTests.test_effort_override=test_effort


def test_clear(self):
    self.chat.connect();old=self.chat.rpc
    self.chat.command('/clear');self.chat.warm_thread.join(timeout=2)
    self.assertTrue(old.closed);self.assertTrue(self.card.exists())
    self.assertFalse(self.chat.command('/quit'))
SlashTests.test_clear_and_quit_aliases=test_clear


def test_unavailable(self):
    self.assertIn('/setup-bedrock',UNAVAILABLE)
    with patch.object(self.chat,'ask',side_effect=AssertionError('Não enviar comando sem suporte à IA')):
        self.chat.command('/setup-bedrock');self.chat.command('/heapdump')
    self.assertIsNone(self.chat.rpc)
SlashTests.test_unavailable_no_side_effects=test_unavailable


def test_read_commands(self):
    for name in ['/memory','/context','/config','/skills','/init','/tasks','/agents','/warnings','/keymap','/pwd']:
        self.assertTrue(self.chat.command(name))
    self.assertIsNone(self.chat.rpc)
SlashTests.test_read_commands_do_not_call_ai=test_read_commands


def test_compact(self):
    class CompactRPC(FakeRPC):
        def call(self,method,params,**kw):
            result=super().call(method,params,**kw)
            if method=='thread/compact/start':
                self.pending=[{'method':'item/completed','params':{'threadId':'fake-thread','item':{'type':'contextCompaction'}}},
                              {'method':'turn/completed','params':{'threadId':'fake-thread','turn':{'status':'completed'}}}]
            return result
    self.chat.factory=CompactRPC;self.chat.command('/compact')
    self.assertFalse(self.chat.compaction_pending);self.assertFalse(self.chat.rpc.pending)
    self.assertTrue(self.card.exists())
    self.chat.ask('oi');self.assertEqual(self.chat.last_answer,'NEXUS_OK')
SlashTests.test_compact_confirmed_and_next_turn=test_compact


def test_fork(self):
    with patch.object(self.chat,'connect',side_effect=AssertionError('Não iniciar sessão para um recurso indisponível')):
        self.chat.command('/fork')
    self.assertIsNone(self.chat.rpc);self.assertTrue(self.card.exists())
SlashTests.test_fork_limit_does_not_create_transcripts=test_fork



if __name__=='__main__':unittest.main(verbosity=2)
