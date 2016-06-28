import webapp2
import logging
import tbuddy
from google.appengine.api import users
from google.appengine.ext import ndb

class UpdateHandler(webapp2.RequestHandler):
    def get(self,cursor=None):
        self.response.out.write('Starting schema migration')
        players = tbuddy.Player.query()
        res, cur, more = players.fetch_page(100, start_cursor=cursor)
        put_queue = [ent for ent in res]
        ndb.put_multi(put_queue)
        if more:
            iter_entities(cur)

app = webapp2.WSGIApplication([('/update_schema', UpdateHandler)])