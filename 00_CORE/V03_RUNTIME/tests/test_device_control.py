import hashlib
import contextlib
import io
import hmac
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import device_control as control

CONFIG={'service':'nexus-device-control','protocol':1,'port':18764,'token':'a'*64,'session':'b'*32}


class ControlTests(unittest.TestCase):
    def test_control_has_direct_menu_commands(self):
        from command_input import Composer
        menu=Composer();menu.insert('/control ')
        self.assertIn('/control pair',[c.name for c in menu.matches()])
        self.assertIn('/control status',[c.name for c in menu.matches()])
    def test_pair_command_dispatches_without_pasting_secret(self):
        from slash_commands import handle
        with patch.object(control,'run',return_value={'paired':True}) as run,contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(handle(None,'/control','pair',lambda *a:None))
        self.assertEqual(run.call_args.args[1],['pair'])
    def test_tap_prompts_and_cancel_executes_nothing(self):
        from slash_commands import handle
        with patch.object(control,'run',return_value={'ok':True}) as run,patch('builtins.input',return_value='100 200'),contextlib.redirect_stdout(io.StringIO()):
            handle(None,'/control','tap',lambda *a:None)
        self.assertEqual(run.call_args.args[1],['tap','100','200'])
        with patch.object(control,'run',side_effect=AssertionError('Cancelado')),patch('builtins.input',return_value=''):
            self.assertTrue(handle(None,'/control','tap',lambda *a:None))
    def test_pairing_rejects_wrong_port_protocol_and_bad_secret(self):
        for change in [{'port':443},{'protocol':2},{'service':'other'},{'token':'x'},{'session':'http://example.com'}]:
            with self.assertRaises(ValueError):control.pairing(json.dumps(dict(CONFIG,**change)))
    def test_private_config_and_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);control.save_pair(base,CONFIG);control.save_pair(base,dict(CONFIG,session='c'*32))
            self.assertEqual((base/'config/device-control.json').stat().st_mode&0o777,0o600)
            self.assertEqual(len(list((base/'state/.private').glob('pair-*.json'))),1)
            self.assertFalse(control.run(base,['forget'])['paired']);self.assertFalse((base/'config/device-control.json').exists())
    def test_actions_validate_before_sending(self):
        for args in [['wipe'],['shell','id'],['tap','nan','1'],['tap','-1','0'],['tap','2'],['home','extra'],['swipe','1','1','2','2','9000']]:
            with self.assertRaises(ValueError):control.parse_action(args)
        self.assertEqual(control.parse_action(['swipe','1','2','3','4','200'])['duration_ms'],200)
    def test_hmac_authentication_without_sending_the_secret(self):
        capture={}
        class Connection:
            def __init__(self,host,port,timeout):capture.update(host=host,port=port)
            def request(self,method,path,body,headers):capture.update(body=body,headers=headers)
            def getresponse(self):return self
            status=200
            def read(self,size):return b'{"ok":true,"accepted":true}'
            def getheader(self,name,default):return hmac.new(CONFIG['token'].encode(),b'response\n'+capture['headers']['X-Nexus-Nonce'].encode()+b'\n'+self.read(8193),hashlib.sha256).hexdigest()
            def close(self):pass
        with patch.object(control.http.client,'HTTPConnection',Connection):
            self.assertTrue(control.request(CONFIG,{'action':'status'})['ok'])
        self.assertEqual((capture['host'],capture['port']),('127.0.0.1',18764))
        self.assertNotIn(CONFIG['token'],json.dumps(capture['headers']))
        headers=capture['headers'];message=b'request\n'+CONFIG['session'].encode()+b'\n'+headers['X-Nexus-Nonce'].encode()+b'\n'+headers['X-Nexus-Time'].encode()+b'\n'+capture['body']
        self.assertEqual(headers['X-Nexus-Signature'],hmac.new(CONFIG['token'].encode(),message,hashlib.sha256).hexdigest())
    def test_spoofed_server_is_not_reported_as_success(self):
        class Connection:
            def __init__(self,*a,**kw):pass
            def request(self,*a):pass
            def getresponse(self):return self
            def read(self,size):return b'{"ok":true}'
            def getheader(self,*a):return '0'*64
            def close(self):pass
        with patch.object(control.http.client,'HTTPConnection',Connection):
            with self.assertRaisesRegex(ValueError,'sem autenticação'):control.request(CONFIG,{'action':'status'})
    def test_no_pairing_does_not_control_the_phone(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(control,'request',side_effect=AssertionError('No request without pairing')):
            self.assertFalse(control.run(folder,['home'])['paired'])
    def test_java_python_hmac_interoperability(self):
        source=Path(__file__).resolve().parents[1]/'plugins/device-control/src/org/nexusmind/control/Auth.java'
        if not source.is_file():self.skipTest('Android plugin source not in this fixture')
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);test=base/'Check.java';test.write_text('import org.nexusmind.control.Auth; class Check { public static void main(String[] a)throws Exception {System.out.print(Auth.sign("test-key", "request\\nsession\\nnonce\\n123\\n{}"));}}')
            subprocess.run(['javac','-d',str(base),str(source),str(test)],check=True,capture_output=True,timeout=20)
            result=subprocess.check_output(['java','-cp',str(base),'Check'],text=True,timeout=10)
            self.assertEqual(result,hmac.new(b'test-key',b'request\nsession\nnonce\n123\n{}',hashlib.sha256).hexdigest())
    def test_manifest_requests_only_needed_policies(self):
        base=Path(__file__).resolve().parents[1]/'plugins/device-control'
        ns='{http://schemas.android.com/apk/res/android}'
        root=ET.parse(base/'AndroidManifest.xml').getroot()
        permissions={p.attrib[ns+'name'] for p in root.findall('uses-permission')}
        self.assertEqual(permissions,{'android.permission.INTERNET','android.permission.FOREGROUND_SERVICE','android.permission.FOREGROUND_SERVICE_SPECIAL_USE','android.permission.POST_NOTIFICATIONS'})
        policies=ET.parse(base/'res/xml/admin.xml').getroot().find('uses-policies')
        self.assertEqual([p.tag for p in policies],['force-lock'])
        config=ET.parse(base/'res/xml/accessibility.xml').getroot()
        self.assertEqual(config.attrib[ns+'canRetrieveWindowContent'],'false')
        self.assertEqual(root.find("application/service[@android:name='.BridgeService']",{'android':ns[1:-1]}).attrib[ns+'exported'],'false')


if __name__=='__main__':unittest.main(verbosity=2)
