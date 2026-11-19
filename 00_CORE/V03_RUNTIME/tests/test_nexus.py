"""Integration tests with isolated fixture; never unmounts or alters real library."""
import hashlib,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
APP=Path(__file__).resolve().parents[1]/'app/nexus.py'
class NexusTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.home=self.root/'internal';self.card=self.root/'card'
  self.card.mkdir();(self.home/'config').mkdir(parents=True)
  (self.card/'.nexus-v03-library.json').write_text(json.dumps({'id':'fixture'}))
  (self.home/'config/library.json').write_text(json.dumps({'id':'fixture','path':str(self.card)}))
  (self.home/'config/skills.json').write_text('[]')
  (self.card/'02_KNOWLEDGE').mkdir();self.doc=self.card/'02_KNOWLEDGE/fixture.txt';self.doc.write_text('orquidea documento inicial\n')
  self.env=dict(os.environ,NEXUS_HOME=str(self.home))
 def tearDown(self):self.tmp.cleanup()
 def run_cli(self,*args,body=None,ok=True):
  r=subprocess.run([sys.executable,str(APP),*args],env=self.env,input=body,text=True,capture_output=True)
  self.assertEqual(r.returncode,0 if ok else 1,r.stdout+r.stderr)
  return json.loads(r.stdout)
 def rec(self,text,verified=True,extra=()):
  args=['record','--kind','semantic','--title','Teste','--source','fixture','--reviewed']
  if verified:args+=['--verified','--evidence','Teste local reproduzível']
  return self.run_cli(*args,*extra,body=text)
 def test_incremental_search_new_process(self):
  self.assertEqual(self.run_cli('sync')['index']['changed'],1)
  self.assertTrue(self.run_cli('search','orquidea'))
  self.assertEqual(self.run_cli('sync')['index']['changed'],0)
  self.doc.write_text('bromelia documento alterado\n')
  self.assertEqual(self.run_cli('sync')['index']['changed'],1)
  self.assertFalse(self.run_cli('search','orquidea'))
  self.assertTrue(self.run_cli('search','bromelia'))
 def test_memory_persistence_dedup_pending_supersedes(self):
  first=self.rec('aprendizado jabuticaba confirmado')
  self.assertTrue(self.rec('aprendizado jabuticaba confirmado')['duplicate'])
  self.rec('hipotese carambola pendente',verified=False)
  self.run_cli('sync');self.assertTrue(self.run_cli('search','jabuticaba'))
  self.assertFalse(self.run_cli('search','carambola'))
  self.assertTrue(self.run_cli('search','carambola','--pending'))
  self.rec('aprendizado pitanga corrigido',extra=['--supersedes',first['id']]);self.run_cli('sync')
  self.assertFalse(self.run_cli('search','jabuticaba'));self.assertTrue(self.run_cli('search','pitanga'))
 def test_offline_queue_and_reconnect(self):
  self.run_cli('sync');moved=self.root/'removed-card';self.card.rename(moved)
  self.assertFalse(self.run_cli('sync')['index']['online'])
  self.assertTrue(self.run_cli('search','orquidea'));self.assertFalse(self.run_cli('context','orquidea')['online'])
  self.rec('goiaba aguardando cartão');self.assertEqual(self.run_cli('status')['pending_writes'],1)
  self.assertFalse(self.card.exists());moved.rename(self.card);self.run_cli('sync')
  self.assertEqual(self.run_cli('status')['pending_writes'],0);self.assertTrue(self.run_cli('search','goiaba'))
 def test_conflict_preserves_outbox(self):
  moved=self.root/'removed-card';self.card.rename(moved);r=self.rec('acerola conflito');moved.rename(self.card)
  dest=self.card/'01_MEMORY/v03/semantic'/ (r['id']+'.json');dest.parent.mkdir(parents=True);dest.write_text('conteudo conflitante')
  self.run_cli('flush',ok=False);self.assertEqual(dest.read_text(),'conteudo conflitante')
  self.assertEqual(self.run_cli('status')['pending_writes'],1)
 def test_invalid_identity_preserves_cache(self):
  self.run_cli('sync');(self.card/'.nexus-v03-library.json').write_text('{"id":"different"}')
  self.assertFalse(self.run_cli('sync')['index']['online']);self.assertTrue(self.run_cli('search','orquidea'))
 def test_secret_rejected(self):
  self.run_cli('record','--kind','semantic','--title','Teste','--source','fixture','--reviewed',body='senha=nao_guardar_isto',ok=False)
  self.assertEqual(self.run_cli('status')['pending_writes'],0)
 def test_full_rescan_same_stat(self):
  self.run_cli('sync');st=self.doc.stat();self.doc.write_text('orquidea documento mudando\n')
  self.assertEqual(self.doc.stat().st_size,st.st_size);os.utime(self.doc,ns=(st.st_atime_ns,st.st_mtime_ns))
  self.assertEqual(self.run_cli('sync','--full')['index']['changed'],1)
 def test_skills_reviewed_restore_and_quarantine(self):
  src=self.card/'03_SKILLS/sample/SKILL.md';src.parent.mkdir(parents=True);text='---\nname: nexus-teste\ndescription: Teste de seleção orquidea\n---\nProcedimento de teste.\n';src.write_text(text)
  dst=self.home/'workspace/.agents/skills/nexus-teste/SKILL.md'
  catalog=[dict(name='nexus-teste',category='Android',triggers='android cartão microsd',description='Testar seleção',path=str(dst),source=str(src),sha256=hashlib.sha256(text.encode()).hexdigest())]
  (self.home/'config/skills.json').write_text(json.dumps(catalog))
  self.assertEqual(self.run_cli('sync')['skills']['restored'],['nexus-teste']);self.assertEqual(dst.read_text(),text)
  self.assertEqual(self.run_cli('skills','android cartão')[0]['name'],'nexus-teste')
  src.write_text('instrução externa alterada')
  self.assertEqual(self.run_cli('sync')['skills']['needs_review'],['nexus-teste']);self.assertEqual(dst.read_text(),text)
 def test_backup_verified_and_tamper_detected(self):
  r=self.run_cli('backup');self.assertTrue(r['verified']);self.assertTrue(self.run_cli('verify-backup',r['permanent'])['verified'])
  p=Path(r['local']);p.write_bytes(b'corrupt archive');self.run_cli('verify-backup',str(p),ok=False)
 def test_working_memory_expiry_and_privacy(self):
  f=self.root/'work.txt';f.write_text('Objetivo temporario revisado')
  self.run_cli('work','--file',str(f),ok=False)
  self.assertFalse(self.run_cli('work'))
  self.run_cli('work','--file',str(f),'--reviewed')
  self.assertIn('temporario',self.run_cli('context','objetivo')['working_memory']['body'])
  state=self.home/'state/work/active.json';r=json.loads(state.read_text());r['expires_at']='2000-01-01T00:00:00+00:00';state.write_text(json.dumps(r))
  self.assertTrue(self.run_cli('work')['expired']);self.run_cli('work','--clear');self.assertFalse(self.run_cli('work'))
 def test_symlink_ignored(self):
  secret=self.root/'outside.txt';secret.write_text('informacao extraterrestre');(self.card/'escape.txt').symlink_to(secret)
  self.run_cli('sync');self.assertFalse(self.run_cli('search','extraterrestre'))
if __name__=='__main__':unittest.main(verbosity=2)
