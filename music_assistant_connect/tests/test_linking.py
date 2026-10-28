"""One-tap MA linking, Supervisor discovery and provider hints (0.6.0)."""
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import startup
import supervisor
from main import app
from manual_browser import missing_message

SUPERVISOR = ('172.30.32.2', 49500)
# Tests below replace httpx.AsyncClient towards MA; keep the real one for test clients.
RealClient = httpx.AsyncClient
MA = {'slug': 'd5369777_music_assistant', 'state': 'started', 'ingress_url': '/api/hassio_ingress/abcdEFGH1234/'}


def ingress_client():
    return RealClient(transport=httpx.ASGITransport(app=app, client=SUPERVISOR), base_url='https://home.example')


def fake_supervisor(monkeypatch, handler):
    requests = []
    def record(request):
        requests.append(request)
        return handler(request)
    monkeypatch.setattr(supervisor, '_client', lambda timeout=8: RealClient(transport=httpx.MockTransport(record)))
    monkeypatch.setattr(supervisor, 'TOKEN', 'supervisor-secret')
    monkeypatch.setattr(supervisor, '_cache', None)
    return requests


class FakeMA:
    """Stands in for httpx.AsyncClient towards MA's /api."""
    calls = []
    status = 200
    def __init__(self, **kwargs): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def post(self, url, *, json, headers):
        FakeMA.calls.append((url, json['command'], headers['Authorization']))
        return SimpleNamespace(status_code=FakeMA.status, raise_for_status=lambda: None, json=lambda: [])


@pytest.fixture
def linked(monkeypatch):
    import main
    FakeMA.calls = []
    FakeMA.status = 200
    saved = []
    async def save(options):
        saved.append(options)
        return True
    async def find(use_cache=True): return MA
    monkeypatch.setattr(main, 'APP_OPTIONS', {'ma_url': '', 'ma_token': '', 'ma_ui_url': ''})
    monkeypatch.setattr(main.httpx, 'AsyncClient', FakeMA)
    monkeypatch.setattr(supervisor, 'save_own_options', save)
    monkeypatch.setattr(supervisor, 'find_music_assistant', find)
    return saved


@pytest.mark.asyncio
async def test_settings_fill_in_ma_address_and_offer_one_tap_link(linked):
    async with ingress_client() as c:
        data = (await c.get('/api/settings', headers={'X-Remote-User-Display-Name': 'Oma'})).json()
    assert data == {'configured': False, 'ma_url': 'http://172.30.32.1:8095',
                    'ma_ui_url': '/hassio/ingress/d5369777_music_assistant',
                    'ma_ingress': MA['ingress_url'], 'ma_state': 'started', 'user_name': 'Oma'}


@pytest.mark.asyncio
async def test_link_verifies_and_stores_token_without_echoing_it(linked):
    import main
    async with ingress_client() as c:
        result = await c.post('/api/link', json={'token': 'fresh-ma-token-123'})
        assert result.status_code == 200
        assert result.json() == {'ok': True, 'saved': True}
        assert 'fresh-ma-token-123' not in result.text
        assert FakeMA.calls == [('http://172.30.32.1:8095/api', 'config/providers', 'Bearer fresh-ma-token-123')]
        assert linked == [{'ma_url': 'http://172.30.32.1:8095', 'ma_token': 'fresh-ma-token-123',
                           'ma_ui_url': '/hassio/ingress/d5369777_music_assistant'}]
        assert main.options()['ma_token'] == 'fresh-ma-token-123'
        settings = await c.get('/api/settings')
        assert settings.json()['configured'] is True
        assert 'fresh-ma-token-123' not in settings.text
        # Later proxy calls use the stored token, never one sent by the page.
        FakeMA.calls = []
        await c.post('/api/ma', json={'url': 'http://192.168.1.66:8095', 'token': 'page-token', 'command': 'config/providers', 'args': {}})
        assert FakeMA.calls == [('http://172.30.32.1:8095/api', 'config/providers', 'Bearer fresh-ma-token-123')]


@pytest.mark.asyncio
async def test_link_rejects_token_ma_refuses(linked):
    import main
    FakeMA.status = 401
    async with ingress_client() as c:
        result = await c.post('/api/link', json={'token': 'rejected-token-1'})
    assert result.status_code == 401
    assert linked == []
    assert main.options()['ma_token'] == ''


@pytest.mark.asyncio
async def test_link_requires_ingress(linked):
    outside = httpx.ASGITransport(app=app, client=('172.30.33.5', 1))
    async with RealClient(transport=outside, base_url='https://home.example') as c:
        assert (await c.post('/api/link', json={'token': 'some-token-123'})).status_code == 403
    assert FakeMA.calls == []


@pytest.mark.asyncio
async def test_find_music_assistant_prefers_started_app(monkeypatch):
    infos = {
        'd5369777_music_assistant': {'version': '2.10.8', 'state': 'stopped', 'ingress_url': '/api/hassio_ingress/stableToken1/'},
        'd5369777_music_assistant_beta': {'version': '2.11.0b7', 'state': 'started', 'ingress_url': '/api/hassio_ingress/betaToken12/'},
    }
    def handler(request):
        slug = request.url.path.split('/')[2]
        if slug not in infos:
            return httpx.Response(400, json={'result': 'error'})
        return httpx.Response(200, json={'result': 'ok', 'data': infos[slug]})
    requests = fake_supervisor(monkeypatch, handler)
    found = await supervisor.find_music_assistant()
    assert found == {'slug': 'd5369777_music_assistant_beta', 'state': 'started', 'ingress_url': '/api/hassio_ingress/betaToken12/'}
    assert all(r.headers['authorization'] == 'Bearer supervisor-secret' for r in requests)
    assert [r.url.path for r in requests] == ['/addons/d5369777_music_assistant/info', '/addons/d5369777_music_assistant_beta/info']


@pytest.mark.asyncio
async def test_find_music_assistant_ignores_unexpected_ingress_paths(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={'data': {'version': '1', 'state': 'started', 'ingress_url': 'https://evil.example/x/'}})
    fake_supervisor(monkeypatch, handler)
    assert (await supervisor.find_music_assistant())['ingress_url'] == ''


@pytest.mark.asyncio
async def test_supervisor_lookups_stay_on_known_slugs(monkeypatch):
    requests = fake_supervisor(monkeypatch, lambda r: httpx.Response(200, json={'data': {}}))
    assert await supervisor.app_info('core_ssh') is None
    assert await supervisor.app_info('../self/options') is None
    assert requests == []
    monkeypatch.setattr(supervisor, 'TOKEN', '')
    assert await supervisor.find_music_assistant(use_cache=False) is None
    assert await supervisor.save_own_options({'ma_token': 'x'}) is False


@pytest.mark.asyncio
async def test_save_own_options_goes_through_supervisor(monkeypatch):
    requests = fake_supervisor(monkeypatch, lambda r: httpx.Response(200, json={'result': 'ok'}))
    assert await supervisor.save_own_options({'ma_url': 'http://172.30.32.1:8095', 'ma_token': 'abc12345', 'ma_ui_url': ''})
    assert requests[0].method == 'POST'
    assert str(requests[0].url) == 'http://supervisor/addons/self/options'
    assert b'"options"' in requests[0].content


@pytest.mark.asyncio
async def test_po_token_status(monkeypatch):
    def handler(request):
        if request.url.host == 'supervisor':
            return httpx.Response(200, json={'data': {'version': '2.0.2', 'state': 'started'}})
        assert str(request.url) == 'http://172.30.32.1:4416/ping'
        return httpx.Response(200, json={'server_uptime': 1})
    fake_supervisor(monkeypatch, handler)
    status = await supervisor.po_token_status()
    assert status['installed'] and status['reachable'] and status['state'] == 'started'
    assert status['app_path'] == '/config/app/d5369777_ytm_po_token_generator/info'
    assert status['server_url'] == 'http://127.0.0.1:4416'

    def down(request):
        if request.url.host == 'supervisor':
            return httpx.Response(400, json={'result': 'error'})
        raise httpx.ConnectError('refused')
    fake_supervisor(monkeypatch, down)
    status = await supervisor.po_token_status()
    assert not status['installed'] and not status['reachable']
    assert status['app_path'] == '/config/app/d5369777_ytm_po_token_generator/info?store=true'


@pytest.mark.asyncio
async def test_po_token_status_endpoint_requires_ingress(monkeypatch):
    async def status(): return {'reachable': True}
    monkeypatch.setattr(supervisor, 'po_token_status', status)
    async with ingress_client() as c:
        assert (await c.get('/api/ytmusic/status')).json() == {'reachable': True}
    outside = httpx.ASGITransport(app=app, client=('192.168.1.9', 1))
    async with httpx.AsyncClient(transport=outside, base_url='https://home.example') as c:
        assert (await c.get('/api/ytmusic/status')).status_code == 403


def test_supervisor_token_is_removed_from_environment():
    environ = {'SUPERVISOR_TOKEN': 'sv-secret', 'PATH': '/bin'}
    assert startup.take_supervisor_token(environ) == 'sv-secret'
    assert environ == {'PATH': '/bin'}
    assert startup.take_supervisor_token({'HASSIO_TOKEN': 'legacy'}) == 'legacy'


def test_bootstrap_hands_supervisor_token_to_memory_only(monkeypatch):
    import main
    import uvicorn
    monkeypatch.setattr(main, 'APP_OPTIONS', None)
    monkeypatch.setenv('SUPERVISOR_TOKEN', 'sv-secret')
    monkeypatch.setattr(startup, 'load_options', lambda: {})
    monkeypatch.setattr(startup, 'drop_privileges', lambda: None)
    seen = {}
    def serve(app, **kwargs):
        seen['env'] = os.environ.get('SUPERVISOR_TOKEN')
        seen['token'] = supervisor.TOKEN
    monkeypatch.setattr(uvicorn, 'run', serve)
    monkeypatch.setattr(supervisor, 'TOKEN', '')
    startup.main()
    assert seen == {'env': None, 'token': 'sv-secret'}


def test_missing_values_get_a_concrete_next_step():
    assert missing_message('soundcloud', {'authorization': 'OAuth x', 'client_id': 'A' * 32}) == ''
    only_token = missing_message('soundcloud', {'authorization': 'OAuth x'})
    assert 'Client ID' in only_token and 'speel een nummer af' in only_token and 'OAuth x' not in only_token
    assert 'log in bij SoundCloud' in missing_message('soundcloud', {'client_id': 'A' * 32})
    assert 'YouTube Music' in missing_message('ytmusic', {'cookie': 'PREF=1'})
    assert missing_message('ytmusic', {'cookie': 'SID=1; __Secure-3PAPISID=2'}) == ''
    assert 'Deezer' in missing_message('deezer', {})
