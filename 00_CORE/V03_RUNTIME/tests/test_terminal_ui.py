import argparse,base64,contextlib,importlib,json,io,os,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import nexus as memory
import terminal_ui as ui
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a1ioAAAAASUVORK5CYII=')
class FakeRPC:
 def __init__(self):self.calls=[];self.sent=[];self.pending=[];self.closed=False
 def start(self):return {'version':'test'}
 def call(self,method,params,**kw):
  self.calls.append((method,params))
  if method=='thread/start':return {'thread':{'id':'fake-router' if params.get('baseInstructions') else 'fake-thread'},'model':params.get('model','gpt-6.1-sol')}
  if method=='model/list':return {'data':[{'model':m,'inputModalities':['text','image']} for m in ['gpt-6.1-sol','gpt-6-luna','gpt-6.1-terra','gpt-6-astra']]}
  if method=='turn/start' and params.get('outputSchema'):
   self.pending=[{'method':'item/agentMessage/delta','params':{'threadId':'fake-router','itemId':'route','delta':json.dumps({'task':'chat','complexity':'low','reason':'Classificação de teste'})}}, {'method':'turn/completed','params':{'threadId':'fake-router','turn':{'status':'completed'}}}]
   return {'turn':{'id':'router-turn'}}
  if method=='turn/start':
   self.pending=[{'method':'item/agentMessage/delta','params':{'threadId':'fake-thread','itemId':'a','delta':'NEXUS_'}},
    {'method':'item/agentMessage/delta','params':{'threadId':'fake-thread','itemId':'a','delta':'OK'}},
    {'method':'turn/completed','params':{'threadId':'fake-thread','turn':{'status':'completed'}}}]
   return {'turn':{'id':'fake-turn'}}
  return {}
 def pump(self,timeout=1):self.callback(self.pending.pop(0))
 def request(self,method,params):self.calls.append((method,params));return len(self.calls)
 def send(self,msg):self.sent.append(msg)
 def close(self):self.closed=True
class UITests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.old=memory.BASE;memory.BASE=self.root/'internal';self.card=self.root/'card';self.card.mkdir()
  for d in ['config','cache','workspace']:(memory.BASE/d).mkdir(parents=True,exist_ok=True)
  (memory.BASE/'config/library.json').write_text(json.dumps({'id':'test','path':str(self.card)}))
  (self.card/'.nexus-v03-library.json').write_text('{"id":"test"}')
  (memory.BASE/'config/skills.json').write_text('[]')
  self.picture=self.root/'foto.png';self.picture.write_bytes(PNG)
  self.silent=contextlib.redirect_stdout(io.StringIO());self.silent.__enter__();self.chat=ui.Terminal(FakeRPC)
 def tearDown(self):self.chat.close();self.silent.__exit__(None,None,None);memory.BASE=self.old;self.tmp.cleanup()
 def primary_turn(self):
  return next(params for method,params in self.chat.rpc.calls if method=='turn/start' and params.get('threadId')=='fake-thread')
 def test_thread_and_turn_permissions_and_stream(self):
  self.chat.ask('olá')
  self.assertEqual(self.chat.last_answer,'NEXUS_OK')
  start=self.chat.rpc.calls[0];self.assertEqual(start[1]['sandbox'],'workspace-write');self.assertTrue(start[1]['ephemeral'])
  turn=self.primary_turn();self.assertEqual(turn['sandboxPolicy']['type'],'workspaceWrite')
  self.assertEqual(turn['sandboxPolicy']['writableRoots'],[str(memory.BASE),str(self.card)])
 def test_photo_snapshot_send_cleanup_preserves_original(self):
  self.chat.add_image(str(self.picture));snapshot=self.chat.attachments[0]
  self.assertNotEqual(snapshot,self.picture);self.assertEqual(snapshot.read_bytes(),PNG)
  self.chat.ask('O que aparece?')
  inputs=self.primary_turn()['input'];self.assertEqual(inputs[1],{'type':'localImage','path':str(snapshot)})
  self.assertFalse(snapshot.exists());self.assertEqual(self.picture.read_bytes(),PNG)
 def test_bad_image_and_android_uri_rejected(self):
  p=self.root/'bad.png';p.write_text('texto sem imagem')
  with self.assertRaises(ValueError):self.chat.add_image(str(p))
  with self.assertRaises(ValueError):ui.image_path('content://media/external/images/1')
 def test_latest_screenshot_selection_and_stale_excluded(self):
  folder=self.root/'Screenshots';folder.mkdir()
  old=folder/'old.png';old.write_bytes(PNG);os.utime(old,(1,1))
  latest=folder/'recent.png';latest.write_bytes(PNG)
  found=ui.recent_screenshots([str(folder)])
  self.assertEqual(found,[latest])
  with patch.object(ui,'recent_screenshots',return_value=found):self.chat.command('/print')
  self.assertEqual(len(self.chat.attachments),1);self.assertEqual(latest.read_bytes(),PNG)
 def test_clipboard_path(self):
  with patch.object(ui,'run_android',return_value='file://'+str(self.picture)) as android:
   self.chat.clipboard();self.assertEqual(len(self.chat.attachments),1);self.assertEqual(android.call_args[0][0],['termux-clipboard-get'])
 def test_picker_mock(self):
  def pick(cmd,**kw):Path(cmd[1]).write_bytes(PNG);return ''
  with patch.object(ui,'run_android',side_effect=pick):self.chat.pick_image()
  self.assertEqual(len(self.chat.attachments),1);self.assertEqual(len(list(Path(self.chat.staging.name).iterdir())),1)
 def test_voice_requires_explicit_send(self):
  with patch.object(ui,'run_android',return_value=json.dumps({'code':0,'text':'Mensagem ditada','error':''})):
   self.chat.voice();self.assertEqual(self.chat.pending,'Mensagem ditada');self.assertIsNone(self.chat.rpc)
  self.chat.command('/enviar');self.assertIsNone(self.chat.pending)
  self.assertIn('Mensagem ditada',self.primary_turn()['input'][0]['text'])
 def test_voice_cancel_does_not_send(self):
  with patch.object(ui,'run_android',return_value=json.dumps({'code':0,'text':'Fala cancelada','error':''})):self.chat.voice()
  self.chat.command('/cancelar');self.assertIsNone(self.chat.pending);self.assertIsNone(self.chat.rpc)
 def test_voice_json_errors_never_become_transcript(self):
  self.chat.pending='Texto anterior'
  for raw in ['}', '{"error":"ERROR_SPEECH_TIMEOUT"}', '{"text":""}', '[]']:
   with patch.object(ui,'run_android',return_value=raw):
    with self.assertRaises(ValueError):self.chat.voice()
   self.assertIsNone(self.chat.pending);self.assertIsNone(self.chat.rpc)
 def test_voice_dialog_backend_and_cancel(self):
  with patch.object(ui,'run_android',return_value='{"code":-2,"text":""}') as android:
   self.chat.voice();self.assertIsNone(self.chat.pending)
   self.assertEqual(android.call_args[0][0][:2],['termux-dialog','speech'])
 def test_android_success_with_empty_error_field(self):
  result=type('Result',(),{'returncode':0,'stdout':'{"code":0,"text":"olá","error":""}','stderr':''})()
  with patch.object(ui.shutil,'which',return_value='/fake'),patch.object(ui.subprocess,'run',return_value=result):
   self.assertEqual(ui.parse_voice(ui.run_android(['termux-dialog','speech'])),'olá')
 def test_prepare_cooldown_and_force(self):
  self.assertTrue(self.chat.prepare());self.assertFalse(self.chat.prepare());self.assertTrue(self.chat.prepare(force=True))
 def test_social_message_has_no_reference_payload_and_uses_low(self):
  with patch.object(memory,'context',side_effect=AssertionError('Não deve buscar manual para conversa social')):
   self.chat.ask('Você consegue me ouvir?')
  turn=self.primary_turn()
  self.assertEqual(turn['input'][0]['text'],'Você consegue me ouvir?');self.assertIn('root=unable',turn['input'][-1]['text']);self.assertEqual(turn['effort'],'low')
  self.assertNotIn('Você',json.dumps(memory.load(memory.BASE/'state/last-latency.json')))
 def test_deep_mode_and_timing(self):
  self.chat.command('/modo profundo');self.chat.ask('oi')
  self.assertEqual(self.primary_turn()['effort'],'high');self.assertIn('total_seconds',self.chat.timings)
 def test_compact_context_excludes_runtime_and_preserves_knowledge(self):
  runtime=self.card/'00_CORE/V03_RUNTIME';runtime.mkdir(parents=True);(runtime/'manual.md').write_text('orquidea manual interno')
  k=self.card/'02_KNOWLEDGE';k.mkdir();(k/'nota.md').write_text('orquidea conhecimento revisado')
  memory.sync();ctx=memory.context('a orquidea',compact=True)
  self.assertEqual([r['path'] for r in ctx['memories']],['02_KNOWLEDGE/nota.md'])
  self.assertEqual(len(memory.search('orquidea')),2)
 def test_router_agent_is_readonly_and_has_no_shell_tools(self):
  self.chat.connect();result=self.chat.classify_route('Preciso de uma ideia para uma festa')
  self.assertEqual(result['task'],'chat')
  start=next(p for m,p in self.chat.rpc.calls if m=='thread/start' and p.get('baseInstructions'))
  self.assertEqual(start['sandbox'],'read-only');self.assertEqual(start['approvalPolicy'],'never')
  self.assertFalse(start['config']['features.shell_tool']);self.assertFalse(start['config']['features.apps'])
 def test_router_does_not_change_primary_conversation_id(self):
  self.chat.ask('Mensagem ditada');self.assertEqual(self.chat.thread,'fake-thread')
  self.assertEqual(self.chat.routing_thread,'fake-router');self.assertEqual(self.primary_turn()['model'],'gpt-6-luna')
  self.chat.ask('Em Python explique um print');self.assertEqual(self.primary_turn()['threadId'],'fake-thread')
  turns=[p for m,p in self.chat.rpc.calls if m=='turn/start' and p.get('threadId')=='fake-thread']
  self.assertEqual(turns[-1]['model'],'gpt-6.1-terra')
 def test_unknown_request_declined(self):
  self.chat.connect();self.chat.server_request({'id':91,'method':'unknown/request','params':{}})
  self.assertEqual(self.chat.rpc.sent[-1]['error']['code'],-32601)
 def test_approval_requires_explicit_yes(self):
  self.chat.connect()
  with patch('builtins.input',return_value=''):
   self.chat.server_request({'id':11,'method':'item/commandExecution/requestApproval','params':{'command':'example'}})
  self.assertEqual(self.chat.rpc.sent[-1]['result']['decision'],'decline')
 def test_permission_expansion_not_granted(self):
  self.chat.connect();self.chat.server_request({'id':1,'method':'item/permissions/requestApproval','params':{}})
  self.assertEqual(self.chat.rpc.sent[-1]['result']['permissions'],{})
 def test_remember_pending_and_originals_untouched(self):
  with patch('builtins.input',return_value='s'):self.chat.remember('Preferência fictícia de teste')
  hits=memory.search('fictícia',pending=True);self.assertTrue(hits);self.assertEqual(hits[0]['validation'],'pending')
  self.assertFalse(memory.search('fictícia'));self.assertEqual(self.picture.read_bytes(),PNG)
 def test_spoken_greeting_does_not_load_documents_or_skills(self):
  phrase='alô alô você daí eu de cá vamos conversar e aí Nexus como que tá'
  with patch.object(memory,'context',side_effect=AssertionError('Saudação não exige documentos')):
   self.chat.ask(phrase)
  self.assertEqual(self.primary_turn()['input'][0],{'type':'text','text':phrase});self.assertEqual(len(self.primary_turn()['input']),2)
  self.assertTrue(self.chat.timings['context_omitted_for_social'])
 def test_greeting_with_technical_task_still_retrieves(self):
  self.assertFalse(ui.smalltalk('Alô Nexus preciso corrigir código Python'))
  path=memory.BASE/'config/skills.json';path.write_text(json.dumps([dict(name='nexus-programacao',category='Programação',triggers='python código',description='Diagnosticar código')]))
  self.assertFalse(memory.skills('Nexus'))
  self.assertEqual(memory.skills('Nexus corrigir Python')[0]['name'],'nexus-programacao')
 def test_warmup_reuses_connection_and_starts_no_model_turn(self):
  self.chat.warmup();self.chat.warm_thread.join(timeout=2)
  rpc=self.chat.rpc;self.assertEqual(self.chat.connection_state(),'pronto')
  self.assertEqual([m for m,_ in rpc.calls],['thread/start','model/list'])
  self.chat.ask('olá');self.assertIs(self.chat.rpc,rpc)
  self.assertEqual([m for m,_ in rpc.calls].count('thread/start'),1)
 def test_slow_warmup_does_not_block_composer(self):
  entered=threading.Event();release=threading.Event()
  class SlowRPC(FakeRPC):
   def start(self):entered.set();release.wait(timeout=2);return {}
   def close(self):super().close();release.set()
  self.chat.factory=SlowRPC
  started=time.perf_counter();self.chat.warmup();self.assertLess(time.perf_counter()-started,.2)
  self.assertTrue(entered.wait(timeout=1));self.assertEqual(self.chat.connection_state(),'conectando em segundo plano')
  release.set();self.chat.warm_thread.join(timeout=2);self.assertEqual(self.chat.connection_state(),'pronto')
 def test_background_approval_is_never_automatic_accept(self):
  class ApprovalRPC(FakeRPC):
   def start(self):self.callback({'id':8,'method':'item/commandExecution/requestApproval','params':{'command':'example'}});return {}
  self.chat.factory=ApprovalRPC
  with patch('builtins.input',side_effect=AssertionError('Sem input em background')):
   self.chat.warmup();self.chat.warm_thread.join(timeout=2)
  self.assertEqual(self.chat.rpc.sent[0]['result']['decision'],'decline')
 def test_close_while_connection_is_starting(self):
  entered=threading.Event();release=threading.Event()
  class SlowRPC(FakeRPC):
   def start(self):entered.set();release.wait(timeout=2);return {}
   def close(self):super().close();release.set()
  self.chat.factory=SlowRPC;self.chat.warmup();self.assertTrue(entered.wait(timeout=1))
  self.chat.disconnect();self.assertIsNone(self.chat.rpc);self.assertFalse(self.chat.warm_thread)
 def test_no_terminal_escape_in_untrusted_output(self):
  self.assertEqual(ui.clean('\x1b[2Jola\x07'),'[2Jola')
 def test_native_launcher_explicit_sandbox(self):
  with patch.object(os,'execvp') as execute:
   memory.launch(argparse.Namespace(prompt=None,dry_run=False))
  args=execute.call_args[0][1]
  self.assertEqual(args[args.index('--sandbox')+1],'workspace-write');self.assertNotIn('--dangerously-bypass-approvals-and-sandbox',args)
 def test_new_chat_preserves_permanent_memory(self):
  self.chat.connect();rpc=self.chat.rpc;self.chat.command('/novo');self.assertTrue(rpc.closed);self.assertTrue(self.card.is_dir())
  self.chat.warm_thread.join(timeout=2);self.assertEqual(self.chat.connection_state(),'pronto')
if __name__=='__main__':unittest.main(verbosity=2)
