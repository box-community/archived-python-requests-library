#!/usr/bin/python

import box_requests
import requests
import os
import sys
import time
import socket
import optparse
import logging

def checktime(path, days):
   try:
      r=os.stat(path)
   except OSError:
      return False
   return (time.time() - r.st_mtime)  < (days * 86400)

def logfailure(msg):
   print >> sys.stderr, "Box API credentials expire if they are not used for a two week"
   print >> sys.stderr, "period. The process that attempts to keep them fresh on"
   print >> sys.stderr, "{0} failed. Details follow:".format(socket.gethostname())
   print >> sys.stderr
   if msg:
      print >> sys.stderr, msg
      print >> sys.stderr
   raise

o=optparse.OptionParser()
o.add_option('-v', '--verbose', action="store_true", dest="verbose", 
	default=False, help="Display username on success")
o.add_option('-d', '--debug', action="store_true", dest="debug", 
	default=False, help="Enable debug logging")
rl=logging.getLogger()
sh=logging.StreamHandler(sys.stderr)
fm=logging.Formatter("%(asctime)s %(name)s [%(levelname)s] %(filename)s:%(lineno)d:%(funcName)s %(message)s")
sh.setFormatter(fm)
rl.addHandler(sh)

(options, args) = o.parse_args()
if options.debug:
   sh.setLevel(logging.DEBUG)
   rl.setLevel(logging.DEBUG)

try:
   with box_requests.boxsession("/var/local/box/boxtoken.dat") as bs:
      ok=False
      try:
         resp=bs.request("GET", "/2.0/users/me")
      except requests.ConnectionError:
         if not checktime("/var/local/box/boxtoken.dat", 7):
            logfailure("Some sort of network problem occured, and has prevented the refresh\nprocess for several days.")
      except requests.Timeout:
         if not checktime("/var/local/box/boxtoken.dat", 7):
            logfailure("Some sort of network problem occured, and has prevented the refresh\nprocess for several days.")
      except ValueError:
         logfailure("This failure seems to be due to a programming error")
      except box_requests.BoxAPIError:
         logfailure("Box rejected the credentials, they may already be invalid")
      except:
         logfailure(None)
      else:
         if options.verbose:
             print "Current user is {0}".format(resp["login"])
except OSError:
   logfailure("The credentials are missing or could not be loaded")
except box_requests.BoxTokenError:
   logfailure("The credentials are missing or could not be loaded")
finally:
   rl.removeHandler(sh)
