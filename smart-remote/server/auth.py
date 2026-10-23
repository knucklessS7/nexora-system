"""Private remembered-device credentials, with locally revocable access."""
import json
import os
from pathlib import Path
import hashlib
import secrets
import time
from collections import defaultdict, deque


class Auth:
    PIN_TTL = 300
    DEVICE_TTL = 365*24*3600
    def __init__(self, clock=time.time, store=None):
        self.clock = clock
        self.pin_hash = None
        self.pin_until = 0
        self.pending = {}
        self.sessions = {}
        self.attempts = defaultdict(deque)
        self.global_attempts = deque()
        self.store = Path(store) if store else None
        if self.store and self.store.exists():
            data=json.loads(self.store.read_text())
            if data.get('version')!=1 or not isinstance(data.get('sessions'),dict):
                raise ValueError('Arquivo de dispositivos inválido.')
            self.sessions={k:v for k,v in data['sessions'].items() if v['until']>self.clock()}

    def save(self):
        if not self.store:return
        self.store.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        tmp=self.store.with_suffix('.tmp')
        fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as stream:
            json.dump({'version':1,'sessions':self.sessions},stream)
            stream.flush();os.fsync(stream.fileno())
        os.chmod(tmp,0o600);os.replace(tmp,self.store)

    def revoke(self, ident=None):
        previous=self.sessions.copy()
        if ident:self.sessions.pop(ident,None)
        else:self.sessions.clear();self.pending.clear();self.pin_hash=None
        try:self.save()
        except OSError:
            self.sessions=previous
            raise

    def remember(self, row):
        # Persist at most once per day; incoming gamepad events never write flash.
        if row['until']-self.clock()<self.DEVICE_TTL-86400:
            row['until']=self.clock()+self.DEVICE_TTL
            self.save()


    @staticmethod
    def digest(value):
        return hashlib.sha256(value.encode()).hexdigest()

    def open_pairing(self):
        self.sessions={k:v for k,v in self.sessions.items() if v['until']>self.clock()}
        if len(self.sessions)>=8:raise ValueError('Revogue um dispositivo antes de parear outro (máximo 8).')
        pin = f'{secrets.randbelow(1000000):06d}'
        self.pin_hash = self.digest(pin)
        self.pin_until = self.clock() + self.PIN_TTL
        self.pending.clear()
        return pin

    def request(self, pin, ip, name):
        now = self.clock()
        for q in (self.attempts[ip], self.global_attempts):
            while q and now - q[0] > 120:
                q.popleft()
        if len(self.attempts[ip]) >= 5 or len(self.global_attempts) >= 20:
            raise ValueError('Muitas tentativas. Aguarde dois minutos.')
        self.attempts[ip].append(now)
        self.global_attempts.append(now)
        if now >= self.pin_until or not self.pin_hash or not secrets.compare_digest(self.digest(pin), self.pin_hash):
            raise ValueError('PIN incorreto, expirado ou pareamento fechado.')
        token = secrets.token_urlsafe(32)
        self.pending[self.digest(token)] = {'name': ''.join(c for c in name[:40] if c.isprintable()), 'ip': ip, 'until': now + 120, 'approved': False}
        self.pin_hash = None  # one successful request per locally opened PIN
        return token

    def approve(self, ident):
        row = self.pending.get(ident)
        if not row or row['until'] <= self.clock():
            raise ValueError('Solicitação expirada.')
        row['approved'] = True

    def exchange(self, token):
        key = self.digest(token)
        row = self.pending.get(key)
        if not row or row['until'] <= self.clock():
            raise ValueError('Solicitação expirada.')
        if not row['approved']:
            return None
        del self.pending[key]
        token = secrets.token_urlsafe(32)
        self.sessions[self.digest(token)] = {'name': row['name'], 'created': self.clock(), 'last': self.clock(), 'until': self.clock()+self.DEVICE_TTL, 'csrf': secrets.token_urlsafe(24)}
        self.save()
        return token

    def session(self, token):
        row = self.sessions.get(self.digest(token or ''))
        if not row or row['until'] <= self.clock():
            raise ValueError('Sessão ausente ou expirada.')
        row['last'] = self.clock()
        return row
