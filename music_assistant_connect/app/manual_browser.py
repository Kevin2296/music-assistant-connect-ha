"""Human-operated Chromium desktop plus an opt-in, session-local cookie extension.

No WebDriver, DevTools connection, fingerprint overrides, or automatic sign-in.
Profiles and extension configuration live in /dev/shm and are removed on close.
"""
from __future__ import annotations

import asyncio
import io
import json
import math
import logging
import os
from pathlib import Path
import secrets
import shutil
import signal
import tempfile
from urllib.parse import urlsplit, urlunsplit

from PIL import Image
from Xlib import display, X

KEYS = {'Enter':'Return','Tab':'Tab','Escape':'Escape','Backspace':'BackSpace',
        'ArrowDown':'Down','ArrowUp':'Up','PageDown':'Next','PageUp':'Prior',
        'Home':'Home','End':'End'}
PROVIDERS = {'ytmusic':'https://music.youtube.com/',
             'soundcloud':'https://soundcloud.com/', 'deezer':'https://www.deezer.com/'}


HINTS = {'authorization':'log in bij SoundCloud (Sign in, rechtsboven)',
         'client_id':'speel een nummer af of zoek iets, zodat SoundCloud zijn Client ID laadt',
         'cookie':'log in bij YouTube Music (Inloggen, rechtsboven) en open daarna Bibliotheek',
         'arl':'log in bij Deezer'}
LABELS = {'authorization':'OAuth-token','client_id':'Client ID','cookie':'aanmeldcookie','arl':'ARL'}


def missing_message(provider, values):
    """Tell the user which value is still missing and what to do; never echo values."""
    allowed = {'ytmusic':('cookie',),'soundcloud':('authorization','client_id'),'deezer':('arl',)}[provider]
    missing = [k for k in allowed if not values.get(k)]
    if provider == 'ytmusic' and not missing and '__Secure-3PAPISID=' not in values.get('cookie',''):
        missing = ['cookie']
    if not missing:
        return ''
    return ('Nog niet gevonden: ' + ', '.join(LABELS[k] for k in missing) + '. Volgende stap: '
            + '; '.join(HINTS[k] for k in missing) + '. Kies daarna opnieuw Haal mijn gegevens op.')


class ManualBrowser:
    def __init__(self):
        self.process = None
        self.server = None
        self.profile = None
        self.screen = None
        self.env = {}
        self.viewport = {'width':980,'height':720}
        self.provider = ''
        self.current_url = ''
        self.navigation = None
        self.nonce = secrets.token_urlsafe(32)
        self.pending = None
        self.ready = asyncio.Event()
        self.lock = asyncio.Lock()

    async def start(self, provider, executable, env, viewport):
        self.provider = provider
        self.current_url = PROVIDERS[provider]
        self.env = env
        self.viewport = viewport
        self.profile = tempfile.TemporaryDirectory(prefix='ma-connect-',dir='/dev/shm')
        root = Path(self.profile.name)
        extension = root/'extension'
        shutil.copytree(Path(__file__).parent/'cookie_extension',extension)
        manifest_path=extension/'manifest.json'
        manifest=json.loads(manifest_path.read_text())
        domain={'ytmusic':'youtube.com','soundcloud':'soundcloud.com','deezer':'deezer.com'}[provider]
        manifest['host_permissions']=[f'https://*.{domain}/*','http://127.0.0.1/*']
        if provider!='soundcloud':manifest['permissions'].remove('webRequest')
        manifest_path.write_text(json.dumps(manifest))
        self.server = await asyncio.start_server(self._bridge,'127.0.0.1',0,limit=70000)
        port = self.server.sockets[0].getsockname()[1]
        config = {'bridge':f'http://127.0.0.1:{port}/{self.nonce}', 'provider':provider}
        (extension/'config.js').write_text('const CONFIG = '+json.dumps(config)+';',encoding='utf-8')
        self.process = await asyncio.create_subprocess_exec(
            executable, '--no-first-run', '--no-default-browser-check',
            '--no-sandbox', '--disable-dev-shm-usage',
            '--disable-background-timer-throttling',
            '--disk-cache-size=1048576', '--media-cache-size=1048576',
            f'--user-data-dir={root / "profile"}',
            f'--disable-extensions-except={extension}', f'--load-extension={extension}',
            '--kiosk', PROVIDERS[provider],
            env=env, stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )
        await asyncio.wait_for(self.ready.wait(),timeout=25)
        self.screen = await asyncio.to_thread(display.Display,env['DISPLAY'])
        return {'ready':True,'provider':provider,'page':PROVIDERS[provider],
                'viewport':viewport,'mode':'manual'}

    async def _bridge(self, reader, writer):
        """Private loopback-only extension channel; nonce required on every request."""
        status = '403 Forbidden'
        result = {'error':'Forbidden'}
        try:
            raw = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'),5)
            lines = raw.decode('ascii').split('\r\n')
            method,path,_ = lines[0].split(' ')
            headers = dict(line.lower().split(':',1) for line in lines[1:] if ':' in line)
            length = int(headers.get('content-length','0').strip())
            origin = headers.get('origin','').strip()
            valid = path == '/' + self.nonce and (not origin or origin.startswith('chrome-extension://'))
            if valid and 0 <= length <= 65536 and method in ('GET','POST'):
                status = '200 OK'
                if method == 'GET':
                    self.ready.set()
                    result = {'capture':self.pending is not None and not self.pending.done()}
                    if self.navigation:
                        result['navigate']=self.navigation
                        self.navigation=None
                else:
                    body = await asyncio.wait_for(reader.readexactly(length),5)
                    data = json.loads(body)
                    if isinstance(data,dict) and data.get('kind')=='status':
                        address=urlsplit(str(data.get('url',''))[:4096])
                        if address.scheme in ('http','https'):
                            self.current_url=urlunsplit((address.scheme,address.netloc,address.path,'',''))
                    elif self.pending is not None and not self.pending.done():
                        self.pending.set_result(data)
                    result = {'ok':True}
        except (ValueError,UnicodeError,asyncio.TimeoutError,asyncio.IncompleteReadError,asyncio.LimitOverrunError):
            status = '400 Bad Request'
            result = {'error':'Invalid request'}
        finally:
            body = json.dumps(result).encode()
            writer.write(f'HTTP/1.1 {status}\r\nContent-Type: application/json\r\nCache-Control: no-store\r\nConnection: close\r\nContent-Length: {len(body)}\r\n\r\n'.encode()+body)
            try:
                await writer.drain()
            except ConnectionError:
                pass
            writer.close()
            await writer.wait_closed()

    def ensure_live(self):
        if self.process is None or self.process.returncode is not None:
            raise RuntimeError('De gewone browser is gesloten. Start een nieuwe sessie.')

    @property
    def url(self):return self.current_url

    def is_closed(self):return self.process is None or self.process.returncode is not None

    async def _input(self,*args,text=None):
        self.ensure_live()
        process = await asyncio.create_subprocess_exec('xdotool',*args,env=self.env,
            stdin=asyncio.subprocess.PIPE if text is not None else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
        try:
            await asyncio.wait_for(process.communicate(text.encode() if text is not None else None),max(10,len(text or '')*.02))
        except asyncio.TimeoutError:
            process.kill();await process.wait()
            logging.getLogger('uvicorn.error').warning('Browser control timeout: action=%s',args[0])
            raise RuntimeError('De browser reageerde niet op de bediening.') from None
        if process.returncode:
            raise RuntimeError('De browserbediening is mislukt.')

    def _point(self,x,y):
        return str(round(max(0,min(self.viewport['width']-1,x)))),str(round(max(0,min(self.viewport['height']-1,y))))

    async def click(self,x,y):
        async with self.lock:
            await self._input('mousemove',*self._point(x,y),'click','1')
        return {'ok':True}

    async def drag(self,x,y,end_x,end_y):
        async with self.lock:
            await self._input('mousemove',*self._point(x,y),'mousedown','1')
            try:
                for step in range(1,13):
                    await self._input('mousemove',*self._point(x+(end_x-x)*step/12,y+(end_y-y)*step/12))
                    await asyncio.sleep(.025)
            finally:
                await self._input('mouseup','1')
        return {'ok':True}

    async def type_text(self,value):
        async with self.lock:
            # Input goes over stdin, never process arguments or shell interpolation.
            await self._input('type','--clearmodifiers','--file','-',text=value)
        return {'ok':True}

    async def key(self,value):
        if value not in KEYS:raise ValueError('Onbekende toets.')
        async with self.lock:await self._input('key',KEYS[value])
        return {'ok':True}

    async def scroll(self,delta_y,x,y):
        async with self.lock:
            await self._input('mousemove',*self._point(x,y),'click','--repeat',str(min(15,max(1,math.ceil(abs(delta_y)/100)))),'--delay','20','5' if delta_y>0 else '4')
        return {'ok':True}

    async def reload(self):
        async with self.lock:await self._input('key','ctrl+r')
        return {'ok':True}

    async def home(self):
        self.ensure_live()
        self.navigation=PROVIDERS[self.provider]
        return {'ok':True}

    def _image(self):
        width,height=self.viewport['width'],self.viewport['height']
        raw=self.screen.screen().root.get_image(0,0,width,height,X.ZPixmap,0xffffffff)
        image=Image.frombytes('RGB',(width,height),raw.data,'raw','BGRX')
        output=io.BytesIO();image.save(output,format='JPEG',quality=67)
        return output.getvalue()

    async def screenshot(self):
        async with self.lock:
            self.ensure_live()
            return await asyncio.to_thread(self._image)

    async def extract(self):
        async with self.lock:
            self.ensure_live()
            self.pending=asyncio.get_running_loop().create_future()
            try:
                data=await asyncio.wait_for(self.pending,8)
            except asyncio.TimeoutError:
                return {'found':False,'values':{},'message':'De cookiehulp reageert niet. Start de browsersessie opnieuw.'}
            finally:
                self.pending=None
            values=data.get('values',{}) if isinstance(data,dict) else {}
            if not isinstance(values,dict):values={}
            allowed={'ytmusic':{'cookie'},'soundcloud':{'authorization','client_id'},'deezer':{'arl'}}[self.provider]
            values={k:v for k,v in values.items() if k in allowed and isinstance(v,str) and 0<len(v)<=60000}
            missing=missing_message(self.provider,values)
            if self.provider=='ytmusic' and missing:values={}
            return {'found':not missing,'values':values,'message':missing or 'Gegevens gevonden.'}

    async def close(self):
        if self.pending and not self.pending.done():self.pending.cancel()
        if self.server:
            self.server.close();await self.server.wait_closed();self.server=None
        if self.screen:
            self.screen.close();self.screen=None
        if self.process:
            process=self.process;self.process=None
            if process.returncode is None:
                try:os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                try:await asyncio.wait_for(process.wait(),5)
                except asyncio.TimeoutError:
                    try:os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    await process.wait()
        if self.profile:
            self.profile.cleanup();self.profile=None
