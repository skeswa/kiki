#!/usr/bin/env python3
"""Isolated tmux baseline smoke. Never addresses the default/user server."""
import json, os, pathlib, select, signal, subprocess, sys, tempfile, time, uuid

root = pathlib.Path(tempfile.mkdtemp(prefix='kiki-tmux-runtime-'))
socket_name = 'kiki-research-' + uuid.uuid4().hex
env = {k:v for k,v in os.environ.items() if k not in ('TMUX', 'TMUX_PANE')}
base = ['tmux', '-L', socket_name, '-f', '/dev/null']
records = []
clients = []
result = {'root':str(root), 'socket_name':socket_name}

def tmux(*args, ok=True):
    p = subprocess.run(base + list(args), env=env, text=True, capture_output=True, timeout=10)
    records.append({'argv':base+list(args),'code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    if ok and p.returncode:
        raise RuntimeError(records[-1])
    return p.stdout.strip()

def await_file(path):
    end = time.monotonic()+5
    while not path.exists():
        if time.monotonic()>end:
            raise RuntimeError('Missing marker '+str(path))
        time.sleep(.02)
    return json.loads(path.read_text())

def control(*args):
    p=subprocess.Popen(base+['-C','attach-session','-t','baseline']+list(args),env=env,
                       stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    clients.append(p)
    return p

def control_command(p, command):
    p.stdin.write((command+'\n').encode());p.stdin.flush()
    time.sleep(.08)

def drain(p):
    chunks=[]
    while select.select([p.stdout],[],[],.1)[0]:
        chunk=os.read(p.stdout.fileno(),65536)
        if not chunk:break
        chunks.append(chunk)
    return b''.join(chunks).decode(errors='replace')

probe=root/'probe.py'
probe.write_text('''import json,os,pathlib,signal,sys,time
p=pathlib.Path(sys.argv[1])
p.write_text(json.dumps(dict(pid=os.getpid(),argv=sys.argv[2:],cwd=os.getcwd(),env=os.environ.get('KIKI_PROBE'),pane=os.environ.get('TMUX_PANE'))))
print('ready marker',flush=True)
signal.signal(signal.SIGHUP,lambda *_:sys.exit(0))
while True:time.sleep(.1)
''')
try:
    result['version']=tmux('-V')
    marker=root/'initial.json'
    result['initial_ids']=tmux('new-session','-d','-P','-F','#{session_id} #{window_id} #{pane_id} #{pid} #{pane_pid}',
                              '-s','baseline','-c',str(root),'-e','KIKI_PROBE=initial',
                              sys.executable,str(probe),str(marker),'literal;$() with spaces')
    result['initial']=await_file(marker)
    pane=result['initial']['pane']
    result['capture']=tmux('capture-pane','-p','-t',pane)
    a=control()
    control_command(a,'refresh-client -C 120x40')
    b=control()
    control_command(b,'refresh-client -C 80x24')
    tmux('set-option','-w','-t',pane,'window-size','smallest')
    result['two_clients_smallest']=tmux('display-message','-p','-t',pane,'#{window_width}x#{window_height}')
    tmux('set-option','-w','-t',pane,'window-size','largest')
    result['two_clients_largest']=tmux('display-message','-p','-t',pane,'#{window_width}x#{window_height}')
    result['clients']=tmux('list-clients','-F','#{client_name} #{client_width}x#{client_height} #{client_control_mode}')
    result['control_output']=drain(a)
    for p in clients:
        p.terminate();p.wait(timeout=5)
    result['after_client_disconnect']=tmux('display-message','-p','-t',pane,'#{pane_id} #{pane_pid} #{session_attached}')
    waiter=subprocess.Popen(base+['wait-for','kiki-ready'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    time.sleep(.05)
    result['waiter_was_blocked']=waiter.poll() is None
    tmux('wait-for','-S','kiki-ready')
    waiter.wait(timeout=5)
    result['waiter_exit']=waiter.returncode
    marker=root/'respawn.json'
    tmux('respawn-pane','-k','-t',pane,'-c',str(root),'-e','KIKI_PROBE=respawn',
         sys.executable,str(probe),str(marker),'new process')
    result['respawn']=await_file(marker)
    result['respawn_ids']=tmux('display-message','-p','-t',pane,'#{session_id} #{window_id} #{pane_id} #{pane_pid}')
    server_pid=int(result['initial_ids'].split()[3])
    os.kill(server_pid,signal.SIGKILL)
    time.sleep(.15)
    result['server_crash_has_session']=tmux('has-session','-t','baseline',ok=False)
    check=subprocess.run(base+['has-session','-t','baseline'],env=env,capture_output=True,text=True,timeout=5)
    result['after_crash_has_session_exit']=check.returncode
    result['after_crash_stderr']=check.stderr
finally:
    for p in clients:
        if p.poll() is None:
            p.terminate();p.wait(timeout=5)
    tmux('kill-server',ok=False)
    (root/'commands.json').write_text(json.dumps(records,indent=2))
    (root/'results.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
