"""Linux production path: manual desktop and real cookie extension, synthetic data only."""
import asyncio
import os
from pathlib import Path
import shutil
import sys
import urllib.parse

import httpx

sys.path.insert(0,str(Path(__file__).parents[1]/'app'))
import manual_browser
from browser import ProviderBrowser


async def title(env):
    process=await asyncio.create_subprocess_exec('xdotool','getwindowfocus','getwindowname',env=env,stdout=asyncio.subprocess.PIPE)
    stdout,_=await process.communicate()
    return stdout.decode()


async def run():
    os.environ.pop('DISPLAY',None)
    fixture='''<title>Manual fixture</title><input style="position:absolute;left:20px;top:20px;width:300px;height:40px" oninput="document.title=this.value"><input type="range" min="0" max="100" value="0" style="position:absolute;left:20px;top:120px;width:300px;height:40px" oninput="document.title='range'+this.value">'''
    manual_browser.PROVIDERS['ytmusic']='data:text/html,'+urllib.parse.quote(fixture)
    original_copy=shutil.copytree
    def copy_extension(source,target,*args,**kwargs):
        result=original_copy(source,target,*args,**kwargs)
        if Path(target).name=='extension':
            script=Path(target)/'bridge.js'
            text=script.read_text().replace('poll();',"chrome.cookies.set({url:'https://music.youtube.com/',name:'__Secure-3PAPISID',value:'synthetic-test-cookie',secure:true,httpOnly:true}).then(()=>poll());")
            script.write_text(text)
        return result
    manual_browser.shutil.copytree=copy_extension
    browser=ProviderBrowser()
    native=None
    try:
        info=await browser.start('ytmusic')
        assert info['mode']=='manual'
        native=browser.native
        profile=Path(native.profile.name)
        assert str(profile).startswith('/dev/shm/')
        args=Path(f'/proc/{native.process.pid}/cmdline').read_bytes()
        assert b'--remote-debugging' not in args and b'--enable-automation' not in args
        async with httpx.AsyncClient(trust_env=False) as client:
            port=native.server.sockets[0].getsockname()[1]
            assert (await client.get(f'http://127.0.0.1:{port}/wrong')).status_code==403
        await asyncio.sleep(1)
        await browser.click(60,40)
        await browser.type_text('manual-fixture-input')
        assert 'manual-fixture-input' in await title(native.env)
        await browser.drag(30,140,300,140)
        assert 'range' in await title(native.env)
        assert (await browser.screenshot()).startswith(b'\xff\xd8')
        result=await browser.extract()
        assert result['found'] is True
        assert '__Secure-3PAPISID=synthetic-test-cookie' in result['values']['cookie']
        assert browser.native is None
        assert not profile.exists()
    finally:
        await browser.close()
        manual_browser.shutil.copytree=original_copy
    assert native.server is None and native.process is None


asyncio.run(run())
print('Manual Chromium, human input relay, real extension with synthetic cookie, private bridge and RAM-profile cleanup passed. No Google/SoundCloud login or CAPTCHA completion tested.')
