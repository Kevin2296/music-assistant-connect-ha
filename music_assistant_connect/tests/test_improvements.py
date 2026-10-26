import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from main import app, navigation_url
from browser import ProviderBrowser

@pytest.mark.asyncio
@pytest.mark.parametrize('envelope', [False, True])
async def test_form_with_null_result_survives_http_bridge(monkeypatch, envelope):
    import main
    form={'flow_id':'f1','type':'form','entries':[{'key':'cookie'}], 'result':None}
    payload={'message_id':'m1','result':form} if envelope else form
    captured={}
    class FakeClient:
        def __init__(self,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,url,*,json,headers):
            captured.update(url=url,headers=headers)
            return SimpleNamespace(status_code=200,raise_for_status=lambda:None,json=lambda:payload)
    client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('172.30.32.2',123)),base_url='https://home.example')
    monkeypatch.setattr(main,'options',lambda:{'ma_url':'http://192.168.1.5:8095','ma_token':'server-secret'})
    monkeypatch.setattr(main.httpx,'AsyncClient',FakeClient)
    async with client:
        result=await client.post('/api/ma',json={'url':'https://attacker.example','token':'override','command':'config/providers/setup','args':{'provider_domain':'ytmusic'}})
    assert result.status_code==200
    assert result.json()['data']==form
    assert captured['url']=='http://192.168.1.5:8095/api'
    assert captured['headers']['Authorization']=='Bearer server-secret'
    assert 'server-secret' not in result.text

@pytest.mark.asyncio
async def test_settings_never_expose_token_and_require_ingress(monkeypatch):
    import main
    monkeypatch.setattr(main,'options',lambda:{'ma_url':'http://192.168.1.5:8095','ma_token':'server-secret','ma_ui_url':'/hassio/ingress/example'})
    for peer,code in [('172.30.32.2',200),('192.168.1.5',403)]:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=(peer,123)),base_url='https://home.example') as c:
            result=await c.get('/api/settings',headers={'X-Ingress-Path':'/api/hassio_ingress/example','X-Forwarded-For':'172.30.32.2'})
            assert result.status_code==code
            assert 'server-secret' not in result.text
            assert result.headers['cache-control']=='no-store'
            if code==200: assert result.json()['configured'] is True

def test_navigation_rejects_unsafe_addresses():
    for address in ['javascript:alert(1)','//evil.example','/\\evil.example','https://user:secret@host','http://192.168.1.1:8095']:
        assert navigation_url(address)==''
    assert navigation_url('/hassio/ingress/music')=='/hassio/ingress/music'
    assert navigation_url('https://music.example')=='https://music.example'

@pytest.mark.asyncio
async def test_partial_soundcloud_capture_keeps_browser_open():
    class Context:
        async def cookies(self): return [{'name':'oauth_token','value':'secret','domain':'.soundcloud.com'}]
    class Page:
        def is_closed(self): return False
    b=ProviderBrowser();b.context=Context();b.page=Page();b.provider='soundcloud';b.started=__import__('time').monotonic()
    closed=[]
    async def close(): closed.append(True)
    b._close_unlocked=close
    result=await b.extract()
    assert result['found'] is False
    assert result['values']['authorization']=='OAuth secret'
    assert not closed
    b.client_id='A'*32
    assert (await b.extract())['found'] is True
    assert closed

def test_runtime_preserves_proxy_peer():
    startup=(Path(__file__).parents[1]/'startup.py').read_text()
    assert 'proxy_headers=False' in startup
