'use strict';
const CredentialHelpers = {
  aliases: {cookie:['cookie','login_cookie'], arl:['arl','arl_token'], authorization:['authorization','oauth_token'], client_id:['client_id']},
  normalize(provider, key, value) {
    if (typeof value !== 'string') return value;
    if (!value.trim()) return value;
    if (provider === 'soundcloud' && ['authorization','oauth_token'].includes(key.toLowerCase())) {
      return value.trim().replace(/^(?:authorization\s*:\s*)?(?:oauth\s+)?/i, 'OAuth ');
    }
    if (provider === 'ytmusic' && ['cookie','login_cookie'].includes(key.toLowerCase())) {
      return value.trim().replace(/^cookie\s*:\s*/i, '');
    }
    return value;
  },
  match(entries, field) {
    const keys = this.aliases[field] || [field];
    return entries.find(e => !e.hidden && !e.read_only && keys.includes(e.key?.toLowerCase()));
  },
  prefill(provider, entries, context = {}) {
    // Only fill fields that are still empty; never overwrite what MA or the user entered.
    const out = {};
    for (const entry of entries || []) {
      const key = (entry.key || '').toLowerCase();
      if (entry.hidden || entry.read_only || String(entry.value ?? entry.default_value ?? '').trim()) continue;
      if (provider === 'ytmusic' && key === 'username' && context.userName) out[entry.key] = context.userName;
      if (provider === 'ytmusic' && key === 'po_token_server_url' && context.poTokenUrl) out[entry.key] = context.poTokenUrl;
    }
    return out;
  },
  blocked(provider, address) {
    // Recognise a provider refusing this server browser so we can say so plainly.
    let url;
    try { url = new URL(address); } catch { return ''; }
    if (provider === 'ytmusic' && url.hostname === 'accounts.google.com' && /\/rejected\b/.test(url.pathname)) {
      return 'Google weigert inloggen in deze serverbrowser. Dit is een beveiliging van Google; deze app omzeilt die niet. Probeer het later nog eens, of koppel YouTube Music eenmalig volgens de handleiding op een computer. Zonder computer: kies een dienst met officiële koppeling, zoals Spotify of Tidal.';
    }
    if (url.hostname.endsWith('captcha-delivery.com') || /\/captcha\b/i.test(url.pathname)) {
      return 'De dienst vraagt een extra controle. Voltooi die zelf in het beeld; deze app lost geen controles voor je op.';
    }
    return '';
  },
  links(base) {
    if (!base) return {};
    const url = new URL(base, location.origin);
    if (url.origin !== location.origin && url.protocol !== 'https:') return {};
    const root = url.href.split('#')[0].replace(/\/$/, '');
    // HA panel navigation is owned by HA. Open its panel instead of appending MA routes.
    if (url.origin === location.origin && url.pathname.startsWith('/hassio/ingress/')) return {home:root};
    return {home:root, providers:root+'/#/settings/providers', profile:root+'/#/settings/profile', api:root+'/api-docs'};
  }
};
if (typeof module !== 'undefined') module.exports = CredentialHelpers;
