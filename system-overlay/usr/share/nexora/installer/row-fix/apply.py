from pathlib import Path
import hashlib,json,os,shutil,time
P=Path(__file__).parent
B=Path('/userdata/system/aura-neon-runtime')
def apply():
 if Path('/boot/AURA-NEON-DESATIVAR').exists() or (B/'recovery-disabled').exists():
  print('Recuperação manual ativa: mantida.');return
 if not (B/'dispatch/emulationstation').exists():return
 manifest=json.loads((P/'manifest.json').read_text())
 for rel,h in manifest.items():assert hashlib.sha256((P/rel).read_bytes()).hexdigest()==h,rel
 # Reactivation is allowed only when the installed binary still matches its manifest.
 expected=(B/'binary.sha256').read_text().split()[0]
 assert hashlib.sha256((B/'bin/emulationstation').read_bytes()).hexdigest()==expected,'Integridade do Aura inválida'
 marker=B/'row-lifecycle-fix.done';revision=hashlib.sha256((P/'manifest.json').read_bytes()).hexdigest()
 target=B/'dispatch/emulationstation'
 if marker.exists() and marker.read_text()==revision and target.read_bytes()==(P/'dispatcher').read_bytes():return
 backup=B/('backup-row-lifecycle-'+str(time.time_ns()));backup.mkdir()
 shutil.copy2(target,backup/'dispatcher')
 for name in ('enabled','disabled-after-failure'):
  if (B/name).exists():shutil.copy2(B/name,backup/name)
 candidate=target.with_suffix('.row-new');shutil.copy2(P/'dispatcher',candidate);candidate.chmod(0o755);os.replace(candidate,target)
 (B/'enabled').touch()
 marker.write_text(revision)
 print('Aura reativado. Encerramento por sinal não desativa mais a segunda fileira.')
if __name__=='__main__':apply()
