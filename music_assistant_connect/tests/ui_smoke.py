"""Run explicitly with Python; needs a Playwright Chromium install or MS Edge."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

site=Path(__file__).parents[1]/'app'/'static'
with sync_playwright() as p:
    try:
        browser=p.chromium.launch(headless=True)
    except Exception:
        browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':390,'height':844})
    errors=[]
    scrolls=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    prefix='/api/hassio_ingress/test-session/'
    def serve(route):
        path=route.request.url.split('https://ha.test')[1]
        assert path.startswith(prefix),path
        path=path[len(prefix):]
        if path=='api/settings':
            route.fulfill(json={'configured':True,'ma_url':'http://192.168.1.5:8095','ma_ui_url':'/hassio/ingress/ma-test'})
        elif path=='api/ma':
            body=route.request.post_data_json
            assert 'token' not in body
            if body['command']=='config/providers':
                route.fulfill(json={'data':[]})
            elif body['command']=='config/providers/setup':
                route.fulfill(json={'data':{'type':'form','flow_id':'test-flow','result':None,'entries':[{'key':'username','type':'string'},{'key':'cookie','type':'secure_string'}],'last_step':True}})
            else: raise AssertionError(body)
        elif path=='api/browser/start':route.fulfill(json={'ready':True,'page':'https://consent.youtube.com/','viewport':{'width':980,'height':720}})
        elif path=='api/browser/scroll':
            scrolls.append(route.request.post_data_json)
            route.fulfill(json={'ok':True})
        elif path in ('api/browser/drag','api/browser/click'):route.fulfill(json={'ok':True})
        elif path=='api/browser/screenshot':route.fulfill(body='<svg xmlns="http://www.w3.org/2000/svg" width="980" height="720"><text x="10" y="30">Consent page</text></svg>',content_type='image/svg+xml')
        elif path=='api/browser/close':route.fulfill(json={'ok':True})
        else:
            file=site/(path or 'index.html')
            types={'.html':'text/html','.js':'text/javascript','.css':'text/css'}
            route.fulfill(body=file.read_bytes(),content_type=types[file.suffix])
    page.route('**/*',serve)
    page.goto('https://ha.test'+prefix)
    page.get_by_text('Verbinding geslaagd.',exact=False).wait_for()
    assert page.locator('#ma-token').is_disabled()
    assert page.get_by_role('link',name='Open Music Assistant').get_attribute('href')=='https://ha.test/hassio/ingress/ma-test'
    page.get_by_role('button',name='YouTube Music').click()
    page.locator('input[data-key="cookie"]').wait_for()
    page.locator('input[data-key="username"]').fill('example-user')
    page.evaluate("patchExtracted({cookie:'test-cookie'})")
    assert page.locator('input[data-key="username"]').input_value()=='example-user'
    assert page.locator('input[data-key="cookie"]').input_value()=='test-cookie'
    page.get_by_role('button',name='Plak uit klembord').wait_for()
    page.get_by_role('button',name='Gegevens opnieuw ophalen').click()
    with page.expect_request('**/api/browser/scroll') as scroll_request:
        page.get_by_role('button',name='Omlaag scrollen',exact=False).click()
    assert scroll_request.value.post_data_json=={'delta_y':550,'x':490,'y':360}
    with page.expect_request('**/api/browser/screenshot'):
        page.get_by_role('button',name='Beeld verversen').click()
    with page.expect_request('**/api/browser/screenshot',timeout=5000):
        pass  # Periodic image updates continue without clicking another control.
    page.locator('#browser-image').hover()
    with page.expect_request('**/api/browser/scroll') as wheel_request:
        page.mouse.wheel(0,200)
    assert wheel_request.value.post_data_json['delta_y']==200
    box=page.locator('#browser-image').bounding_box()
    page.mouse.move(box['x']+20,box['y']+30)
    page.mouse.down()
    with page.expect_request('**/api/browser/drag') as drag_request:
        page.mouse.move(box['x']+100,box['y']+30,steps=5)
        page.mouse.up()
    assert drag_request.value.post_data_json['end_x']>drag_request.value.post_data_json['x']
    page.locator('#browser-end').click()
    assert not errors,errors
    assert page.evaluate('sessionStorage.getItem("ma-token")') is None
    browser.close()
print('Mobile Ingress UI smoke passed (mock Music Assistant, no real credentials).')
