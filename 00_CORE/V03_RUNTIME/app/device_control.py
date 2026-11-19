"""Nexus companion client: loopback only, authenticated messages, no credential output."""
import hashlib
import hmac
import http.client
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
import time

PORT=18764
ACTIONS={'status','home','back','recents','notifications','quick_settings','lock','tap','swipe'}


def pairing(raw):
    if not isinstance(raw,str) or len(raw)>4096:raise ValueError('Pareamento inválido')
    try:data=json.loads(raw)
    except ValueError:raise ValueError('No app Nexus Controle, inicie a ponte e copie o pareamento. Não cole o segredo no chat.') from None
    if not isinstance(data,dict) or data.get('service')!='nexus-device-control' or data.get('protocol')!=1 or data.get('port')!=PORT:
        raise ValueError('Formato de pareamento incompatível')
    for key,size in [('token',64),('session',32)]:
        if not isinstance(data.get(key),str) or not re.fullmatch('[a-f0-9]{'+str(size)+'}',data[key]):raise ValueError('Pareamento incompleto')
    return {key:data[key] for key in ['service','protocol','port','token','session']}


def request(config,command):
    data=pairing(json.dumps(config));body=json.dumps(command,separators=(',',':'),ensure_ascii=False).encode()
    nonce=secrets.token_hex(16);stamp=str(int(time.time()*1000))
    message=b'request\n'+data['session'].encode()+b'\n'+nonce.encode()+b'\n'+stamp.encode()+b'\n'+body
    signature=hmac.new(data['token'].encode(),message,hashlib.sha256).hexdigest()
    connection=http.client.HTTPConnection('127.0.0.1',PORT,timeout=6)
    try:
        connection.request('POST','/v1/action',body,{'Content-Type':'application/json','X-Nexus-Session':data['session'],
            'X-Nexus-Time':stamp,'X-Nexus-Nonce':nonce,'X-Nexus-Signature':signature})
        response=connection.getresponse();raw=response.read(8193)
        if len(raw)>8192:raise ValueError('Resposta local excede o limite')
        expected=hmac.new(data['token'].encode(),b'response\n'+nonce.encode()+b'\n'+raw,hashlib.sha256).hexdigest()
        if not hmac.compare_digest(response.getheader('X-Nexus-Signature',''),expected):raise ValueError('Resposta sem autenticação válida. Nenhuma confirmação de execução.')
        value=json.loads(raw)
        if response.status!=200 or not isinstance(value,dict) or not value.get('ok'):
            raise ValueError('Controle Android: '+str(value.get('error','ação recusada'))[:200] if isinstance(value,dict) else 'Resposta inválida')
        return value
    except (OSError,http.client.HTTPException):
        raise ValueError('Ponte local indisponível ou sem confirmação. Abra Nexus Controle, inicie a ponte e faça /control pair. Não repita gestos sem conferir a tela.') from None
    finally:connection.close()


def save_pair(base,config):
    path=Path(base)/'config/device-control.json';path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        folder=Path(base)/'state/.private';folder.mkdir(mode=0o700,parents=True,exist_ok=True)
        backup=folder/('pair-'+secrets.token_hex(8)+'.json')
        with backup.open('xb') as f:f.write(path.read_bytes())
        backup.chmod(0o600)
    fd,temp=tempfile.mkstemp(prefix='.pair-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:json.dump(config,f);f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(temp,path);path.chmod(0o600)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def parse_action(args):
    action=args[0] if args else 'status'
    if action not in ACTIONS:raise ValueError('Ação não suportada; use nexus control help')
    expected=3 if action=='tap' else 5 if action=='swipe' else 1
    if len(args or ['status']) not in ({5,6} if action=='swipe' else {expected}):raise ValueError('Use tap X Y ou swipe X Y X2 Y2 [MS]')
    result={'action':action}
    if action in {'tap','swipe'}:
        for key,value in zip(['x','y','x2','y2'],args[1:5]):
            try:n=float(value)
            except ValueError:raise ValueError('Coordenadas precisam ser numéricas') from None
            if not math.isfinite(n) or n<0 or n>16384:raise ValueError('Coordenada fora do intervalo')
            result[key]=n
        if action=='swipe':
            try:duration=int(args[5]) if len(args)==6 else 400
            except ValueError:raise ValueError('Duração inválida') from None
            if not 50<=duration<=2000:raise ValueError('Duração deve ser 50 a 2000 ms')
            result['duration_ms']=duration
    return result


def run(base,args):
    base=Path(base);name=args[0] if args else 'status'
    if name=='help':return {'commands':['/control open','/control pair','/control status','/control home','/control back','/control recents',
            '/control notifications','/control quick_settings','/control tap X Y','/control swipe X Y X2 Y2 [MS]','/control lock','/control forget'],
            'setup':'Instale o APK, ative as permissões desejadas no Android, inicie a ponte e copie o pareamento. Nenhuma permissão é concedida pelo terminal.'}
    if name=='open':
        executable=shutil.which('am')
        if not executable:raise ValueError('Abra o app Nexus Controle pela tela inicial')
        p=subprocess.run([executable,'start','-n','org.nexusmind.control/.MainActivity'],capture_output=True,text=True,timeout=10)
        if p.returncode or any(word in (p.stderr+p.stdout).lower() for word in ['error','exception','not found']):raise ValueError('App não abriu. Instale o APK e abra Nexus Controle pela tela inicial.')
        return {'opened':True,'permissions':'Ative somente as funções que desejar, nas telas Android.'}
    if name=='apk':return {'apk':str(base/'plugins/device-control/dist/nexus-device-control-0.1.0.apk')}
    path=base/'config/device-control.json'
    if name=='forget':
        # Forget is the user's explicit request to remove this operational credential.
        path.unlink(missing_ok=True)
        for backup in (base/'state/.private').glob('pair-*.json'):backup.unlink()
        return {'paired':False,'next':'No app, use Revogar pareamentos para invalidar o segredo também no Android.'}
    if name=='pair':
        tool=shutil.which('termux-clipboard-get')
        if not tool:raise ValueError('Termux:API/termux-clipboard-get necessário para parear sem colar segredos no chat')
        p=subprocess.run([tool],capture_output=True,text=True,timeout=10)
        if p.returncode:raise ValueError('Não foi possível ler o pareamento do clipboard')
        config=pairing(p.stdout.strip());status=request(config,{'action':'status'});save_pair(base,config)
        # Only clear clipboard if its content is still exactly the pairing just consumed.
        setter=shutil.which('termux-clipboard-set')
        if setter:
            try:
                current=subprocess.run([tool],capture_output=True,text=True,timeout=5)
                if current.returncode==0 and current.stdout==p.stdout:subprocess.run([setter],input='',capture_output=True,text=True,timeout=5)
            except (OSError,subprocess.SubprocessError):pass
        return {'paired':True,'online':True,'device':status,'secret_saved':'somente config privada interna; nunca exibido ou enviado à IA'}
    command=parse_action(args)
    if not path.is_file():return {'paired':False,'online':False,'next':'Abra Nexus Controle, inicie a ponte, copie o pareamento e use /control pair.'}
    config=pairing(path.read_text())
    return request(config,command)
