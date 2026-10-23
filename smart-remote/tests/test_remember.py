import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from auth import Auth

class RememberTests(unittest.TestCase):
 def test_restart_renew_and_revoke(self):
  with tempfile.TemporaryDirectory() as folder:
   now=[1700000000.0];path=Path(folder)/'devices.json'
   a=Auth(lambda:now[0],path);pin=a.open_pairing();pending=a.request(pin,'ip','phone');a.approve(a.digest(pending));token=a.exchange(pending)
   self.assertNotIn(token,path.read_text());self.assertNotIn(pin,path.read_text())
   b=Auth(lambda:now[0],path);self.assertEqual(b.session(token)['name'],'phone')
   now[0]+=9*3600;self.assertEqual(b.session(token)['name'],'phone')
   now[0]+=2*86400;row=b.session(token);old=row['until'];b.remember(row);self.assertGreater(row['until'],old)
   b.revoke(b.digest(token));c=Auth(lambda:now[0],path)
   with self.assertRaises(ValueError):c.session(token)
 def test_expired_and_revoke_all(self):
  with tempfile.TemporaryDirectory() as folder:
   now=[1700000000.0];path=Path(folder)/'devices.json';a=Auth(lambda:now[0],path)
   def pair():
    pin=a.open_pairing();p=a.request(pin,'ip','phone');a.approve(a.digest(p));return a.exchange(p)
   one=pair();two=pair();a.revoke(a.digest(one));a.session(two)
   a.revoke();b=Auth(lambda:now[0],path);self.assertFalse(b.sessions)
   token=pair();now[0]+=Auth.DEVICE_TTL+1
   with self.assertRaises(ValueError):Auth(lambda:now[0],path).session(token)
if __name__=='__main__':unittest.main()
