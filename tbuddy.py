import os
import cgi
import urllib
from google.appengine.api import users
from google.appengine.ext import ndb
import jinja2
import webapp2
import random

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
    
MAIN_PAGE_HTML = """\
<html>
  <body>
    <form action="/results" method="post">
      <div><input type="number" name="numtables" min="1" max="64"></div>
      <div><input type="submit" value="Submit"></div>
    </form>
  </body>
</html>
"""

CREATE_TOURNAMENT_TEMPLATE = """\
<hr>
    <form>New Tournament name:
      <input value="" name="tournament_name">
      <select name="game">
       <option value="Warmachine/Hordes">Warmachine/Hordes</option>
       <option value="Netrunner">Netrunner</option>
       <option value="Armada">Armada</option>
       </select>
      <input type="submit" value="Create New">
    </form>
"""

MAIN_PAGE_FOOTER_TEMPLATE = """\
    <hr>
    Logged in as: %s <a href="%s">%s</a>
  </body>
</html>
"""

terraintable = {'Wilderness': ['Thornwood Forest',
			'Blindwater Marshes',
			'Bloodstone Marches',
			'The Gnarls',
			'Dragonspine Peaks',
			'Skirovnya'],
		'Ruins & Battlegrounds': ['Castle of the Keys',
					'Bones of Orboros',
					'Orgoth Ruins',
					'Northguard trenchlines',
					'Crael Valley',
					'Point Bourne'],
		'Civilization': ['Ternon Crag',
				'Caspia/Sul',
				'Imer',
				'Leryn',
				'Five Fingers',
				'Korsk']}
				
regions = list(terraintable.keys())

#START NDB data models
class User(ndb.Model):
    """Model for representing a user"""
    identity = ndb.StringProperty(indexed=False)
    email = ndb.StringProperty(indexed=False)
    
class Tournament(ndb.Model):
    """Model for representing a tournament."""
    name = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)
    game = ndb.StringProperty(indexed=False)
    maxrounds = ndb.IntegerProperty(indexed=False)
    currentround = ndb.IntegerProperty(indexed=False)
    
class Player
    """A given player within the tournament"""
    name = ndb.StringProperty(indexed=False)
    faction = ndb.StringProperty(indexed=False)
    
#END NDB data models

class MainPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        
        if user:
                #Header
                self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
                self.response.write('<html><body>')
                #Current tournament section
                #Create new tournament section
                self.response.write(CREATE_TOURNAMENT_TEMPLATE)
                #HTML footer
                url = users.create_logout_url(self.request.uri)
                url_linktext = 'Logout'
                self.response.write(MAIN_PAGE_FOOTER_TEMPLATE %(user, url, url_linktext))
	else:
                self.redirect(users.create_login_url(self.request.uri))
        

class Results(webapp2.RequestHandler):

    def post(self):
        self.response.write('<br>')
        for x in range(int(cgi.escape(self.request.get('numtables')))):
        	self.response.write(str(x+1)+' ')
		self.response.write(random.choice(terraintable[random.choice(regions)]))
		self.response.write('<br>')
        self.response.write('</pre></body></html>')

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/results', Results),
], debug=True)