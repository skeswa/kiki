#!/usr/bin/env python3
"""Isolated Herdr 0.9.5 + jj smoke test, with no agent or integration install."""
import argparse, json, os, pathlib, shlex, socket, subprocess, tempfile, time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--herdr', type=pathlib.Path, required=True, help='Existing Herdr executable; recorded research used 0.9.5')
args = parser.parse_args()
binary = args.herdr.expanduser().resolve()
if not binary.is_file():
    parser.error('--herdr must name an existing executable')
# Use a short Unix socket path, even when the platform temp directory is long.
root = pathlib.Path(tempfile.mkdtemp(prefix='kiki-herdr-', dir='/tmp'))
config = root / 'config' / 'herdr'
config.mkdir(parents=True)
(root / 'runtime').mkdir()
(root / 'empty.toml').write_text('')
(config / 'config.toml').write_text('onboarding = false\n[update]\nversion_check = false\nmanifest_check = false\n[terminal]\ndefault_shell = "/bin/sh"\nshell_mode = "non_login"\n[session]\nresume_agents_on_restore = false\n')
env = {k:v for k,v in os.environ.items() if not k.startswith('HERDR_')}
env.update(XDG_CONFIG_HOME=str(root/'config'), XDG_STATE_HOME=str(root/'state'), XDG_CACHE_HOME=str(root/'cache'), XDG_RUNTIME_DIR=str(root/'runtime'), HERDR_SOCKET_PATH=str(root/'api.sock'), SHELL='/bin/sh', ENV='', JJ_CONFIG=str(root/'empty.toml'))
records=[]

def command(argv):
    p=subprocess.run(argv, env=env, cwd=root, text=True, capture_output=True, timeout=20)
    records.append({'argv':argv,'code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    assert p.returncode == 0, records[-1]
    return p.stdout

def rpc(method, params=None):
    request={'id':str(len(records)), 'method':method, 'params':params or {}}
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(10)
        sock.connect(env['HERDR_SOCKET_PATH'])
        sock.sendall((json.dumps(request)+'\n').encode())
        data=sock.makefile('rb').readline()
    response=json.loads(data)
    records.append({'request':request,'response':response})
    assert 'error' not in response, response
    return response['result']

parent=root/'parent'
child=root/'child'
command(['jj','git','init','--no-colocate',str(parent)])
command(['jj','-R',str(parent),'workspace','add','--name','child',str(child)])
assert not (child/'.git').exists()
result={'root':str(root),'binary':str(binary),'version':command([str(binary),'--version']).strip()}
log=(root/'server.log').open('w')
server=subprocess.Popen([str(binary),'server'],env=env,cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
try:
    deadline=time.monotonic()+15
    while not (root/'api.sock').exists():
        if server.poll() is not None:
            raise RuntimeError((root/'server.log').read_text())
        assert time.monotonic()<deadline, 'server socket timeout'
        time.sleep(.05)
    result['ping']=rpc('ping')
    created=rpc('workspace.create',{'cwd':str(child),'label':'kiki jj smoke','env':{'KIKI_THREAD_ID':'research-thread'}})
    result['created']=created
    workspace_id=created['workspace']['workspace_id']
    panes=rpc('pane.list',{'workspace_id':workspace_id})['panes']
    pane_id=panes[0]['pane_id']
    rpc('workspace.report_metadata',{'workspace_id':workspace_id,'source':'user:kiki-research','tokens':{'thread_id':'research-thread','jj_status':'research'}})
    result['metadata']=rpc('workspace.get',{'workspace_id':workspace_id})
    marker=root/'actual-cwd.txt'
    # Wait for the new shell before submitting a short command.
    time.sleep(.2)
    rpc('pane.send_input',{'pane_id':pane_id,'text':'pwd > '+shlex.quote(str(marker)),'keys':['Enter']})
    deadline=time.monotonic()+10
    while not marker.exists():
        assert time.monotonic()<deadline, 'shell command timeout'
        time.sleep(.05)
    assert pathlib.Path(marker.read_text().strip()).resolve()==child.resolve()
    result['cwd_verified']=True
    result['snapshot']=rpc('session.snapshot')
    (child/'keep.txt').write_text('keep after closing terminal\n')
    rpc('workspace.close',{'workspace_id':workspace_id})
    assert (child/'keep.txt').read_text()=='keep after closing terminal\n'
    assert (child/'.jj').is_dir()
    result['close_preserves_workspace_files']=True
finally:
    if server.poll() is None:
        try:
            rpc('server.stop')
            server.wait(timeout=10)
        except Exception:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
    result['server_exit']=server.returncode
    log.close()
    (root/'commands.json').write_text(json.dumps(records,indent=2))
    (root/'results.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ('snapshot','created','metadata')},indent=2))
