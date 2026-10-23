"""Resolve a stale DHCP address without binding to every interface."""
import ipaddress
import json
import subprocess

def select(config, rows, routes):
    addresses=[]
    for row in rows:
        for addr in row.get('addr_info',[]):
            ip=ipaddress.ip_address(addr['local'])
            if addr.get('family')=='inet' and ip.is_private and not ip.is_loopback and not ip.is_link_local:
                addresses.append((row['ifname'],addr))
    if any(a['local']==config['bind'] for _,a in addresses):return dict(config)
    if ipaddress.ip_address(config['bind']).is_loopback:return dict(config)
    default={r.get('dev') for r in routes if r.get('dst')=='default'}
    candidates=[a for dev,a in addresses if dev in default] or [a for _,a in addresses]
    if not candidates:raise RuntimeError('Sem IPv4 de rede local. Conecte a rede e abra o pareamento novamente.')
    addr=candidates[0];ip=addr['local'];result=dict(config)
    result['bind']=ip
    scheme='https' if config.get('cert') else 'http'
    result['origins']=[f"{scheme}://{ip}:{config.get('port',8765)}"]
    result['networks']=[str(ipaddress.ip_network(f"{ip}/{addr['prefixlen']}",strict=False)),'127.0.0.0/8']
    return result

def current(config):
    def query(*args):return json.loads(subprocess.check_output(['ip','-j','-4',*args],timeout=3))
    return select(config,query('addr','show','scope','global'),query('route','show','default'))
