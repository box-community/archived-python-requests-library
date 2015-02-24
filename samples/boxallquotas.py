#!/usr/bin/python
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

# this script raises quotas of all non-admin users to 100GB. 
# quotas higher than 100GB are left alone

import box_requests
import sys
import logging
import optparse
import json

o=optparse.OptionParser()
o.add_option('-v', '--verbose', action="store_true", dest="verbose", 
        default=False, help="Display username on success")
o.add_option('-d', '--debug', action="store_true", dest="debug", 
        default=False, help="Enable debug logging")
(options, args) = o.parse_args()

rl=logging.getLogger()
sh=logging.StreamHandler(sys.stderr)
fm=logging.Formatter("%(asctime)s %(name)s [%(levelname)s] %(filename)s:%(lineno)d:%(funcName)s %(message)s")
sh.setFormatter(fm)
rl.addHandler(sh)

if options.debug:
   sh.setLevel(logging.DEBUG)
   rl.setLevel(logging.DEBUG)

log=logging.getLogger("dumpusers")
try:
 with box_requests.boxsession() as bs:
  respjs=bs.request("GET", "/2.0/users?limit=1")
  #print resp.getheaders()
  if respjs.has_key('total_count'):
    print >> sys.stderr, "{0} total users".format(respjs['total_count'])
  else:
    raise Exception, "No user count in response"
  count=respjs['total_count']
  current=0
  while current < count:
    bs.client.close()
    respjs=bs.request("GET", "/2.0/users?limit=100&offset={0}&fields=login,space_used,space_amount,status,role".format(current))
    log.debug("Fetching /2.0/users?limit=100&offset={0}".format(current))
    for item in respjs['entries']:
      current=current+1
      if item['type'] == "user":
        id=str(item['id'])
        login=item['login']
        used=str(item['space_used'])
        quota=item['space_amount']
        quotas=str(item['space_amount'])
        status=str(item['status'])
        if (quota <  100 * 1024 * 1024 * 1024 and item['role'] != "admin"):
            print "Raising quota for {0}".format(login)
            nq=json.dumps({'space_amount':  100 * 1024 * 1024 * 1024})
            a=bs.request("PUT", "https://api.box.com/2.0/users/{0}".format(id), data=nq)
            if (quota == a['space_amount']):
               raise Exception, "quota did not change"
        else:
            print "Leaving quota for {0} at {1}".format(login, quota)
      else:
        print >> sys.stderr, "Skipping object of type {0}".format(item['type'])
finally:
 rl.removeHandler(sh)
