"""Linux integration: real production browser/display, local consent-like fixture."""
import asyncio
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).parents[1]/'app'))
from browser import ProviderBrowser, PROVIDER_URLS


async def run():
    os.environ.pop('DISPLAY',None)
    b=ProviderBrowser(use_manual=False)
    # Stay offline: start the real browser on about:blank, then load a fixture.
    PROVIDER_URLS['ytmusic']='about:blank'
    try:
        await b.start('ytmusic')
        assert b.display_process and b.display_process.returncode is None
        display=b.display_process
        ua=await b.page.evaluate('navigator.userAgent')
        assert 'Chrome/' in ua and 'HeadlessChrome/' not in ua,ua
        await b.page.set_content('''<div id="consent" style="height:650px;overflow:auto"><div style="height:1300px">Consent text</div><button id="choice" onclick="document.body.dataset.chosen='yes'">Choose</button></div>''')
        await b.scroll(1500,490,360)
        await b.page.locator('#choice').wait_for(state='visible')
        box=await b.page.locator('#choice').bounding_box()
        assert 0 <= box['y'] < 650,box
        await b.click(box['x']+box['width']/2,box['y']+box['height']/2)
        assert await b.page.get_attribute('body','data-chosen')=='yes'
        assert len(await b.screenshot())>100
    finally:
        await b.close()
    assert display.returncode is not None
    assert b.page is None and b.display_process is None


asyncio.run(run())
print('Production Chromium with virtual display, nested consent scrolling, click and cleanup passed. No provider login tested.')
