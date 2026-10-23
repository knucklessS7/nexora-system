from pathlib import Path
import hashlib,json,os,shutil,time,subprocess
P=Path(__file__).parent;B=Path('/userdata/system/aura-neon-runtime')
def apply():
 if Path('/boot/AURA-NEON-DESATIVAR').exists() or (B/'recovery-disabled').exists():return
 if not (B/'bin/emulationstation').exists():return
 manifest=json.loads((P/'manifest.json').read_text())
 for name,h in manifest.items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==h,name
 revision=hashlib.sha256((P/'manifest.json').read_bytes()).hexdigest();marker=B/'home-row.done'
 if marker.exists() and marker.read_text()==revision:return
 expected=(B/'binary.sha256').read_text().split()[0];binary=B/'bin/emulationstation'
 assert hashlib.sha256(binary.read_bytes()).hexdigest()==expected,'Binario atual com integridade invalida'
 backup=B/('backup-home-row-'+str(time.time_ns()));backup.mkdir()
 for f in (binary,B/'binary.sha256',B/'dispatch/emulationstation'):
  shutil.copy2(f,backup/('dispatcher' if f.parent.name=='dispatch' else f.name))
 candidate=binary.with_suffix('.home-new');shutil.copy2(P/'emulationstation',candidate);candidate.chmod(0o755)
 subprocess.run([str(candidate),'--help'],check=True,stdout=subprocess.DEVNULL,env={**os.environ,'LD_BIND_NOW':'1'})
 os.replace(candidate,binary)
 (B/'binary.sha256').write_text(manifest['emulationstation']+'  bin/emulationstation\n')
 shutil.copy2(P/'dispatcher',B/'dispatch/emulationstation');(B/'dispatch/emulationstation').chmod(0o755)
 (B/'enabled').touch();marker.write_text(revision)
 print('Home nativo e preservacao da interface instalados para proximo inicio.')
if __name__=='__main__':apply()
