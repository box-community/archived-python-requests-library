#!/usr/bin/python

import box_requests
import sys
import logging
import optparse

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
    respjs=bs.request("GET", "/2.0/users?limit=100&offset={0}".format(current))
    log.debug("Fetching /2.0/users?limit=100&offset={0}".format(current))
    for item in respjs['entries']:
      current=current+1
      if item['type'] == "user":
        id=str(item['id'])
        login=item['login']
        used=str(item['space_used'])
        quota=str(item['space_amount'])
        status=str(item['status'])
        print ",".join([id,login,used,quota,status])
      else:
        print >> sys.stderr, "Skipping object of type {0}".format(item['type'])
finally:
 rl.removeHandler(sh)
