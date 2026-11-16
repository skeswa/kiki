#!/usr/bin/env python3
"""Private tmux server loss with deliberately HUP-ignoring descendants."""
import json, os, pathlib, signal, subprocess, sys, tempfile, time, uuid

root=pathlib.Path(tempfile.mkdtemp(prefix='kiki-tmux-orphan-'))
env={k:v for k,v in os.environ.items() if k not in ('TMUX','TMUX_PANE')}
records=[]; results={'root':str(root),'cases':{}}
probe=root/'writer.py'
probe.write_text('''import json,os,pathlib,signal,subprocess,sys,time
signal.signal(signal.SIGHUP,signal.SIG_IGN)
r=pathlib.Path(sys.argv[1]);role=sys.argv[2]
if role=='worker':
 c=subprocess.Popen([sys.executable,__file__,str(r),'child'])
 (r/'pids.json').write_text(json.dumps(dict(worker=os.getpid(),child=c.pid,group=os.getpgrp())))
while True:
 (r/(role+'.heartbeat')).write_text(str(time.time_ns()))
 time.sleep(.025)
''')
for mode in ('graceful','sigkill'):
    case=root/mode;case.mkdir()
    sock='kiki-research-'+uuid.uuid4().hex
    base=['tmux','-L',sock,'-f','/dev/null']
    pids={}
    def tmux(*args,ok=True):
        p=subprocess.run(base+list(args),env=env,text=True,capture_output=True,timeout=5)
        records.append(dict(argv=base+list(args),code=p.returncode,stdout=p.stdout,stderr=p.stderr))
        if ok and p.returncode:raise RuntimeError(records[-1])
        return p.stdout.strip()
    try:
        ids=tmux('new-session','-d','-P','-F','#{pid} #{pane_pid}', '-s','orphan',sys.executable,str(probe),str(case),'worker')
        end=time.monotonic()+5
        while not all((case/f).exists() for f in ('pids.json','worker.heartbeat','child.heartbeat')):
            assert time.monotonic()<end
            time.sleep(.02)
        pids=json.loads((case/'pids.json').read_text())
        before={role:(case/(role+'.heartbeat')).read_text() for role in ('worker','child')}
        if mode=='sigkill':os.kill(int(ids.split()[0]),signal.SIGKILL)
        else:tmux('kill-server')
        time.sleep(.25)
        after={role:(case/(role+'.heartbeat')).read_text() for role in ('worker','child')}
        results['cases'][mode]=dict(socket=sock,ids=ids,pids=pids,
            heartbeat_advanced={role:before[role]!=after[role] for role in before},
            has_session=tmux('has-session','-t','orphan',ok=False))
    finally:
        for role in ('child','worker'):
            if role in pids:
                try:os.kill(pids[role],signal.SIGKILL)
                except ProcessLookupError:pass
        tmux('kill-server',ok=False)
results['version']=subprocess.run(['tmux','-V'],capture_output=True,text=True).stdout.strip()
(root/'results.json').write_text(json.dumps(results,indent=2))
(root/'commands.json').write_text(json.dumps(records,indent=2))
print(json.dumps(results,indent=2))
