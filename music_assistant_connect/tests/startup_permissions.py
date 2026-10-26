"""Linux/root integration check: Supervisor's root-owned mode-0600 options file."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

assert os.getuid()==0, 'Run this integration check as root on Linux.'
app_dir=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as folder:
    os.chmod(folder,0o755)
    options=Path(folder)/'options.json'
    options.write_text(json.dumps({'ma_url':'http://192.168.1.5:8095','ma_token':'integration-secret'}))
    os.chmod(options,0o600)
    script=r'''
import asyncio, os, pathlib, sys, types
sys.path.insert(0, sys.argv[1])
import startup
options=pathlib.Path(sys.argv[2])
original_load=startup.load_options
original_drop=startup.drop_privileges
startup.load_options=lambda:original_load(options)
startup.drop_privileges=lambda:original_drop('nobody')
def serve(app, **kwargs):
    import main, httpx
    assert os.getuid()!=0 and os.getgid()!=0 and os.getgroups()==[]
    try:
        options.read_text()
    except PermissionError:
        pass
    else:
        raise AssertionError('Runtime user can read protected Supervisor file')
    assert main.options()['ma_token']=='integration-secret'
    assert kwargs['proxy_headers'] is False
    async def request():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('172.30.32.2',123)),base_url='http://ha.test') as client:
            response=await client.get('/api/settings')
            assert response.status_code==200
            assert response.json()['configured'] is True
            assert 'integration-secret' not in response.text
    asyncio.run(request())
sys.modules['uvicorn']=types.SimpleNamespace(run=serve)
startup.main()
'''
    result=subprocess.run([sys.executable,'-c',script,str(app_dir),str(options)],capture_output=True,text=True)
    assert result.returncode==0, result.stderr
    assert 'integration-secret' not in result.stdout+result.stderr
    assert options.stat().st_uid==0
    assert options.stat().st_mode & 0o777==0o600
print('Root-only Supervisor options loaded; HTTP runtime runs unprivileged; token remains private.')
