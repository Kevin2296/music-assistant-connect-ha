"""One-tap 'Koppel met Music Assistant' in a real browser with a mock HA ingress and MA."""
from pathlib import Path
from playwright.sync_api import sync_playwright

site=Path(__file__).parents[1]/'app'/'static'
with sync_playwright() as p:
    try:
        browser=p.chromium.launch(headless=True)
    except Exception:
        browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':390,'height':844})
    errors=[];linked=[];ma_calls=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    prefix='/api/hassio_ingress/connect-session/'
    ma_ingress='/api/hassio_ingress/ma-session-1/'
    def serve(route):
        path=route.request.url.split('https://ha.test')[1]
        if path==ma_ingress+'api':
            body=route.request.post_data_json
            ma_calls.append(body)
            assert body['command']=='auth/token/create' and body['args']=={'name':'Music Assistant Connect'}
            route.fulfill(json='new-long-lived-token')
            return
        assert path.startswith(prefix),path
        path=path[len(prefix):]
        if path=='api/settings':
            route.fulfill(json={'configured':bool(linked),'ma_url':'http://172.30.32.1:8095','ma_ui_url':'/hassio/ingress/d5369777_music_assistant','ma_ingress':ma_ingress,'ma_state':'started','user_name':'Oma'})
        elif path=='api/link':
            linked.append(route.request.post_data_json['token'])
            route.fulfill(json={'ok':True,'saved':True})
        elif path=='api/ma':
            assert 'token' not in route.request.post_data_json
            route.fulfill(json={'data':[]})
        else:
            file=site/(path or 'index.html')
            types={'.html':'text/html','.js':'text/javascript','.css':'text/css'}
            route.fulfill(body=file.read_bytes(),content_type=types[file.suffix])
    page.route('**/*',serve)
    page.goto('https://ha.test'+prefix)
    button=page.get_by_role('button',name='Koppel met Music Assistant')
    button.wait_for()
    assert not page.locator('#manual-connection').evaluate('d=>d.open')
    assert page.locator('#ma-url').input_value()=='http://172.30.32.1:8095'
    button.click()
    page.get_by_text('Gekoppeld.',exact=False).wait_for()
    page.get_by_text('Verbonden',exact=True).wait_for()
    assert linked==['new-long-lived-token'] and len(ma_calls)==1
    assert page.locator('#auto-link').is_hidden()
    assert 'new-long-lived-token' not in page.content()
    assert not errors,errors
    browser.close()
print('One-tap link smoke passed (mock HA ingress and Music Assistant, no real credentials).')
