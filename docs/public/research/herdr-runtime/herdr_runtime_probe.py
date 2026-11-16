#!/usr/bin/env python3
"""Isolated Unix Herdr lifecycle probe; only signals fixture-owned processes."""
import argparse, fcntl, json, os, pathlib, pty, select, shlex, signal, socket, struct, subprocess, sys, tempfile, termios, time
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--herdr',type=pathlib.Path,required=True)
args=parser.parse_args()
binary=args.herdr.resolve()
root=pathlib.Path(tempfile.mkdtemp(prefix='kk-runtime-',dir='/tmp'))
config=root/'config'/'herdr'
config.mkdir(parents=True)
(root/'runtime').mkdir()
(config/'config.toml').write_text('onboarding = false\n[update]\nversion_check = false\nmanifest_check = false\n[terminal]\ndefault_shell = "/bin/sh"\nshell_mode = "non_login"\n[session]\nresume_agents_on_restore = false\n')
env={k:v for k,v in os.environ.items() if not k.startswith('HERDR_')}
env.update(XDG_CONFIG_HOME=str(root/'config'),XDG_STATE_HOME=str(root/'state'),XDG_RUNTIME_DIR=str(root/'runtime'),XDG_CACHE_HOME=str(root/'cache'),HERDR_SOCKET_PATH=str(root/'api.sock'),HERDR_CLIENT_SOCKET_PATH=str(root/'client.sock'),SHELL='/bin/sh',ENV='',TERM='xterm-256color')
records=[]
result={'root':str(root),'version':subprocess.check_output([str(binary),'--version'],text=True).strip()}
server=None
clients=[]
owned=[]
logs=[]
worker=root/'worker.py'
worker.write_text('''import json, os, pathlib, signal, subprocess, sys, time
folder=pathlib.Path(sys.argv[1]); folder.mkdir(exist_ok=True)
if sys.argv[2]=='ignore-hup': signal.signal(signal.SIGHUP,signal.SIG_IGN)
if sys.argv[2]=='child':
 while True: time.sleep(.1)
child=subprocess.Popen([sys.executable,__file__,str(folder),'child'])
(folder/'identity.json').write_text(json.dumps({'pid':os.getpid(),'child':child.pid,'pgid':os.getpgrp(),'sid':os.getsid(0),'tag':os.environ.get('KIKI_RESEARCH_TAG'),'cwd':os.getcwd(),'argv':sys.argv[2:]}))
while True:
 (folder/'heartbeat').write_text(str(time.monotonic_ns()))
 time.sleep(.05)
''')

def wait_until(fn,timeout=10):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        value=fn()
        if value: return value
        time.sleep(.04)
    raise RuntimeError('timeout: '+str(fn))

def rpc(method,params=None):
    req={'id':str(len(records)),'method':method,'params':params or {}}
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(10);sock.connect(env['HERDR_SOCKET_PATH'])
        sock.sendall((json.dumps(req)+'\n').encode())
        reply=json.loads(sock.makefile('rb').readline())
    records.append({'request':req,'response':reply})
    if 'error' in reply: raise RuntimeError(reply)
    return reply['result']

def start_server():
    global server
    log=(root/('server-'+str(len(logs))+'.log')).open('w');logs.append(log)
    server=subprocess.Popen([str(binary),'server'],env=env,cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
    def ready():
        if server.poll() is not None: raise RuntimeError('server exited '+str(server.returncode))
        try: return rpc('ping')
        except (FileNotFoundError,ConnectionRefusedError,ConnectionResetError): return False
    wait_until(ready)

def stop_server():
    if server and server.poll() is None:
        rpc('server.stop');server.wait(timeout=10)

def ps(pid):
    p=subprocess.run(['ps','-p',str(pid),'-o','stat=','-o','command='],text=True,capture_output=True)
    return p.stdout.strip()

def running(pid):
    info=ps(pid)
    return bool(info and not info.startswith('Z'))

def create(label,tag=None):
    params={'cwd':str(root),'label':label}
    if tag:params['env']={'KIKI_RESEARCH_TAG':tag}
    r=rpc('workspace.create',params)
    wid=r['workspace']['workspace_id']
    pane=rpc('pane.list',{'workspace_id':wid})['panes'][0]
    return wid,pane

def run_worker(pane,name,mode='normal'):
    folder=root/name;folder.mkdir()
    time.sleep(.15)
    rpc('pane.send_input',{'pane_id':pane,'text':'exec '+shlex.join([sys.executable,str(worker),str(folder),mode]),'keys':['Enter']})
    wait_until(lambda:(folder/'identity.json').exists())
    ident=json.loads((folder/'identity.json').read_text())
    owned.extend([ident['pid'],ident['child']])
    wait_until(lambda:(folder/'heartbeat').exists())
    return folder,ident

def direct_worker(wid,name):
    folder=root/name;folder.mkdir()
    layout=rpc('layout.apply',{'workspace_id':wid,'tab_label':name,'root':{
        'type':'pane','cwd':str(root),'command':[sys.executable,str(worker),str(folder),'normal','literal;$() with spaces'],
        'env':{'KIKI_RESEARCH_TAG':'direct-tag'}}})['layout']
    pane=layout['root']['pane_id']
    wait_until(lambda:(folder/'identity.json').exists())
    ident=json.loads((folder/'identity.json').read_text())
    owned.extend([ident['pid'],ident['child']])
    return pane,ident

def alive_heartbeat(folder):
    old=(folder/'heartbeat').read_text();time.sleep(.2)
    return old!=(folder/'heartbeat').read_text()

def shell_env(pane,name):
    f=root/(name+'.json')
    code='import os,json,pathlib;pathlib.Path('+repr(str(f))+').write_text(json.dumps({"tag":os.environ.get("KIKI_RESEARCH_TAG"),"pid":os.getpid()}))'
    rpc('pane.send_input',{'pane_id':pane,'text':shlex.join([sys.executable,'-c',code]),'keys':['Enter']})
    wait_until(lambda:f.exists())
    return json.loads(f.read_text())

def attach():
    master,slave=pty.openpty()
    fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,120,0,0))
    client=subprocess.Popen([str(binary),'client'],env=env,cwd=root,stdin=slave,stdout=slave,stderr=slave,start_new_session=True)
    os.close(slave);os.set_blocking(master,False);clients.append((client,master))
    data=bytearray();end=time.monotonic()+1.5
    while time.monotonic()<end:
        try:
            chunk=os.read(master,65536);data.extend(chunk)
            # Answer common terminal queries to allow headless fixture attach.
            if b'\x1b[6n' in chunk:os.write(master,b'\x1b[1;1R')
            if b'\x1b[c' in chunk:os.write(master,b'\x1b[?1;2c')
        except BlockingIOError:pass
        except OSError:break
        time.sleep(.02)
    return client,master,len(data)

try:
    start_server()
    direct_wid,_=create('direct-launch')
    direct_pid,direct_ident=direct_worker(direct_wid,'direct-initial')
    result['direct_argv_initial']=direct_ident
    result['direct_argv_process_info']=rpc('pane.process_info',{'pane_id':direct_pid})
    wid,pane=create('lifecycle','initial-tag')
    pid=pane['pane_id']
    result['initial_env']=shell_env(pid,'initial-env')
    split=rpc('pane.split',{'target_pane_id':pid,'direction':'right','cwd':str(root)})
    panes=rpc('pane.list',{'workspace_id':wid})['panes']
    extra=next(p for p in panes if p['pane_id']!=pid)
    result['split_without_env']=shell_env(extra['pane_id'],'split-env')
    rpc('workspace.report_metadata',{'workspace_id':wid,'source':'user:runtime-probe','tokens':{'thread':'fixture'}})
    folder,ident=run_worker(pid,'live')
    result['worker']=ident
    result['no_client_heartbeat']=alive_heartbeat(folder)
    client,master,n=attach()
    result['client_attach']={'running':client.poll() is None,'terminal_bytes':n}
    if client.poll() is None:
        os.write(master,b'\x02q')
        try:client.wait(timeout=4)
        except subprocess.TimeoutExpired:client.terminate();client.wait(timeout=4)
    result['client_detach_exit']=client.returncode
    result['heartbeat_after_client_detach']=alive_heartbeat(folder)
    client2,master2,n2=attach()
    result['second_client_attach']={'running':client2.poll() is None,'terminal_bytes':n2}
    if client2.poll() is None:client2.kill();client2.wait(timeout=4)
    result['heartbeat_after_client_sigkill']=alive_heartbeat(folder)
    result['before_restart_pane']=rpc('pane.get',{'pane_id':pid})
    result['process_info']=rpc('pane.process_info',{'pane_id':pid})
    stop_server()
    result['worker_dead_after_graceful_stop']=not running(ident['pid'])
    result['child_dead_after_graceful_stop']=not running(ident['child'])
    saved=json.loads((config/'session.json').read_text())
    result['persisted_snapshot_keys']=list(saved)
    start_server()
    result['restored_workspace']=rpc('workspace.get',{'workspace_id':wid})
    result['restored_pane']=rpc('pane.get',{'pane_id':pid})
    result['restored_env']=shell_env(pid,'restored-env')
    result['restored_process_info']=rpc('pane.process_info',{'pane_id':pid})
    result['direct_argv_after_restore']=rpc('pane.process_info',{'pane_id':direct_pid})
    respawn_pid,respawn_ident=direct_worker(direct_wid,'direct-exit')
    result['before_process_exit']=rpc('pane.get',{'pane_id':respawn_pid})
    os.kill(respawn_ident['pid'],signal.SIGTERM)
    def respawned():
        try:
            info=rpc('pane.process_info',{'pane_id':respawn_pid})['process_info']
        except RuntimeError:
            if records[-1]['response'].get('error',{}).get('code')=='pane_not_found':
                return {'pane_closed':True}
            raise
        return info if info.get('shell_pid') and info['shell_pid']!=respawn_ident['pid'] else None
    result['after_process_exit_info']=wait_until(respawned)
    if not result['after_process_exit_info'].get('pane_closed'):
        result['after_process_exit']=rpc('pane.get',{'pane_id':respawn_pid})
        result['after_process_exit_env']=shell_env(respawn_pid,'after-exit-env')
    # Close one terminal group while another worker is live.
    other,otherpane=create('other-thread')
    otherfolder,otherident=run_worker(otherpane['pane_id'],'other')
    rpc('workspace.close',{'workspace_id':wid})
    result['other_workspace_survives_close']=alive_heartbeat(otherfolder)
    graceful,gracefulpane=create('graceful-ignore-hup')
    gracefulfolder,gracefulident=run_worker(gracefulpane['pane_id'],'graceful-ignore-hup','ignore-hup')
    rpc('workspace.close',{'workspace_id':graceful})
    result['ignore_hup_worker_dead_after_workspace_close']=not running(gracefulident['pid'])
    result['ignore_hup_child_dead_after_workspace_close']=not running(gracefulident['child'])
    # Restart to get a simple shell before force-kill experiment.
    stop_server();start_server()
    crash,crashpane=create('crash')
    crashfolder,crashident=run_worker(crashpane['pane_id'],'ignore-hup','ignore-hup')
    result['crash_worker']=crashident
    server.kill();server.wait(timeout=5)
    result['server_sigkill_exit']=server.returncode
    time.sleep(.3)
    result['ignore_hup_worker_survives_server_sigkill']=running(crashident['pid'])
    result['ignore_hup_heartbeat_after_server_sigkill']=alive_heartbeat(crashfolder) if running(crashident['pid']) else False
finally:
    for client,fd in clients:
        if client.poll() is None:client.kill();client.wait(timeout=5)
        os.close(fd)
    if server and server.poll() is None:
        try:stop_server()
        except Exception:server.kill();server.wait(timeout=5)
    # Confirm unique fixture path in argv before killing any remaining worker.
    for pid in owned:
        if running(pid) and str(worker) in ps(pid):os.kill(pid,signal.SIGKILL)
    result['remaining_owned_workers']=[pid for pid in owned if running(pid) and str(worker) in ps(pid)]
    for log in logs:log.close()
    (root/'commands.json').write_text(json.dumps(records,indent=2))
    (root/'results.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('before_restart_pane','restored_pane','restored_workspace')},indent=2))
