const {test}=require('node:test');
const assert=require('node:assert/strict');
const h=require('../app/static/helpers.js');
global.location={origin:'https://home.example'};
test('cookie matching never selects PO token or other secret fields',()=>{
  assert.equal(h.match([{key:'po_token'},{key:'cookie_backup'},{key:'cookie'}],'cookie').key,'cookie');
  assert.equal(h.match([{key:'cookie',read_only:true}],'cookie'),undefined);
});
test('manual SoundCloud authorization and Youtube Cookie headers normalize',()=>{
  assert.equal(h.normalize('soundcloud','authorization','abc'),'OAuth abc');
  assert.equal(h.normalize('soundcloud','authorization','Authorization: OAuth abc'),'OAuth abc');
  assert.equal(h.normalize('ytmusic','cookie','Cookie: SID=abc; X=def'),'SID=abc; X=def');
  assert.equal(h.normalize('qobuz','password','  secret  '),'  secret  ');
});
test('remote links use HA panel or HTTPS and never leak tokens',()=>{
  assert.deepEqual(h.links('/hassio/ingress/music'),{home:'https://home.example/hassio/ingress/music'});
  assert.equal(h.links('https://music.example')['providers'],'https://music.example/#/settings/providers');
  assert.deepEqual(h.links('http://192.168.1.5:8095'),{});
});
test('YouTube Music prefill only fills empty fields',()=>{
  const entries=[{key:'username',type:'string'},{key:'cookie',type:'secure_string'},{key:'po_token_server_url',type:'string',default_value:'http://127.0.0.1:4416'}];
  assert.deepEqual(h.prefill('ytmusic',entries,{userName:'Oma',poTokenUrl:'http://127.0.0.1:4416'}),{username:'Oma'});
  assert.deepEqual(h.prefill('ytmusic',[{key:'po_token_server_url',value:''}],{poTokenUrl:'http://127.0.0.1:4416'}),{po_token_server_url:'http://127.0.0.1:4416'});
  assert.deepEqual(h.prefill('ytmusic',[{key:'username',value:'mijn-merk'}],{userName:'Oma'}),{});
  assert.deepEqual(h.prefill('soundcloud',entries,{userName:'Oma'}),{});
});
test('provider refusals are recognised for a plain explanation',()=>{
  assert.match(h.blocked('ytmusic','https://accounts.google.com/v3/signin/rejected'),/Google weigert/);
  assert.equal(h.blocked('ytmusic','https://accounts.google.com/v3/signin/identifier'),'');
  assert.equal(h.blocked('ytmusic','not a url'),'');
  assert.match(h.blocked('soundcloud','https://geo.captcha-delivery.com/captcha/'),/zelf/);
});
