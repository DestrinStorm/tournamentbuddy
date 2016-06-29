import webapp2
import logging
import tbuddy
from google.appengine.api import users
from google.appengine.ext import ndb

class AdminPage(webapp2.RequestHandler):
    def get(self):
        self.response.out.write('Hi, I am an admin page')
            #    logging.info(users.User(_user_id=tournament.key.parent().id()))


app = webapp2.WSGIApplication([('/admin', AdminPage)])