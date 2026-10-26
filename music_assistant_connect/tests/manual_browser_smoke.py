"""Linux production path: manual desktop and real cookie extension, synthetic data only."""
import asyncio
import os
from pathlib import Path
import shutil
import sys
import urllib.parse
import io
from PIL import Image

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
    fixture='''<title>Manual fixture</title><input style="position:absolute;left:20px;top:20px;width:300px;height:40px;background:red;border:0" oninput="document.title=this.value"><input type="range" min="0" max="100" value="0" style="position:absolute;left:20px;top:120px;width:300px;height:40px" oninput="document.title='range'+this.value">'''
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
        # Browser chrome/infobars may shift the page. Locate the red test input
        # in the actual desktop image instead of assuming a fixed content offset.
        image=Image.open(io.BytesIO(await browser.screenshot())).convert('RGB')
        pixels=image.load()
        points=[(x,y) for y in range(image.height) for x in range(image.width) if pixels[x,y][0]>200 and pixels[x,y][1]<60 and pixels[x,y][2]<60]
        assert points, 'Fixture not visible; focused window: '+repr(await title(native.env))
        counts={}
        for x,y in points:counts[y]=counts.get(y,0)+1
        rows=[y for y,count in counts.items() if count>200]
        assert rows, 'Large red fixture input not visible'
        top=min(rows)
        left=min(x for x,y in points if y==top+10)
        await browser.click(left+40,top+20)
        # Repeating a click without moving the pointer must not wait for movement.
        for _ in range(4):
            await asyncio.wait_for(browser.click(left+40,top+20),2)
        await asyncio.wait_for(browser.scroll(100,left+40,top+20),2)
        await browser.type_text('manual-fixture-input')
        for _ in range(20):
            actual=await title(native.env)
            if 'manual-fixture-input' in actual:break
            await asyncio.sleep(.1)
        assert 'manual-fixture-input' in actual,(repr(actual),left,top)
        await browser.drag(left+10,top+120,left+280,top+120)
        actual=await title(native.env)
        assert 'range' in actual,repr(actual)
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
