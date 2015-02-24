#!/usr/bin/env python
# Copyright (C) 2002-2014 Carnegie Mellon University
# derived from gdata/gauth.py in Google's gdata-python-client package
#
# Copyright (C) 2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# This module is used for version 2 of the Google Data APIs.


"""Provides auth related token classes and functions for Google Data APIs.

Token classes represent a user's authorization of this app to access their
data. 

Unlike the original version this uses requests as the http framework
and only includes OAuth2 support
"""


import datetime
import time
import random
import urllib
import urlparse
import requests
import requests.cookies

import json
from urlparse import parse_qsl

__author__ = 'j.s@google.com (Jeff Scudder)'


OAUTH2_AUTH_LABEL = 'OAuth '


class Error(Exception):
  pass


class UnsupportedTokenType(Error):
  """Raised when token to or from blob is unable to convert the token."""
  pass


class OAuth2AccessTokenError(Error):
  """Raised when an OAuth2 error occurs."""
  def __init__(self, error_message):
    self.error_message = error_message


class OAuth2RevokeError(Error):
  """Raised when an OAuth2 token revocation was unsuccessful."""

  def __init__(self, http_response):
    """Sets the HTTP information in the error.

    Args:
      http_response: The response from the server, contains error information.
      response_body: string (optional) specified if the response has already
                     been read from the http_response object.
    """
    self.status = http_response.status_code
    self.reason = http_response.raw.reason
    self.body = http_response.text
    self.headers = http_response.headers

    self.error_msg = 'Invalid response %s.' % self.status
    try:
      json_from_body = http_response.json()
      if isinstance(json_from_body, dict):
        self.error_msg = json_from_body.get('error', self.error_msg)
    except (ValueError, JSONDecodeError):
      pass

  def __str__(self):
    return 'OAuth2RevokeError(status=%i, error=%s)' % (self.status,
                                                       self.error_msg)


class OAuth2Token(requests.auth.AuthBase):
  """Token object for OAuth 2.0 as described on
  <http://code.google.com/apis/accounts/docs/OAuth2.html>.

  Token can be applied to a gdata.client.GDClient object using the authorize()
  method, which then signs each request from that object with the OAuth 2.0
  access token.
  This class supports 3 flows of OAuth 2.0:
    Client-side web flow: call generate_authorize_url with `response_type='token''
      and the registered `redirect_uri'.
    Server-side web flow: call generate_authorize_url with the registered
      `redirect_url'.
    Native applications flow: call generate_authorize_url as it is. You will have
      to ask the user to go to the generated url and pass in the authorization
      code to your application.
  """

  def __init__(self, client_id, client_secret, scope, user_agent,
      auth_uri='https://accounts.google.com/o/oauth2/auth',
      token_uri='https://accounts.google.com/o/oauth2/token',
      access_token=None, refresh_token=None,
      revoke_uri='https://accounts.google.com/o/oauth2/revoke'):
    """Create an instance of OAuth2Token

    This constructor is not usually called by the user, instead
    OAuth2Credentials objects are instantiated by the OAuth2WebServerFlow.

    Args:
      client_id: string, client identifier.
      client_secret: string client secret.
      scope: string, scope of the credentials being requested.
      user_agent: string, HTTP User-Agent to provide for this application. (
      auth_uri: string, URI for authorization endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      token_uri: string, URI for token endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      revoke_uri: string, URI for revoke endpoint. For convenience
        defaults to Google's endpoints but any OAuth 2.0 provider can be used.
      access_token: string, access token.
      refresh_token: string, refresh token.
    """
    self.client_id = client_id
    self.client_secret = client_secret
    self.scope = scope
    self.user_agent = user_agent
    self.auth_uri = auth_uri
    self.token_uri = token_uri
    self.revoke_uri = revoke_uri
    self.access_token = access_token
    self.refresh_token = refresh_token
    headers = {
      'user-agent': self.user_agent,
    }
    #self.session=requests.session(headers=headers)
    self.session=requests.session()
    self.session.headers=headers
    # True if the credentials have been revoked or expired and can't be
    # refreshed.
    self._invalid = False

  @property
  def invalid(self):
    """True if the credentials are invalid, such as being revoked."""
    return getattr(self, '_invalid', False)

  def _refresh(self):
    """Refresh the access_token using the refresh_token.

    Args:
       http: An instance of httplib2.Http.request
           or something that acts like it.
    """
    args={
      'grant_type': 'refresh_token',
      'client_id': self.client_id,
      'client_secret': self.client_secret,
      'refresh_token' : self.refresh_token
      }
    headers = {
        'user-agent': self.user_agent,
    }

    response=self.session.post(self.token_uri, data=args)
    if response:
      self._extract_tokens(response.json())
    else:
      self._invalid = True
    return response

  def _extract_tokens(self, d):
    self.access_token = d['access_token']
    self.refresh_token = d.get('refresh_token', self.refresh_token)
    if 'expires_in' in d:
      self.token_expiry = datetime.timedelta(
          seconds = int(d['expires_in'])) + datetime.datetime.now()
    else:
      self.token_expiry = None

  def generate_authorize_url(self, redirect_uri='oob', response_type='code',
                             access_type='offline', **kwargs):
    """Returns a URI to redirect to the provider.

    Args:
      redirect_uri: Either the string 'oob' for a non-web-based application, or
                    a URI that handles the callback from the authorization
                    server.
      response_type: Either the string 'code' for server-side or native
                     application, or the string 'token' for client-side
                     application.
      access_type: Either the string 'offline' to request a refresh token or
                   'online'.

    If redirect_uri is 'oob' then pass in the
    generated verification code to get_access_token,
    otherwise pass in the query parameters received
    at the callback uri to get_access_token.
    If the response_type is 'token', no need to call
    get_access_token as the API will return it within
    the query parameters received at the callback:
      oauth2_token.access_token = YOUR_ACCESS_TOKEN
    """
    self.redirect_uri = redirect_uri
    query = {
      'response_type': response_type,
      'client_id': self.client_id,
      'redirect_uri': redirect_uri,
      'scope': self.scope,
      'access_type': access_type
      }
    query.update(kwargs)
    parts = list(urlparse.urlparse(self.auth_uri))
    query.update(dict(parse_qsl(parts[4]))) # 4 is the index of the query part
    parts[4] = urllib.urlencode(query)
    return urlparse.urlunparse(parts)

  def get_access_token(self, code):
    """Exhanges a code for an access token.

    Args:
      code: string or dict, either the code as a string, or a dictionary
        of the query parameters to the redirect_uri, which contains
        the code.
    """

    if not (isinstance(code, str) or isinstance(code, unicode)):
      code = code['code']

    args={
      'grant_type': 'authorization_code',
      'client_id': self.client_id,
      'client_secret': self.client_secret,
      'code': code,
      'redirect_uri': self.redirect_uri,
      'scope': self.scope
      }
    response=self.session.post(self.token_uri, data=args)
    if response:
      self._extract_tokens(response.json())
      return self
    else:
      error_msg = 'Invalid response %s.' % response.status_code
      try:
        d = response.json
        if 'error' in d:
          error_msg = d['error']
      except:
        pass
      raise OAuth2AccessTokenError(error_msg)

  def revoke(self, revoke_uri=None, refresh_token=None):
    """Revokes access via a refresh token.

    Args:
      revoke_uri: string, URI for revoke endpoint. If not provided, or if
        None is provided, the revoke_uri attribute on the object is used.
      refresh_token: string, refresh token. If not provided, or if None is
        provided, the refresh_token attribute on the object is used.

    Raises:
      UnsupportedTokenType if the token is not one of the supported token
      classes listed above.

    Example:
      >>> token.revoke()
    """
    base_revoke_uri = revoke_uri or self.revoke_uri
    token = refresh_token or self.refresh_token or self.access_token

    response=self.session.get(base_revoke_uri, params={'token': token})
    if not response:
      raise OAuth2RevokeError(response)
    else:
      self._invalid = True

  def handle_401(self, r, **kwargs):
    r.request.deregister_hook('response', self.handle_401)
    if r.status_code == 401 and not self.invalid:
       self._refresh()
       if not self.invalid:
          r.content
          r.raw.release_conn()
          prep = r.request.copy()
          requests.cookies.extract_cookies_to_jar(prep._cookies, r.request, r.raw)
          prep.prepare_cookies(prep._cookies)
          self.modify_request(prep)
          prep.deregister_hook('response', self.handle_401)
          _r = r.connection.send(prep, **kwargs)
          _r.history.append(r)
          return _r   
    return r


  def modify_request(self, http_request):
    """Sets the Authorization header in the HTTP request using the token.

    Returns:
      The same HTTP request object which was passed in.
    """
    http_request.headers['Authorization'] = '%s%s' % (OAUTH2_AUTH_LABEL,
                                                      self.access_token)
    http_request.register_hook('response', self.handle_401)
    return http_request

  ModifyRequest = modify_request
  __call__ = modify_request


def _join_token_parts(*args):
  """"Escapes and combines all strings passed in.

  Used to convert a token object's members into a string instead of
  using pickle.

  Note: A None value will be converted to an empty string.

  Returns:
    A string in the form 1x|member1|member2|member3...
  """
  return '|'.join([urllib.quote_plus(a or '') for a in args])


def _split_token_parts(blob):
  """Extracts and unescapes fields from the provided binary string.

  Reverses the packing performed by _join_token_parts. Used to extract
  the members of a token object.

  Note: An empty string from the blob will be interpreted as None.

  Args:
    blob: str A string of the form 1x|member1|member2|member3 as created
        by _join_token_parts

  Returns:
    A list of unescaped strings.
  """
  return [urllib.unquote_plus(part) or None for part in blob.split('|')]


def token_to_blob(token):
  """Serializes the token data as a string for storage in a datastore.

  Supported token classes: ClientLoginToken, AuthSubToken, SecureAuthSubToken,
  OAuthRsaToken, and OAuthHmacToken, TwoLeggedOAuthRsaToken,
  TwoLeggedOAuthHmacToken and OAuth2Token.

  Args:
    token: A token object which must be of one of the supported token classes.

  Raises:
    UnsupportedTokenType if the token is not one of the supported token
    classes listed above.

  Returns:
    A string represenging this token. The string can be converted back into
    an equivalent token object using token_from_blob. Note that any members
    which are set to '' will be set to None when the token is deserialized
    by token_from_blob.
  """
  #if isinstance(token, ClientLoginToken):
  #  return _join_token_parts('1c', token.token_string)
  #el
  if isinstance(token, OAuth2Token):
    return _join_token_parts(
        '2o', token.client_id, token.client_secret, token.scope,
        token.user_agent, token.auth_uri, token.token_uri,
        token.access_token, token.refresh_token)
  else:
    raise UnsupportedTokenType(
        'Unable to serialize token of type %s' % type(token))


TokenToBlob = token_to_blob


def token_from_blob(blob):
  """Deserializes a token string from the datastore back into a token object.

  Supported token classes: OAuth2Token.

  Args:
    blob: string created by token_to_blob.

  Raises:
    UnsupportedTokenType if the token is not one of the supported token
    classes listed above.

  Returns:
    A new token object with members set to the values serialized in the
    blob string. Note that any members which were set to '' in the original
    token will now be None.
  """
  parts = _split_token_parts(blob)
  if parts[0] == '2o':
    return OAuth2Token(parts[1], parts[2], parts[3], parts[4], parts[5],
                       parts[6], parts[7], parts[8])
  else:
    raise UnsupportedTokenType(
        'Unable to deserialize token with type marker of %s' % parts[0])


TokenFromBlob = token_from_blob


def dump_tokens(tokens):
  return ','.join([token_to_blob(t) for t in tokens])


def load_tokens(blob):
  return [token_from_blob(s) for s in blob.split(',')]
