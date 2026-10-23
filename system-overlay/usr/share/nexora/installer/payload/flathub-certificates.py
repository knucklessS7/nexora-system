#!/usr/bin/env python3
"""Use the supplied Mozilla trust anchors for the system Flathub remote only."""
from pathlib import Path
import configparser
import os
import shutil
import ssl
import sys
import tempfile
import time
import subprocess


def configure(cafile, backup_dir, candidates):
    cafile = Path(cafile).resolve(strict=True)
    # Reject empty, invalid or non-certificate downloads before changing config.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cafile=str(cafile))
    if not context.cert_store_stats()['x509_ca']:
        raise ValueError('A base de certificados nao contem autoridades confiaveis.')
    for folder in candidates:
        target = (Path(folder) / 'repo/config').resolve()
        if not target.is_file():
            continue
        cfg = configparser.ConfigParser(interpolation=None)
        cfg.optionxform = str
        cfg.read(target, encoding='utf-8')
        section = 'remote "flathub"'
        if not cfg.has_section(section):
            continue
        if cfg.get(section, 'tls-ca-path', fallback='') == str(cafile) and cfg.get(section, 'tls-permissive', fallback='false') == 'false':
            print('[CERTIFICADOS] Flathub ja usa a base Mozilla do Aura.')
            return
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup_dir / ('flathub-config-' + str(time.time_ns()) + '.ini'))
        cfg.set(section, 'tls-ca-path', str(cafile))
        cfg.set(section, 'tls-permissive', 'false')
        fd, temporary = tempfile.mkstemp(prefix='aura-config-', dir=target.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
                cfg.write(stream)
                stream.flush()
                os.fsync(stream.fileno())
            shutil.copymode(target, temporary)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        print('[CERTIFICADOS] Flathub configurado com base Mozilla; validacao TLS ativa.')
        return
    raise RuntimeError('Configuracao do Flathub de sistema nao localizada; nenhuma alteracao aplicada.')


def installations():
    candidates = []
    if os.environ.get('FLATPAK_SYSTEM_DIR'):
        candidates.append(os.environ['FLATPAK_SYSTEM_DIR'])
    try:
        result = subprocess.run(['flatpak', '--installations'], capture_output=True, text=True, timeout=20)
        if result.returncode == 0:
            candidates.extend(line.strip() for line in result.stdout.splitlines() if line.strip().startswith('/'))
    except (OSError, subprocess.TimeoutExpired):
        pass
    candidates.extend(['/userdata/saves/flatpak/binaries', '/var/lib/flatpak', '/userdata/saves/flatpak'])
    return list(dict.fromkeys(candidates))


if __name__ == '__main__':
    candidates = installations()
    configure(sys.argv[1], sys.argv[2], candidates)
