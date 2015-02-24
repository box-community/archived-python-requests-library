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
import boxtoken
import os
import time
import fcntl
import requests
import logging

class BoxAPIError(Exception):
    pass
class BoxTokenError(Exception):
    pass
def parsekvlist(str):
    ret={}
    sa=str.split(",")
    for kv in sa:
        (k,v)=kv.split("=")
        ret[k.strip()]=v.strip().strip('"')
    return ret
def _checkresponse(resp, check_retry=False):
  if resp.status_code >= 300:
    msg="Call failed with code {0}: {1}".format(resp.status_code, resp.raw.reason)
    if resp.status_code >= 400 and resp.status_code < 499:
       try:
          wa=resp.headers["WWW-Authenticate"]
          if wa and wa.startswith("Bearer "):
             auth=parsekvlist(wa.replace("Bearer ", "", 1))
             msg="Call failed with code {0}: {1}; error: {2}, description: {3}".format(resp.status_code, resp.raw.reason, auth["error"], auth["error_description"])
       except:
          pass
    #print msg
    #print resp.getheaders()
    #print resp.read()
    try:
        errjs=resp.json()
        msg="Call failed: status {0}, message {1}".format(errjs["code"], errjs["message"])
        logging.debug("Full error is %s", errjs)
    except:
        pass
    if check_retry and resp.status_code == 429:
        try:
            ra=resp.headers["Retry-After"]
            return (True, int(ra))
        except KeyError:
            return (True, -1)
        except ValueError:
            return (True, -1)
    raise BoxAPIError, msg
  if resp.status_code != 204:
    try:
        rlen=int(resp.headers["content-length"])
    except KeyError:
        rlen=-1
    except ValueError:
        rlen=-1
    if rlen == 0:
        raise BoxAPIError, "Call returned no data"
  return None
class boxsession(object):
    token=None
    loadfile=None
    client=None
    open=False
    _wait=None
    def __enter__(self):
        if self.open:
           raise BoxTokenError, "boxsession is not reentrant"
        if self.readonly:
            fd=os.open(self.tokpath, os.O_RDONLY)
        else:
            for retry in range (5):
                fd=os.open(self.tokpath, os.O_RDWR)
                fcntl.lockf(fd, fcntl.LOCK_EX, 0, 0, os.SEEK_SET)
                st=os.fstat(fd)
                if st.st_nlink == 0:
                    fcntl.lockf(fd, fcntl.LOCK_UN, 0, 0, os.SEEK_SET)
                    os.close(fd)
                    fd=None
                if fd:
                    break
            else:
                raise BoxTokenError, "Cannot open/lock token file"
        self.loadfile=os.fdopen(fd, "r")
        token=boxtoken.token_from_blob(self.loadfile.read())
        if self.token is None:
		self.token=token
		self.client=None
	
	if self.token.access_token != token.access_token:
                self.token=token
                self.client=None
        # shouldn't happen
	if self.token.refresh_token != token.refresh_token:
		self.token=token
        if self.client is None:
            self.client=requests.session()
            self.client.auth=self.token
            # requests needs full uris. not compatible with atom.client's 
            # defaulting!
        self.open=True
        self.revoked=False
        return self
    def __exit__(self, type, value, tb):
        self.open=False
        loadfile=self.loadfile
        self.loadfile=None
        token=self.token
        self.token=False
        
        if not self.readonly and token and self.revoked:
            os.unlink(self.tokpath)
        elif not self.readonly and token and token.dirty:
            u=os.umask(0066)
            savefile=open(self.tokpath+".NEW", "w")
            savefile.truncate()
            savefile.write(boxtoken.token_to_blob(token))
            savefile.close()
            os.rename(self.tokpath + ".NEW", self.tokpath)
            os.umask(u)
        loadfile.close()
    def __init__(self, path=None, readonly=False):
        if path is None:
            fileprefix=""
            if os.path.exists("/var/local/box"):
                fileprefix="/var/local/box/"
            self.tokpath=fileprefix+"boxtoken.dat"
        else:
            self.tokpath=path
        self.readonly=readonly
    def revoke(self):
        if self.readonly:
           raise BoxTokenError, "boxsession is read only"
        elif self.open:
           self.token.revoke()
        else:
           raise BoxTokenError, "boxsession not open"
        self.revoked=True
    def checkresponse(self, resp):
        r=_checkresponse(resp)
        self._wait=None
        return r
    def request(self, method, url, **kwargs):
        if not self.open:
            raise BoxTokenError, "boxsession not open"
        if method in ('GET', 'OPTIONS'):
            kwargs.setdefault('allow_redirects', True)
        elif method in ('HEAD', 'DELETE'):
            kwargs.setdefault('allow_redirects', False)
        if not url.startswith("http"):
           if not url.startswith("/"):
              raise BoxAPIError, "Invalid url, must be absolute path"
           url="https://api.box.com{0}".format(url)
        with self.client as client:
            while True:
                r=client.request(method=method, url=url, **kwargs)
                if self._wait and self._wait > 600:
                    _checkresponse(r, check_retry=False)#raises exception
                    self._wait=None
                    #logging.debug("Headers are %s", r.headers)
                    if r.status_code == 204:
                        r.content # consume response
                        return None
                    return r.json()
                rr=_checkresponse(r, check_retry=True) #raises exception, except for 429
                if rr is None:
                    self._wait=None
                    #logging.debug("Headers are %s", r.headers)
                    #if r.headers["connection"]=="close":
                    #   pass
                    if r.status_code == 204:
                        r.content
                        return None
                    return r.json()
                elif rr[0] == True:
                    if self._wait:
                       self._wait = self._wait + 60
                    elif rr[1] > 0:
                       self._wait = rr[1]
                    else:
                       self._wait = 30
                    time.sleep(self._wait)
            
