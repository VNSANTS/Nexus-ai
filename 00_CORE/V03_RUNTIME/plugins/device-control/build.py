"""Build locally with verified Android SDK and installed Termux tools; never installs the APK."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time
import zipfile

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parents[1]

def run(argv):
    env=dict(os.environ,JAVA_TOOL_OPTIONS='-Xmx256m')
    subprocess.run([str(a) for a in argv],check=True,env=env)

def main():
    sdk=BASE/'cache/android-sdk-34/android.jar'
    if not sdk.is_file():raise ValueError('Verified Android SDK 34 android.jar missing')
    for tool in ['aapt2','javac','d8','zipalign','apksigner','keytool']:
        if not shutil.which(tool):raise ValueError('Missing installed tool: '+tool)
    work=ROOT/'build'/str(time.time_ns());work.mkdir(parents=True)
    for name in ['generated','classes','dex']:(work/name).mkdir()
    run(['aapt2','compile','--dir',ROOT/'res','-o',work/'resources.zip'])
    run(['aapt2','link','-I',sdk,'--manifest',ROOT/'AndroidManifest.xml','--java',work/'generated','-o',work/'unsigned.apk',work/'resources.zip'])
    sources=list((ROOT/'src').rglob('*.java'))+list((work/'generated').rglob('*.java'))
    run(['javac','--release','8','-encoding','UTF-8','-classpath',sdk,'-d',work/'classes',*sources])
    classes=list((work/'classes').rglob('*.class'))
    run(['d8','--min-api','26','--lib',sdk,'--output',work/'dex',*classes])
    with zipfile.ZipFile(work/'unsigned.apk','a') as apk:
        for dex in (work/'dex').glob('*.dex'):apk.write(dex,dex.name)
    run(['zipalign','-f','4',work/'unsigned.apk',work/'aligned.apk'])
    private=ROOT/'.keys';private.mkdir(mode=0o700,exist_ok=True)
    password=private/'store-pass';keystore=private/'release.p12'
    if not password.exists():
        with password.open('x') as f:f.write(secrets.token_hex(32)+'\n')
        password.chmod(0o600)
    if not keystore.exists():
        run(['keytool','-genkeypair','-keystore',keystore,'-storetype','PKCS12','-alias','nexus-local',
             '-storepass:file',password,'-keypass:file',password,'-keyalg','RSA','-keysize','2048','-validity','3650',
             '-dname','CN=Nexus Local Device Control, O=Nexus Mind'])
        keystore.chmod(0o600)
    output=ROOT/'dist/nexus-device-control-0.1.0.apk';output.parent.mkdir(exist_ok=True)
    if output.exists():
        backup=ROOT/'dist/backups';backup.mkdir(exist_ok=True);shutil.copy2(output,backup/(str(time.time_ns())+'.apk'))
    run(['apksigner','sign','--ks',keystore,'--ks-key-alias','nexus-local','--ks-pass','file:'+str(password),
         '--out',work/'signed.apk',work/'aligned.apk'])
    run(['apksigner','verify','--verbose',work/'signed.apk'])
    shutil.copy2(work/'signed.apk',output)
    report={'apk':str(output),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'size':output.stat().st_size,
            'package':'org.nexusmind.control','version':'0.1.0','installed':False,'runtime_permissions_tested':False}
    (ROOT/'dist/build-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
