import asyncio

import httpx
import pytest


@pytest.mark.asyncio
async def test_private_cookie_bridge_requires_nonce_and_rejects_web_origins():
    from manual_browser import ManualBrowser
    browser=ManualBrowser()
    browser.server=await asyncio.start_server(browser._bridge,'127.0.0.1',0)
    port=browser.server.sockets[0].getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    try:
        async with httpx.AsyncClient(trust_env=False) as client:
            assert (await client.get(base+'/wrong')).status_code==403
            assert (await client.get(base+'/'+browser.nonce,headers={'Origin':'https://music.youtube.com'})).status_code==403
            assert not browser.ready.is_set()
            response=await client.get(base+'/'+browser.nonce,headers={'Origin':'chrome-extension://test'})
            assert response.json()=={'capture':False}
            assert 'access-control-allow-origin' not in response.headers
            browser.pending=asyncio.get_running_loop().create_future()
            await client.post(base+'/'+browser.nonce,json={'values':{'cookie':'fixture-only'}})
            assert (await browser.pending)['values']['cookie']=='fixture-only'
    finally:
        await browser.close()
