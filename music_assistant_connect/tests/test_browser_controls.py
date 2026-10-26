import time
from types import SimpleNamespace

import httpx
import pytest

from browser import ProviderBrowser
from main import app


@pytest.mark.asyncio
async def test_scroll_wheels_inside_viewport_and_handles_page_keys():
    calls=[]
    class Mouse:
        async def move(self,*args):calls.append(('move',args))
        async def wheel(self,*args):calls.append(('wheel',args))
    class Keyboard:
        async def press(self,value):calls.append(('key',value))
    class Page:
        mouse=Mouse();keyboard=Keyboard();url='https://consent.youtube.com/'
        def is_closed(self):return False
        async def wait_for_timeout(self,ms):pass
    browser=ProviderBrowser();browser.page=Page();browser.started=time.monotonic()
    assert (await browser.scroll(550,490,360))['url']=='https://consent.youtube.com/'
    assert calls[:2]==[('move',(490,360)),('wheel',(0,550))]
    await browser.key('PageDown')
    assert calls[-1]==('key','PageDown')
    with pytest.raises(ValueError):await browser.key('Control+L')


@pytest.mark.asyncio
async def test_scroll_checks_ingress_owner_and_input_limits(monkeypatch):
    import main
    monkeypatch.setattr(main.browser,'page',SimpleNamespace())
    monkeypatch.setattr(main,'browser_session_owner','ha:owner')
    calls=[]
    async def scroll(*args):calls.append(args);return {'ok':True}
    monkeypatch.setattr(main.browser,'scroll',scroll)
    for peer,owner,body,code in [
        ('172.30.32.2','owner',{'x':490,'y':360,'delta_y':550},200),
        ('172.30.32.2','other',{'x':490,'y':360,'delta_y':550},423),
        ('172.30.32.99','owner',{'x':490,'y':360,'delta_y':550},403),
        ('172.30.32.2','owner',{'x':490,'y':360,'delta_y':99999},422),
    ]:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=(peer,123)),base_url='http://ha.test') as client:
            response=await client.post('/api/browser/scroll',headers={'X-Remote-User-Id':owner},json=body)
            assert response.status_code==code
    assert calls==[(550,490,360)]


@pytest.mark.asyncio
async def test_drag_is_private_to_owner(monkeypatch):
    import main
    monkeypatch.setattr(main.browser,'page',SimpleNamespace())
    monkeypatch.setattr(main,'browser_session_owner','ha:owner')
    calls=[]
    async def drag(*args):calls.append(args);return {'ok':True}
    monkeypatch.setattr(main.browser,'drag',drag)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('172.30.32.2',123)),base_url='http://ha.test') as client:
        body={'x':20,'y':100,'end_x':300,'end_y':100}
        assert (await client.post('/api/browser/drag',headers={'X-Remote-User-Id':'other'},json=body)).status_code==423
        assert (await client.post('/api/browser/drag',headers={'X-Remote-User-Id':'owner'},json=body)).status_code==200
    assert calls==[(20,100,300,100)]
