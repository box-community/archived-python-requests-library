#!/usr/bin/python

import box_requests
import time
import datetime
import pytz.tzfile
import requests
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
log=logging.getLogger(__name__)
# retry a get up to 5 times if a transient error is received
def retry_get(client, uri):
    retry_count=0
    while True:
        try:
            return client.request('GET', uri)
        except ValueError:
            raise
        except requests.RequestException:
            if retry_count >= 5:
                raise
            retry_count+=1

tz=pytz.tzfile.build_tzinfo('localtime', open("/etc/localtime"))
n=datetime.datetime.now(tz)
endt=n.replace(hour=0,minute=0,second=0,microsecond=0)
startt=endt-datetime.timedelta(1, 0, 1)
with box_requests.boxsession(None) as boxsess:
  log.debug("Fetching events from {0} to {1}".format(startt,endt))
  lastitem=None
  skipto=None
  uri="/2.0/events?stream_type=admin_logs&created_after={0}&created_before={1}".format(startt, endt)
  respjs=retry_get(boxsess, uri)
  while respjs.has_key('chunk_size') and respjs['chunk_size'] > 0:
    if not respjs.has_key('entries'):
      raise Exception, "JSON result is malformed: No entries"
    try:
      entrycount=len(respjs["entries"])
    except:
      raise Exception, "JSON result is malformed: 'entries' is not a list"
    nsp=0
    if respjs.has_key('next_stream_position'):
       nsp=respjs['next_stream_position']
    log.debug("next_stream_position is %s; chunk size is %s; entries is %s", nsp, respjs['chunk_size'], entrycount)
    maxts=0
    maxid=0
    for item in respjs['entries']:
      #print item
      if item['type'] == "event":
        # on non-initial fetches, skip rows that have the same timestamp, 
        # until we find one that matches the last line from the previous batch
        if skipto:
           if skipto['created_at'] != item['created_at']:
              skipto=None
           elif skipto == item:
              skipto=None
              continue
        if skipto:
           continue
        print ",".join([str(item['created_by']['login']), str(item['created_at']), str(item['ip_address']), str(item['event_type'])])
        if item['created_at'] > maxts:
          maxts=item['created_at']
        if item['event_id'] > maxid:
          maxid=item['event_id']
        lastitem=item
      else:
        print >> sys.stderr, "Skipping object of type {0}".format(item['type'])
    if lastitem is None:
       break
    skipto=lastitem
    uri="/2.0/events?stream_type=admin_logs&created_after={0}&created_before={1}".format(lastitem['created_at'], endt)
    if options.verbose:
      print >> sys.stderr, "Max timestamp is {0} and max event id is {1}".format(maxts, maxid)
      print >> sys.stderr, "Fetching events from {0}".format(lastitem['created_at'])
    lastitem=None
    log.debug("Fetching from {0}".format(uri))
    respjs=retry_get(boxsess, uri)
