# Copyright (c) 2012-2015 Carnegie Mellon University.  All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#
# 3. The name "Carnegie Mellon University" must not be used to
#    endorse or promote products derived from this software without
#    prior written permission. For permission or any legal
#    details, please contact
#      Carnegie Mellon University
#      Center for Technology Transfer and Enterprise Creation
#      4615 Forbes Avenue
#      Suite 302
#      Pittsburgh, PA  15213
#      (412) 268-7393, fax: (412) 268-7395
#      innovation@andrew.cmu.edu
#
# 4. Redistributions of any form whatsoever must retain the following
#    acknowledgment:
#    "This product includes software developed by Computing Services
#     at Carnegie Mellon University (http://www.cmu.edu/computing/)."
#
# CARNEGIE MELLON UNIVERSITY DISCLAIMS ALL WARRANTIES WITH REGARD TO
# THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS, IN NO EVENT SHALL CARNEGIE MELLON UNIVERSITY BE LIABLE
# FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN
# AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING
# OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
import basetoken
OAUTH2_AUTH_LABEL = 'Bearer '

class BoxOAuth2Token(basetoken.OAuth2Token):
    """Token object for OAuth 2.0 as described on
    <http://code.google.com/apis/accounts/docs/OAuth2.html>.

    Uses "Bearer" rather than OAuth as HTTP auth scheme"""

    def __init__(self, *args, **kw):
        kw.setdefault("auth_uri", "https://api.box.com/oauth2/authorize")
        kw.setdefault("token_uri", "https://api.box.com/oauth2/token")
        kw.setdefault("revoke_uri", "https://api.box.com/oauth2/revoke")
        super(BoxOAuth2Token, self).__init__(*args, **kw)
        self._dirty=False

    def _refresh(self, *args, **kw):
        ret=super(BoxOAuth2Token, self)._refresh(*args, **kw)
        if not self.invalid:
           self._dirty=True
        return ret

    def get_access_token(self, *args, **kw):
        ret=super(BoxOAuth2Token, self).get_access_token(*args, **kw)
        self._dirty=True
        return ret

    @property
    def dirty(self):
       """True if the credentials have been changed since the object was created."""
       return getattr(self, '_dirty', False)

 
    def modify_request(self, http_request):
        """Sets the Authorization header in the HTTP request using the token.
        
        Returns:
        The same HTTP request object which was passed in.
        """
        super(BoxOAuth2Token, self).modify_request(http_request)
        http_request.headers['Authorization'] = '%s%s' % (OAUTH2_AUTH_LABEL,
                                                          self.access_token)
        return http_request
                
    ModifyRequest = modify_request 
    __call__ = modify_request


def token_to_blob(token):
    if isinstance(token, BoxOAuth2Token):
        return basetoken._join_token_parts(
            '2o', token.client_id, token.client_secret, token.scope,
            token.user_agent, token.auth_uri, token.token_uri,
            token.access_token, token.refresh_token)
    else:
        raise basetoken.UnsupportedTokenType(
            'Unable to serialize token of type %s' % type(token))

def token_from_blob(blob):
    parts = basetoken._split_token_parts(blob)
    
    if parts[0] == '2o':
        return BoxOAuth2Token(parts[1], parts[2], parts[3], parts[4], parts[5],
                           parts[6], parts[7], parts[8])
    else:
        raise UnsupportedTokenType(
            'Unable to deserialize token with type marker of %s' % parts[0])
    
    
TokenFromBlob = token_from_blob

