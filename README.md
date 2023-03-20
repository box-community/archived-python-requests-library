<img src="images/box-dev-logo-clip.png" 
alt= “box-dev-logo” 
style="margin-left:-10px;"
width=40%;>

box_session - Python helper for [Box](http://box.com) API
-----------------------------------------------------------

This library helps manage box authentication credentials for python apps.
It is mostly designed with single-user admin apps in mind, not file management
apps or multi-user web apps.

Usage example:

```python
from box_requests import boxsession

session=boxsession("boxtoken.dat")
with session:
  u=session.request("GET", "/2.0/users/me")
  print "User is %s" % u['login']
```



Features
----------------------------

- OAuth token management (including saving refresh token on update)
- retry on 429 errors
- Based on the [Python Requests](http://python-requests.org/) library. Keyword args passed to boxession's request method are passed to requests' session.request

Included sample scripts
----------------------------
The samples directory includes scripts to:

- get initial oauth credentials (web server with WSGI required)
- dump all users in a box enterprise domain
- dump events in a box enterprise domain
- change quotas for users in a box enterprise domain
