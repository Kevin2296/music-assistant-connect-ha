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
