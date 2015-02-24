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


# this script creates the boxtoken-tmpl.dat file containing
# the oauth client_id and client_secret
# boxauth.wsgi uses that file to get an oauth token that
# can actually be used with APIs

from box_requests import boxtoken
import sys

if len(sys.argv) < 3:
  print "Usage: boxtokeninit client_id secret [filename]"
  sys.exit(1)
client_id=sys.argv.pop(1)
client_secret=sys.argv.pop(1)
filename="boxtoken-tmpl.dat"
try:
  filename=sys.argv.pop(1)
except:
  pass

t=boxtoken.BoxOAuth2Token(client_id, client_secret, "", "Python-requests-box")
blob=boxtoken.token_to_blob(t)

savefile=open(filename, "w")
savefile.truncate()
savefile.write(blob)
savefile.close()

