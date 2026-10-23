#!/usr/bin/env python3
"""Bounded local health records; no browsing URLs, environment or credentials."""
import json,os,re,signal,subprocess,sys,time
from pathlib import Path

def read(path):
    try:return Path(path).read_text().strip()
    except OSError:return ''

def snapshot():
    values={}
    for line in read('/proc/meminfo').splitlines():
        key,_,value=line.partition(':')
        if key in ('MemTotal','MemAvailable','SwapTotal','SwapFree'):values[key]=value.strip()
    temperatures=[]
    for hw in Path('/sys/class/hwmon').glob('hwmon*'):
        for sensor in hw.glob('temp*_input'):
            value=read(sensor)
            if value.lstrip('-').isdigit():temperatures.append({'device':read(hw/'name'),'sensor':read(sensor.with_name(sensor.name.replace('_input','_label'))),'celsius':int(value)/1000})
    for zone in Path('/sys/class/thermal').glob('thermal_zone*'):
        value=read(zone/'temp')
        if value.lstrip('-').isdigit():temperatures.append({'device':read(zone/'type'),'celsius':int(value)/1000})
    return {'time':time.time(),'boot_id':read('/proc/sys/kernel/random/boot_id'),'uptime':read('/proc/uptime'),'load':read('/proc/loadavg'),'memory':values,'temperatures':temperatures}

def append(folder,record):
    folder.mkdir(parents=True,exist_ok=True)
    file=folder/'health.jsonl';previous=folder/'health.previous.jsonl'
    if file.exists() and file.stat().st_size>512*1024:os.replace(file,previous)
    with file.open('a',encoding='utf-8') as stream:
        stream.write(json.dumps(record,ensure_ascii=False)+'\n');stream.flush();os.fsync(stream.fileno())

def main():
    owner=int(sys.argv[1]);app=sys.argv[2]
    folders=[Path('/userdata/system/aura/diagnostics'),Path('/boot/aura-diagnostics')]
    running=True
    def stop(*_):
        nonlocal running
        running=False
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    recent=set();first=True
    while running:
        try:os.kill(owner,0)
        except ProcessLookupError:break
        record=snapshot();record.update(app=app,event='start' if first else 'sample');first=False
        try:
            result=subprocess.run(['dmesg','--color=never'],capture_output=True,text=True,timeout=2,errors='replace')
            lines=[line for line in result.stdout.splitlines() if re.search(r'out of memory|oom-kill|killed process|gpu hang|gpu reset|i915.*(error|hang|reset)|thermal.*(critical|thrott)|overheat|machine check|hardware error|I/O error|EXT4-fs error',line,re.I)]
            record['kernel_errors']=[line[:600] for line in lines if line not in recent][-20:];recent=set(lines)
        except (OSError,subprocess.SubprocessError):pass
        for folder in folders:
            try:append(folder,record)
            except OSError:pass
        for _ in range(20):
            if not running:break
            time.sleep(1)
    for folder in folders:
        try:append(folder,dict(snapshot(),app=app,event='monitor-stopped'))
        except OSError:pass

if __name__=='__main__':main()
