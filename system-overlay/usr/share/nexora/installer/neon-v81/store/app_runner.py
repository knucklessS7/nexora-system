#!/usr/bin/env python3
"""Launch Aura .app entries without treating their metadata as shell code."""
from pathlib import Path
import os, shlex, sys

def command(path):
    path=Path(path)
    if not path.is_file(): raise ValueError('Atalho nao encontrado.')
    text=path.read_text(encoding='utf-8-sig')
    if text.startswith('#!'): return ['bash',str(path)]
    data=dict(line.split('=',1) for line in text.splitlines() if '=' in line and not line.startswith('#'))
    if data.get('type')!='command' or not data.get('exec'): raise ValueError('Formato .app nao reconhecido.')
    argv=shlex.split(data['exec'])
    if not argv: raise ValueError('Atalho sem comando.')
    # Original Aura streaming entries point directly to launch.sh.
    if len(argv)==1 and Path(argv[0]).is_file() and argv[0].endswith('.sh'): return ['bash',argv[0]]
    return argv

if __name__=='__main__':
    try:
        argv=command(sys.argv[1]);os.execvp(argv[0],argv)
    except Exception as exc:
        print('Aura: '+str(exc),file=sys.stderr);sys.exit(1)
