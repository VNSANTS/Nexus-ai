import errno,fcntl,os,pty,select,signal,struct,subprocess,sys,termios,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from command_input import COMMANDS,Composer,width,truncate

class ComposerTests(unittest.TestCase):
 def test_slash_shows_all_and_filters(self):
  m=Composer();m.insert('/');self.assertEqual(m.matches(),list(COMMANDS))
  m.insert('vo');self.assertEqual([x.name for x in m.matches()],['/voz','/voice'])
 def test_arrow_selection_and_tab(self):
  m=Composer();m.insert('/');m.key('DOWN');m.key('TAB');self.assertEqual(m.text,'/voz');self.assertEqual(m.key('ENTER'),'/voz')
 def test_enter_selects_filtered_command(self):
  m=Composer();m.insert('/sta');self.assertEqual(m.key('ENTER'),'/status')
 def test_required_argument_completes_before_submit(self):
  m=Composer();m.insert('/bus');self.assertIsNone(m.key('ENTER'));self.assertEqual(m.text,'/buscar ')
  m.insert('memória Android');self.assertEqual(m.key('ENTER'),'/buscar memória Android')
 def test_mode_subcommands(self):
  m=Composer();m.insert('/modo ');self.assertEqual(len(m.matches()),2)
  m.key('DOWN');self.assertEqual(m.key('ENTER'),'/modo profundo')
 def test_escape_closes_without_sending(self):
  m=Composer();m.insert('/vo');m.key('ESC');self.assertFalse(m.matches());self.assertEqual(m.text,'/vo')
 def test_text_and_unicode_editing(self):
  m=Composer();m.insert('você me ouve?');m.key('HOME');m.insert('Olá, ');m.key('END');m.key('BACKSPACE');self.assertEqual(m.key('ENTER'),'Olá, você me ouve')
 def test_paste_cannot_submit_or_inject_terminal_controls(self):
  m=Composer();m.insert('texto\n/sair\x1b[2J');self.assertEqual(m.text,'texto /sair[2J')
 def test_display_columns(self):
  self.assertEqual(width('ação'),4);self.assertEqual(width('界'),2);self.assertEqual(truncate('a界b',3),'a界')
 def test_limit_input_size(self):
  m=Composer();m.insert('x'*50000);self.assertEqual(len(m.text),32000)

class PtyTests(unittest.TestCase):
 def run_editor(self,keys,resize=False):
  master,slave=pty.openpty();before=termios.tcgetattr(slave)
  fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',24,45,0,0))
  app=str(Path(__file__).resolve().parents[1]/'app')
  program='import sys;sys.path.insert(0,'+repr(app)+');from command_input import CommandInput;v=CommandInput().read("Você › ");print("RESULT="+repr(v))'
  proc=subprocess.Popen([sys.executable,'-c',program],stdin=slave,stdout=slave,stderr=slave,env=dict(os.environ,TERM='xterm-256color'))
  data=b''
  def read_until(needle,timeout=5):
   nonlocal data
   end=time.monotonic()+timeout
   while needle not in data and time.monotonic()<end:
    if select.select([master],[],[],.1)[0]:
     try:
      chunk=os.read(master,65536)
      if not chunk:break
      data+=chunk
     except OSError:break
   self.assertIn(needle,data)
  try:
   read_until('Você'.encode());os.write(master,b'/');read_until(b'/voz')
   if resize:
    fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',16,32,0,0));time.sleep(.25)
   os.write(master,keys);read_until(b'RESULT=');proc.wait(timeout=3)
   while select.select([master],[],[],.05)[0]:
    try:data+=os.read(master,65536)
    except OSError:break
   self.assertEqual(proc.returncode,0,data.decode(errors='replace'));self.assertEqual(termios.tcgetattr(slave),before)
   return data.decode(errors='replace')
  finally:
   if proc.poll() is None:proc.kill();proc.wait()
   os.close(master);os.close(slave)
 def test_real_terminal_menu_filter_and_submit(self):
  text=self.run_editor(b'vo\r');self.assertIn("RESULT='/voz'",text)
 def test_real_terminal_arrow_and_tab(self):
  text=self.run_editor(b'\x1b[B\t\r');self.assertIn("RESULT='/voz'",text)
 def test_real_terminal_paste_unicode_and_resize(self):
  text=self.run_editor(b'buscar\t\x1b[200~'+ 'ação no cartão'.encode()+b'\x1b[201~\r',resize=True)
  self.assertIn("RESULT='/buscar ação no cartão'",text)
if __name__=='__main__':unittest.main(verbosity=2)
