#!/usr/bin/python

import box_requests
import sys
import os
from wsgiref.util import application_uri
import logging


class BoxAuthApp:
    def defaction(self):
        tokengood=False
        try:
            with box_requests.boxsession("/var/local/box/boxtoken.dat") as bs:
                resp=bs.request("GET", "/2.0/users/me")
                whoiam="{0} &lt;{1}&gt;".format(resp["name"], resp["login"])
                resp=bs.request("GET", "/2.0/users?limit=1")
                tokengood=True
        except:
            pass
        
        
        if tokengood:
            self.body.append("<p>Valid authentication for {0} found".format(whoiam))
            #self.body.append("<p>To replace the authentication data, start by deleting it")
            #self.body.append("<form>")
            #self.body.append("<input type=\"submit\" name=\"action\" value=\"Delete\">")
            #self.body.append("<input type=\"submit\" name=\"action\" value=\"Revoke\">")
            #self.body.append("</form>")
            return



        try:
            with box_requests.boxsession("/var/local/box/boxtoken-tmpl.dat", readonly=True) as basetoken:
                authurl=basetoken.token.generate_authorize_url(redirect_uri=self.redirect_uri)
        except:
            logger.error("Could not initialize oauth token template", exc_info=1)
            self.body.append("<p>Error, cannot set up box authentication, no api configuration available")
            self.body.append("<p>The <code>/var/local/box/boxtoken-tmpl.dat</code> file, containing the api configuration, does not exist or cannot be loaded")
            return
            
            
        self.headers=("Refresh", "5; url={0}".format(authurl))
        self.body.append("<p>You will be redirected to box to set up authorization in 5 seconds...")
        self.body.append("<p>Or click <a href=\"{0}\">here</a>".format(cgi.escape(authurl)))
        return

    def deleteaction(self):
        try:
            os.unlink("/var/local/box/boxtoken.dat")
        except OSError:
            pass
        return None
    
    
    def revokeaction(self):
        try:
            with box_requests.boxsession("/var/local/box/boxtoken.dat") as bs:
                bs.token.revoke()
        except grequestauth.OAuth2RevokeError:
            pass
        return None
        
        
    def boxreply(self, code):
        export_token=None
        try:
            with box_requests.boxsession("/var/local/box/boxtoken-tmpl.dat", readonly=True) as basetoken:
                authurl=basetoken.token.generate_authorize_url(redirect_uri=self.redirect_uri)
                try:
                    basetoken.token.get_access_token(code)
                    export_token=box_requests.token_to_blob(basetoken.token)
                except grequestauth.OAuth2AccessTokenError as e:
                    self.body.append("<p>Error, cannot set up box authentication, access token could not be fetched")
                    self.body.append("<p>{0}".format(e.error_message))
                    return
                except Exception as e:
                    logger.error("Could not get access token", exc_info=1)
                    self.body.append("<p>Error, cannot set up box authentication, access token could not be fetched")
                    self.body.append("<p>{0}".format(e.message))
                    return
        except Exception as e:
            logger.error("Could not initialize oauth token template", exc_info=1)
            self.body.append("<p>Error, cannot set up box authentication, no api configuration available")
            self.body.append("<p>The <code>/var/local/box/boxtoken-tmpl.dat</code> file, containing the api configuration, does not exist or cannot be loaded")
            return
        

        try:
            u=os.umask(0066)
            savefile=open("/var/local/box/boxtoken.dat.NEW", "w")
            savefile.truncate()
            savefile.write(export_token)
            savefile.close()
            os.rename("/var/local/box/boxtoken.dat.NEW", "/var/local/box/boxtoken.dat")
            os.umask(u)
        except OSError:
            try:
                basetoken.token.revoke()
            except grequestauth.OAuth2RevokeError:
                pass
            logger.error("Could not save token", exc_info=1)
            self.body.append("<p>Error, cannot set up box authentication, Could not save token")
        return None

    def boxerror(self, message, desc):
        self.body.append("<p>Error, cannot set up box authentication, authentication request rejected or canceled")
        self.body.append("<p>{0}; {1}".format(message, desc))
        return None
    
    def copy_proxy_settings(self):
        proxy_keys = [
            'no',
            'all',
            'http',
            'https',
            'ftp',
            'socks'
            ]
        
        for h in proxy_keys:
            k=h+'_proxy'
            if k in self.environ:
                os.environ[k]=self.environ[k]
                if k.upper() in self.environ:
                    os.environ[k.upper()]=self.environ[k.upper()]

    def __init__(self, environ, start_response):
        self.logger=logging.getLogger("boxauth")
        #self.logger.setLevel(logging.DEBUG)
        self.redirect_uri=application_uri(environ)
        self.environ=environ
        self.start_response=start_response
        self.headers=None
        self.body=[]
    def __call__(self):
        self.copy_proxy_settings()
        form=cgi.parse(environ=self.environ, fp=self.environ['wsgi.input'])
        self.logger.debug("enter")
        self.logger.debug(form)
        if form.has_key('error'):
            self.logger.debug("Got error reply from box")
            self.boxerror(form['error'][0], form.get('error_description', "No details provided"))
        elif form.has_key('code'):
            self.logger.debug("Got intermediate response code from box")
            self.boxreply(form['code'][0])
        #elif form.has_key('action'):
        #    self.logger.debug("User is removing token")
        #    if form['action'][0].lower() == "revoke":
        #        self.revokeaction()
        #        self.deleteaction()
        #    elif form['action'][0].lower() == "delete":
        #        self.deleteaction()
        #    else:
        #        self.body.append("<p>invalid action")
        elif len(form.keys()) > 0:
            self.logger.debug("Unknown script parameters %s", form.keys())
            self.body.append("<p>invalid post arguments")
            
        if len(self.body) == 0:
            self.logger.debug("Checking for existing valid token")
            self.defaction()

        self.logger.debug(self.headers)
        self.logger.debug(self.body)
        headers=[('Content-Type', 'text/html;charset=UTF-8')]
        if self.headers:
            headers.append(self.headers)
        self.start_response('200 OK', headers)
        TOP= """
<!DOCTYPE html>
<html>
<head>
<title>Box API authorization</title>
</head>
<body>
"""
        BOTTOM="""
</body>
</html>
"""
        self.logger.debug("exit")
        return [TOP, "\n".join(self.body), BOTTOM]

def application(environ, start_response):
    loghandler=logging.FileHandler("/var/local/box/authlog")
    formatter=logging.Formatter("%(asctime)s %(name)s [%(levelname)s] %(filename)s:%(lineno)d:%(funcName)s %(message)s")
    loghandler.setFormatter(formatter)
    rl=logging.getLogger()
    rl.addHandler(loghandler)
    try:
        app=BoxAuthApp(environ, start_response)
        ret=app()
    finally:
        rl.removeHandler(loghandler)
        loghandler.close()
    return ret
