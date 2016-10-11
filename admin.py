import networkx
import os
import cgi
import urllib
import random
import math
import itertools as it
import networkx as nx
from google.appengine.api import users
from google.appengine.ext import ndb
import jinja2
import webapp2
import logging
#logging.info("hello")

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True,)

def formatdatetime(value, format='%Y-%m-%d %H:%M'):
    return value.strftime(format)

def getplayercount(tournament):
    numplayers = len(Player.query(ancestor=tournament.key).fetch())
    return numplayers

def isFinished(thisround):
    tables = Table.query(ancestor=thisround.key).fetch()
    finished = True
    for table in tables:
        if not(table.finished):
            finished = False
    return finished

def clearWinner(tournament):
    playerlist = Player.query(ancestor=tournament.key).fetch(projection=[Player.name, Player.score])
    highscore = 0
    for player in playerlist:
        if player.score > highscore:
            highscore = player.score
    highScorers = Player.query(Player.score == highscore,ancestor=tournament.key).fetch()
    if len(highScorers) == 1:
        return True
    return False

JINJA_ENVIRONMENT.filters['formatdatetime']=formatdatetime
JINJA_ENVIRONMENT.filters['getplayercount']=getplayercount
JINJA_ENVIRONMENT.filters['isFinished']=isFinished
JINJA_ENVIRONMENT.filters['clearWinner']=clearWinner

def user_key(user_id):
    """Constructs a Datastore key for a user entity."""
    return ndb.Key('User', user_id)

ROUND_LENGTHS = {0:30,25:50,50:70,75:100,100:120,150:150,200:200}
SCENARIOS = ['Entrenched','Line Breaker','Take and Hold','The Pit','Extraction','Incursion','Outlast','Recon']
FACTIONS = ['Cryx','Cygnar','Khador','Protectorate of Menoth','Retribution of Scyrah','Convergence of Cyriss','Mercenaries','Circle Orboros','Legion of Everblight','Skorne','Trollbloods','Minions']
MAXGROUP = 50

#START NDB data models
class Tournament(ndb.Model):
    """Model for representing a tournament."""
    name = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)
    system = ndb.StringProperty(indexed=False)
    pointsize = ndb.IntegerProperty(default=75)
    currentround = ndb.IntegerProperty(indexed=False,default=0)

class Round(ndb.Model):
    """A round within the tournament"""
    number = ndb.IntegerProperty()
    length = ndb.IntegerProperty(indexed=False)
    scenario = ndb.StringProperty(indexed=False,choices=SCENARIOS)
    
class Table(ndb.Model):
    """A table/pairing of players within a given round of the tournament"""
    number = ndb.IntegerProperty()
    players = ndb.KeyProperty(repeated=True)
    finished = ndb.BooleanProperty(indexed=False,default=False)
    
class Player(ndb.Model):
    """A given player within the tournament"""
    name = ndb.StringProperty()
    number = ndb.IntegerProperty()
    note = ndb.StringProperty(default="")
    faction = ndb.StringProperty(indexed=False,choices=FACTIONS)
    opponents = ndb.KeyProperty(repeated=True)
    scorelist = ndb.IntegerProperty(repeated=True)
    cplist = ndb.IntegerProperty(repeated=True)
    pcdestlist = ndb.IntegerProperty(repeated=True)
    score = ndb.ComputedProperty(lambda self: sum(self.scorelist))
    cp = ndb.ComputedProperty(lambda self: sum(self.cplist))
    pcdest = ndb.ComputedProperty(lambda self: sum(self.pcdestlist))
    sos = ndb.ComputedProperty(lambda self: sum(opponent.get().score for opponent in self.opponents))
    bye = ndb.BooleanProperty(default=False)
    pairedDown = ndb.BooleanProperty(default=False)
    dropped = ndb.BooleanProperty(default=False)
#END NDB data models

class adminview(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            identity = users.get_current_user().user_id()
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            #get list of ALL tournaments owned by this user
            tournaments = Tournament.query().order(-Tournament.date).fetch()
            template_values = {
                'user': user,
                'tournaments': tournaments,
                'url': url,
                'url_linktext': url_linktext,
                }
            template = JINJA_ENVIRONMENT.get_template('admin.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url(self.request.uri))
            
class adminRunTournament(webapp2.RequestHandler):
    def get(self):
        logging.info("hi")
        user = users.get_current_user()    
        if user:
            identity = users.get_current_user().user_id()
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            error = self.request.get('ERR')
            tournamentkeyurlstr = self.request.get('TKEY')
            tournamentkey = ndb.Key(urlsafe=tournamentkeyurlstr)
            tournament = tournamentkey.get()
            tables = []
            thisround = []
            players = Player.query(ancestor=tournament.key).order(-Player.score, -Player.sos, -Player.cp, -Player.pcdest, Player.dropped,Player.number,Player.name).fetch()
            if tournament.currentround > 0:
                getrounds = Round.query(ancestor=tournamentkey)
                thisround = getrounds.filter(Round.number == tournament.currentround).get()
                tables = Table.query(ancestor=thisround.key).order(Table.number).fetch()
            template_values = {
                'user': user,
                'tournament': tournament,
                'players':players,
                'tables':tables,
                'thisround':thisround,
                'url': url,
                'url_linktext': url_linktext,
                'error': error,
                }
            template = JINJA_ENVIRONMENT.get_template('run.html')
            self.response.write(template.render(template_values)) 

app = webapp2.WSGIApplication([
    ('/admin', adminview),
    ('/adminrun', adminRunTournament),
], debug=True)