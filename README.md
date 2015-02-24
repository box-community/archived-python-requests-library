box_session - Python helper for [Box](http://box.com) API
-----------------------------------------------------------

This library helps manage box authentication credentials for python apps.
It is mostly designed with single-user admin apps in mind, not file management
apps or multi-user web apps.

Usage example:

```python
from box_requests import boxsession

session=boxsession("boxtoken.dat")
u=session.request("/2.0/users/me")
print "User is %s" % u['login']
```



Supported features
----------------------------

- OAuth token management (including saving refresh token on update)
- retry on 429 errors


Included sample scripts
----------------------------
The samples directory includes scripts to:

- get initial oauth credentials (web server with WSGI required)
- dump all users in a box enterprise domain
- dump events in a box enterprise domain
- change quotas for users in a box enterprise domain
