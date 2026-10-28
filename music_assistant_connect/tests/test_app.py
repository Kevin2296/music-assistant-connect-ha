"""Run: pytest -q"""
import os
import sys
from pathlib import Path
import pytest
import httpx

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from main import app, validate_ma_url
from browser import ProviderBrowser

SUPERVISOR=('172.30.32.2',49500)

@pytest.mark.asyncio
async def test_http_basics():
    transport=httpx.ASGITransport(app=app, client=SUPERVISOR)
    async with httpx.AsyncClient(transport=transport,base_url='http://test') as c:
        assert (await c.get('/')).status_code==200
        assert (await c.get('/health')).json()['ok']
        assert (await c.get('/')).status_code==200
        page=(await c.get('/',)).text
        assert 'Music Connect' in page
        assert "'Inloggen bij '" in (await c.get('/app.js',)).text

@pytest.mark.asyncio
async def test_local_only_rules():
    assert validate_ma_url('http://127.0.0.1:8095')=='http://127.0.0.1:8095'
    assert validate_ma_url('http://192.168.1.2:8095')=='http://192.168.1.2:8095'
    for host in ['http://1.1.1.1:8095', 'http://169.254.169.254:8095', 'file:///etc/passwd','http://127.0.0.1:9898']:
        with pytest.raises(ValueError):validate_ma_url(host)

@pytest.mark.asyncio
async def test_api_rejects_unknown_commands():
    transport=httpx.ASGITransport(app=app, client=SUPERVISOR)
    async with httpx.AsyncClient(transport=transport,base_url='http://test') as c:
        res=await c.post('/api/ma',json={'url':'http://127.0.0.1:8095','token':'123456789','command':'system/erase','args':{}})
        assert res.status_code==400
        assert 'Niet-toegestaan' in res.json()['detail']

@pytest.mark.asyncio
async def test_browser_cookie_extraction():
    class StubContext:
        async def cookies(self):
            return [{'name':'oauth_token','value':'test-soundcloud-token','domain':'.soundcloud.com'}, {'name':'arl','value':'aabbcc','domain':'.deezer.com'}]
    class StubPage:
        def is_closed(self):return False
    b=ProviderBrowser();b.context=StubContext();b.page=StubPage();b.provider='soundcloud';b.client_id='A'*32;b.started=__import__('time').monotonic()
    async def close():
        b.context=None;b.page=None
    b._close_unlocked=close
    result=await b.extract()
    assert result['values']=={'client_id':'A'*32,'authorization':'OAuth test-soundcloud-token'}
    b.context=StubContext();b.page=StubPage();b.provider='deezer';b.started=__import__('time').monotonic()
    result=await b.extract()
    assert result['values']['arl']=='aabbcc'

@pytest.mark.asyncio
async def test_browser_rejects_wrong_inputs():
    transport=httpx.ASGITransport(app=app, client=SUPERVISOR)
    async with httpx.AsyncClient(transport=transport,base_url='http://test') as c:
        assert (await c.post('/api/browser/key',headers={'X-Remote-User-Id':'test-admin'},json={'value':'Control+Shift+J'})).status_code==400
        assert (await c.post('/api/browser/start',headers={'X-Remote-User-Id':'test-admin'},json={'provider':'totally-unrelated'})).status_code==400

@pytest.mark.asyncio
async def test_ma_setup_command_forwarding(monkeypatch):
    import main
    from types import SimpleNamespace
    captured={}
    class FakeClient:
        def __init__(self,**kwargs):
            assert kwargs['follow_redirects'] is False
        async def __aenter__(self):return self
        async def __aexit__(self,*args):return None
        async def post(self,url,*,json,headers):
            captured['url']=url
            captured['payload']=json
            assert headers['Authorization']=='Bearer abcde12345'
            return SimpleNamespace(status_code=200,raise_for_status=lambda:None,json=lambda:{'message_id':'xx','result':{'flow_id':'f1','step_id':'user','type':'form','entries':[]}})
    original_client = httpx.AsyncClient
    client=original_client(transport=httpx.ASGITransport(app=app, client=SUPERVISOR),base_url='http://test')
    monkeypatch.setattr(main.httpx,'AsyncClient',FakeClient)
    async with client:
        res=await client.post('/api/ma',json={'url':'http://127.0.0.1:8095','token':'abcde12345','command':'config/providers/setup','args':{'provider_domain':'soundcloud'}})
    assert res.status_code==200
    assert res.json()['data']['flow_id']=='f1'
    assert captured['url']=='http://127.0.0.1:8095/api'
    assert captured['payload']['command']=='config/providers/setup'

@pytest.mark.asyncio
async def test_ingress_is_trusted_only_from_supervisor(monkeypatch):
    import main
    supervisor=httpx.ASGITransport(app=app, client=('172.30.32.2', 49500))
    outside=httpx.ASGITransport(app=app, client=('172.30.32.99', 49501))
    async with httpx.AsyncClient(transport=supervisor, base_url='http://test') as c:
        page=await c.get('/',headers={'X-Remote-User-Id':'admin-id'})
        assert page.status_code==200
        assert page.headers['x-frame-options']=='SAMEORIGIN'
        assert 'frame-ancestors \'self\'' in page.headers['content-security-policy']
        assert 'href="style.css"' in page.text
        assert 'src="app.js"' in page.text
        assert 'href="/style.css"' not in page.text
        assert (await c.get('/app.js')).status_code==200
        js=(await c.get('/app.js')).text
        assert "post('api/ma'" in js
        assert (await c.get('/sw.js')).status_code==404
    async with httpx.AsyncClient(transport=outside, base_url='http://test') as c:
        res=await c.get('/',headers={'X-Remote-User-Id':'admin-id','X-Ingress-Path':'/api/hassio_ingress/fake/'})
        assert res.status_code==403
        assert res.headers['x-frame-options']=='DENY'

@pytest.mark.asyncio
async def test_ingress_separates_browser_users(monkeypatch):
    import main
    class StubPage:pass
    monkeypatch.setattr(main.browser, 'page', StubPage())
    monkeypatch.setattr(main, 'browser_session_owner', 'ha:user-a')
    supervisor=httpx.ASGITransport(app=app, client=('172.30.32.2', 49500))
    async with httpx.AsyncClient(transport=supervisor,base_url='http://test') as c:
        res=await c.post('/api/browser/close',headers={'X-Remote-User-Id':'user-b'})
        assert res.status_code==423
        res=await c.post('/api/browser/close')
        assert res.status_code==403
    monkeypatch.setattr(main.browser, 'page', None)
