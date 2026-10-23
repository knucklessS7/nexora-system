"""Install the official RGSX release, preserving unrelated PORTS and saves."""
from pathlib import Path, PurePosixPath
import hashlib, json, os, queue, shutil, stat, subprocess, tempfile, threading, time, zipfile
import xml.etree.ElementTree as ET

PORTS = Path('/userdata/roms/ports')
BASE = Path('/userdata/system/aura-store-native')
VERSION = 'v2.7.0.8'
URL = 'https://github.com/RetroGameSets/RGSX/releases/download/'+VERSION+'/RGSX_full_latest.zip'
# Filled from the verified official release archive when packaging.
SHA256 = '776f082fbe6eb815b4f1b0ce32fcabd0f7e7a049c0219c262867bcb77e655552'

def find_launcher(ports=PORTS):
    primary = ports/'RGSX/RGSX.sh'
    if primary.is_file(): return primary
    return next((p for p in sorted(ports.glob('*.sh')) if 'rgsx' in p.stem.casefold()), None)

class RgsxWorker:
    def __init__(self, q, ports=PORTS, base=BASE):
        self.q=q; self.ports=ports; self.base=base
        self.cancelled=threading.Event(); self.proc=None; self.committing=False
    def emit(self,kind,**data): self.q.put((kind,data))
    def cancel(self):
        if self.committing: return
        self.cancelled.set()
        if self.proc and self.proc.poll() is None: self.proc.terminate()
    def check(self):
        if self.cancelled.is_set(): raise RuntimeError('Instalação cancelada; tente novamente quando quiser.')
    def install_archive(self,archive,stage):
        self.check()
        with zipfile.ZipFile(archive) as z:
            selected=[]
            for info in z.infolist():
                p=PurePosixPath(info.filename)
                if p.is_absolute() or '..' in p.parts or '\\' in info.filename:
                    raise RuntimeError('Caminho inválido no pacote.')
                mode=(info.external_attr>>16)&0xffff
                if stat.S_ISLNK(mode): raise RuntimeError('Link não permitido no pacote.')
                if info.is_dir(): continue
                if info.filename.startswith('ports/RGSX/') or info.filename in ('ports/images/RGSX.png','ports/videos/RGSX.mp4'):
                    selected.append(info)
            required={'ports/RGSX/RGSX.sh','ports/RGSX/__main__.py'}
            if not required.issubset({i.filename for i in selected}): raise RuntimeError('Pacote incompleto.')
            total=sum(i.file_size for i in selected)
            if total>2*1024**3 or shutil.disk_usage(self.ports).free<total+64*1024**2:
                raise RuntimeError('Espaço insuficiente para extrair o RGSX.')
            for i,info in enumerate(selected):
                self.check()
                dest=stage/Path(*PurePosixPath(info.filename).parts[1:]);dest.parent.mkdir(parents=True,exist_ok=True)
                with z.open(info) as src, dest.open('wb') as dst: shutil.copyfileobj(src,dst)
                mode=(info.external_attr>>16)&0o777
                dest.chmod(0o755 if mode&0o111 or dest.suffix=='.sh' else 0o644)
                if i%40==0:self.emit('progress',percent=80+int(15*i/len(selected)),text='Preparando arquivos do RGSX...')
        # Parse before replacing anything. Never discard an existing malformed list.
        gl=self.ports/'gamelist.xml'
        tree=ET.parse(gl) if gl.exists() else ET.ElementTree(ET.Element('gameList'))
        root=tree.getroot()
        if root.tag!='gameList': raise RuntimeError('Lista de jogos inválida; original preservado.')
        for game in list(root.findall('game')):
            if game.findtext('path')=='./RGSX/RGSX.sh':root.remove(game)
        game=ET.SubElement(root,'game')
        for key,value in {'path':'./RGSX/RGSX.sh','name':'RGSX','desc':'RetroGameSets Xtra','image':'./images/RGSX.png','thumbnail':'./images/RGSX.png','video':'./videos/RGSX.mp4'}.items():ET.SubElement(game,key).text=value
        tree.write(stage/'gamelist.xml',encoding='utf-8',xml_declaration=True)
        self.check();self.committing=True
        self.emit('progress',percent=97,text='Concluindo instalação; aguarde...')
        backup=self.base/('rgsx-backup-'+str(time.time_ns()));backup.mkdir(parents=True)
        targets=['RGSX','images/RGSX.png','videos/RGSX.mp4','gamelist.xml'];changed=[]
        try:
            for rel in targets:
                src=stage/rel;dst=self.ports/rel;saved=backup/rel
                if not src.exists():continue
                dst.parent.mkdir(parents=True,exist_ok=True)
                if dst.exists():
                    saved.parent.mkdir(parents=True,exist_ok=True);os.replace(dst,saved)
                changed.append((dst,saved))
                os.replace(src,dst)
        except Exception:
            for dst,saved in reversed(changed):
                if dst.is_dir(): shutil.rmtree(dst)
                elif dst.exists(): dst.unlink()
                if saved.exists():os.replace(saved,dst)
            raise
        finally:self.committing=False
        (backup/'source.json').write_text(json.dumps({'url':URL,'version':VERSION,'sha256':SHA256}),encoding='utf-8')
    def run(self):
        self.base.mkdir(parents=True,exist_ok=True);self.ports.mkdir(parents=True,exist_ok=True)
        try:
            import fcntl
            with (self.base/'rgsx-install.lock').open('w') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                if find_launcher(self.ports):
                    self.emit('done',percent=100,text='RGSX já instalado.');return
                if shutil.disk_usage(self.ports).free<700*1024**2:raise RuntimeError('Reserve pelo menos 700 MB livres para instalar.')
                with tempfile.TemporaryDirectory(prefix='.aura-rgsx-',dir=self.ports) as tmp:
                    tmp=Path(tmp);archive=tmp/'release.zip';stage=tmp/'stage';stage.mkdir()
                    self.emit('progress',percent=1,text='Baixando RGSX oficial (133 MB)...')
                    with (self.base/'rgsx-install.log').open('a') as log:
                        self.proc=subprocess.Popen(['curl','--fail','--location','--proto','=https','--proto-redir','=https','--connect-timeout','20','--max-time','900','--retry','2','--silent','--show-error','--output',str(archive),URL],stdout=log,stderr=log)
                        while self.proc.poll() is None:
                            self.check()
                            size=archive.stat().st_size if archive.exists() else 0
                            self.emit('progress',percent=min(75,1+int(size/139504151*74)),text=f'Baixando RGSX: {size//1048576} MB')
                            self.cancelled.wait(.5)
                        self.check()
                        if self.proc.returncode:raise RuntimeError('Download falhou. Verifique internet/data e tente novamente.')
                    self.emit('progress',percent=78,text='Verificando integridade do pacote...')
                    digest=hashlib.sha256()
                    with archive.open('rb') as f:
                        for chunk in iter(lambda:f.read(1048576),b''):self.check();digest.update(chunk)
                    if digest.hexdigest()!=SHA256:raise RuntimeError('Pacote diferente do validado; instalação cancelada.')
                    self.install_archive(archive,stage)
                    self.emit('done',percent=100,text='RGSX instalado. Selecione Abrir.')
        except Exception as e:
            if self.proc and self.proc.poll() is None:self.proc.terminate();self.proc.wait(timeout=10)
            self.emit('error',text=str(e))
