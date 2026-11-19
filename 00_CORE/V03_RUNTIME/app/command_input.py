"""Small ANSI slash-command picker for Termux; standard library only, no disk history."""
import codecs
import collections
from dataclasses import dataclass
import os
import select
import shutil
import sys
import termios
import tty
import unicodedata
from slash_commands import ALIASES, ENTRIES
import json
from pathlib import Path

@dataclass(frozen=True)
class Command:
    name: str
    description: str
    argument: str = ''
    @property
    def usage(self):return self.name+(' '+self.argument if self.argument else '')

COMMANDS = (
    Command('/ajuda','Ver todos os comandos'),
    Command('/voz','Ditar pelo microfone do Android'),
    Command('/foto','Selecionar uma imagem no Android'),
    Command('/print','Anexar o print mais recente'),
    Command('/anexar','Anexar uma imagem pelo caminho','CAMINHO'),
    Command('/colar','Anexar pelo caminho copiado'),
    Command('/anexos','Ver os anexos da próxima mensagem'),
    Command('/sem-anexos','Descartar anexos temporários'),
    Command('/enviar','Enviar o ditado revisado'),
    Command('/ditado','Editar o texto reconhecido'),
    Command('/cancelar','Descartar o ditado'),
    Command('/buscar','Buscar na memória e documentos da biblioteca','TERMOS'),
    Command('/pesquisar','Pesquisar na internet com o Codex','TERMOS'),
    Command('/skills','Listar ou encontrar habilidades'),
    Command('/lembrar','Guardar uma síntese pendente','TEXTO'),
    Command('/modo rapido','Respostas com raciocínio leve'),
    Command('/modo profundo','Análises com mais raciocínio'),
    Command('/tempo','Ver tempo da última resposta'),
    Command('/roteador','Ver modelo escolhido e motivo'),
    Command('/status','Ver estado da memória e do cartão'),
    Command('/sync','Atualizar o índice e a fila'),
    Command('/backup','Criar e verificar um backup'),
    Command('/novo','Nova conversa; preservar memórias'),
    Command('/user','Definir o nome exibido no prompt','NOME'),
    Command('/reconectar','Reiniciar a conexão com Codex'),
    Command('/limpar','Limpar a tela'),
    Command('/sair','Encerrar o Nexus'),
    Command('/root','Consultar a declaração local de root'),
    Command('/root true','Declarar root existente; não autoriza uso'),
    Command('/root false','Declarar dispositivo sem root'),
    Command('/root unable','Root indisponível ou não confirmado'),
    Command('/device','Ver o ambiente deste dispositivo'),
    Command('/codex','Abrir a interface nativa; todos os menus /'),
    Command('/claude','Abrir Claude Code, se instalado'),
    Command('/comandos','Ajuda dos comandos nativos e !'),
)
COMMANDS += tuple(Command(name, description) for name, description in ENTRIES)
COMMANDS += tuple(Command(name, 'Atalho de '+target) for name,target in ALIASES.items())
# Reference entries are visibly unavailable, never silently sent to an AI or another application.
_reference=json.loads(Path(__file__).with_name('slash_reference.json').read_text())
UNAVAILABLE=frozenset(set(_reference['codex']+_reference['claude'])-{item.name for item in COMMANDS})
COMMANDS += tuple(Command(name,'Indisponível nesta interface') for name in sorted(UNAVAILABLE))


def width(text):
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in {'W','F'} else 1 for c in text)


def truncate(text,columns):
    result=[];used=0
    for c in text:
        size=width(c)
        if used+size>max(0,columns):break
        result.append(c);used+=size
    return ''.join(result)


def printable(text):
    return ''.join(c for c in text if ord(c)>=32 and not 127<=ord(c)<=159)


class Composer:
    def __init__(self):
        self.text='';self.cursor=0;self.selected=0;self.hidden=False
    def matches(self):
        if self.hidden or not self.text.startswith('/'):return []
        return [item for item in COMMANDS if item.name.startswith(self.text)]
    def insert(self,text):
        # Pasted newlines are text, never implicit Enter/send operations.
        text=printable(text.replace('\r',' ').replace('\n',' '))
        text=text[:max(0,32000-len(self.text))]
        self.text=self.text[:self.cursor]+text+self.text[self.cursor:];self.cursor+=len(text)
        self.selected=0;self.hidden=False
    def replace(self,text):
        self.text=printable(text)[:32000];self.cursor=len(self.text);self.selected=0;self.hidden=True
    def choose(self):
        found=self.matches()
        if not found:return None
        item=found[self.selected%len(found)]
        self.text=item.name+(' ' if item.argument else '');self.cursor=len(self.text);self.hidden=True
        return item
    def key(self,key):
        found=self.matches()
        if key in {'UP','DOWN'} and found:
            self.selected=(self.selected+(-1 if key=='UP' else 1))%len(found)
        elif key=='TAB':self.choose()
        elif key=='ENTER':
            item=self.choose()
            if item and item.argument:return None
            return self.text
        elif key=='ESC':self.hidden=True
        elif key=='BACKSPACE':
            if self.cursor:
                self.text=self.text[:self.cursor-1]+self.text[self.cursor:];self.cursor-=1;self.selected=0;self.hidden=False
        elif key=='DELETE':
            self.text=self.text[:self.cursor]+self.text[self.cursor+1:];self.selected=0;self.hidden=False
        elif key=='LEFT':self.cursor=max(0,self.cursor-1)
        elif key=='RIGHT':self.cursor=min(len(self.text),self.cursor+1)
        elif key=='HOME':self.cursor=0
        elif key=='END':self.cursor=len(self.text)
        elif key=='CLEAR':self.text='';self.cursor=0;self.hidden=False;self.selected=0
        elif key=='KILL_END':self.text=self.text[:self.cursor];self.selected=0;self.hidden=False
        return None


class CommandInput:
    def __init__(self):
        self.history=[];self.queue=collections.deque();self.decoder=codecs.getincrementaldecoder('utf-8')('replace')
        self.fd=None;self.row=0;self.size=None
    def char(self,timeout=None):
        if self.queue:return self.queue.popleft()
        if not select.select([self.fd],[],[],timeout)[0]:return ''
        raw=os.read(self.fd,4096)
        if not raw:raise EOFError
        self.queue.extend(self.decoder.decode(raw))
        return self.queue.popleft() if self.queue else self.char(timeout)
    def key(self):
        c=self.char(.2)
        if not c:return ('IDLE',None)
        basic={'\r':'ENTER','\n':'ENTER','\t':'TAB','\x7f':'BACKSPACE','\x08':'BACKSPACE',
               '\x01':'HOME','\x05':'END','\x15':'CLEAR','\x0b':'KILL_END','\x0e':'DOWN','\x10':'UP','\x0c':'REDRAW'}
        if c=='\x03':raise KeyboardInterrupt
        if c=='\x04':return ('EOF',None)
        if c=='\x1b':
            seq=self.char(.04)
            if not seq:return ('ESC',None)
            if seq not in {'[','O'}:
                self.queue.appendleft(seq);return ('ESC',None)
            while len(seq)<24:
                nextc=self.char(.04)
                if not nextc:break
                seq+=nextc
                if nextc.isalpha() or nextc=='~':break
            if seq=='[200~':
                pasted=''
                while not pasted.endswith('\x1b[201~'):
                    c=self.char(1)
                    if c:pasted+=c
                    if len(pasted)>65536:raise ValueError('Colagem muito grande; limite de 32 mil caracteres')
                return ('TEXT',pasted[:-6])
            key={'[A':'UP','[B':'DOWN','[C':'RIGHT','[D':'LEFT','[H':'HOME','[F':'END',
                 'OH':'HOME','OF':'END','OA':'UP','OB':'DOWN','OC':'RIGHT','OD':'LEFT',
                 '[1~':'HOME','[7~':'HOME','[4~':'END','[8~':'END','[3~':'DELETE','[Z':'UP'}.get(seq,'IGNORE')
            return (key,None)
        if c in basic:return (basic[c],None)
        return ('TEXT',c) if ord(c)>=32 else ('IGNORE',None)
    def render(self,model,label):
        size=shutil.get_terminal_size((80,24));self.size=size
        columns=max(8,size.columns-1);found=model.matches();lines=[]
        if found:
            count=max(1,min(6,size.lines-4));index=model.selected%len(found);start=max(0,min(index-count//2,len(found)-count))
            for i in range(start,min(start+count,len(found))):
                item=found[i];name=item.usage;pad=max(1,min(20,columns//2)-width(name))
                text=truncate(('› ' if i==index else '  ')+name+' '*pad+item.description,columns)
                if i==index and not os.environ.get('NO_COLOR'):text='\033[30;46m'+text+'\033[0m'
                lines.append(text)
            lines.append(truncate('↑↓ escolhem · Tab completa · Enter seleciona · Esc fecha',columns))
        prefix=truncate(label,max(1,columns//3));room=max(1,columns-width(prefix)-1)
        left=model.text[:model.cursor];right=model.text[model.cursor:]
        # Horizontal window keeps the cursor visible without wrapping over the popup.
        while width(left)>room-1:left=left[1:]
        visible=truncate(left+right,room)
        lines.append(prefix+visible)
        sys.stdout.write('\r'+('\033['+str(self.row)+'A' if self.row else '')+'\033[J')
        sys.stdout.write('\n'.join(lines));self.row=len(lines)-1
        sys.stdout.write('\r\033['+str(width(prefix)+width(left)+1)+'G');sys.stdout.flush()
    def finish(self,label,text):
        sys.stdout.write('\r'+('\033['+str(self.row)+'A' if self.row else '')+'\033[J')
        # The submitted text may wrap naturally after the editable frame is removed.
        sys.stdout.write(label+printable(text)+'\n');sys.stdout.flush();self.row=0
    def read(self,label):
        if not sys.stdin.isatty() or not sys.stdout.isatty() or os.environ.get('TERM')=='dumb':return input(label)
        self.fd=sys.stdin.fileno();saved=termios.tcgetattr(self.fd);model=Composer();self.row=0;position=len(self.history);draft=''
        try:
            tty.setraw(self.fd)
            current=termios.tcgetattr(self.fd);current[1]=saved[1];termios.tcsetattr(self.fd,termios.TCSANOW,current)
            sys.stdout.write('\033[?2004h');self.render(model,label)
            while True:
                key,text=self.key()
                if key=='IDLE':
                    if shutil.get_terminal_size((80,24))!=self.size:self.render(model,label)
                    continue
                if key=='EOF':
                    if not model.text:raise EOFError
                    model.key('DELETE')
                elif key=='TEXT':model.insert(text)
                elif key in {'UP','DOWN'} and not model.matches() and self.history:
                    if position==len(self.history):draft=model.text
                    position=max(0,min(len(self.history),position+(-1 if key=='UP' else 1)))
                    model.replace(self.history[position] if position<len(self.history) else draft)
                else:
                    result=model.key(key)
                    if result is not None:
                        self.finish(label,result)
                        # Keep only slash commands in RAM; never record conversational messages.
                        if result.startswith('/') and (not self.history or self.history[-1]!=result):self.history=(self.history+[result])[-40:]
                        return result
                self.render(model,label)
        except (KeyboardInterrupt,EOFError):
            self.finish(label,'');raise
        finally:
            sys.stdout.write('\033[?2004l');sys.stdout.flush();termios.tcsetattr(self.fd,termios.TCSANOW,saved)
