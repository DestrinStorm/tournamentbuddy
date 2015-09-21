import os
import cgi
import urllib
import random
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

JINJA_ENVIRONMENT.filters['formatdatetime']=formatdatetime
JINJA_ENVIRONMENT.filters['getplayercount']=getplayercount

def user_key(user_id):
    """Constructs a Datastore key for a user entity."""
    return ndb.Key('User', user_id)

#START NDB data models
class Tournament(ndb.Model):
    """Model for representing a tournament."""
    name = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)
    system = ndb.StringProperty(indexed=False)
    currentround = ndb.IntegerProperty(indexed=False,default=0)

class Round(ndb.Model):
    """A round within the tournament"""
    number = ndb.IntegerProperty()
    length = ndb.IntegerProperty(indexed=False)
    scenario = ndb.StringProperty(indexed=False,choices=['Destruction','Two Fronts','Close Quarters','Fire Support','Incoming','Incursion','Outflank','Recon'])
    
class Table(ndb.Model):
    """A table/pairing of players within a given round of the tournament"""
    number = ndb.IntegerProperty()
    players = ndb.KeyProperty(repeated=True)
    terrain = ndb.StringProperty(indexed=False)
    finished = ndb.BooleanProperty(indexed=False,default=False)
    
class Player(ndb.Model):
    """A given player within the tournament"""
    name = ndb.StringProperty(indexed=False)
    faction = ndb.StringProperty(indexed=False,choices=['Cryx','Cygnar','Khador','Protectorate of Menoth','Retribution of Scyrah','Convergence of Cyriss','Mercenaries','Circle Orboros','Legion of Everblight','Skorne','Trollbloods','Minions'])
    score = ndb.IntegerProperty(default=0)
    sos = ndb.IntegerProperty(default=0)
    cp = ndb.IntegerProperty(default=0)
    pcdest = ndb.IntegerProperty(default=0)
#END NDB data models

class MainPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            identity = users.get_current_user().user_id()
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            #get list of tournaments owned by this user
            tournaments = Tournament.query(ancestor=user_key(identity)).fetch()
            template_values = {
                'user': user,
                'tournaments': tournaments,
                'url': url,
                'url_linktext': url_linktext,
                }
            template = JINJA_ENVIRONMENT.get_template('main.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect(users.create_login_url(self.request.uri))

class NewTournament(webapp2.RequestHandler):
    def get(self):
        # Grab the new tournament name and set a container for it
        if users.get_current_user():
            identity=users.get_current_user().user_id()
            tournament = Tournament(parent=user_key(identity))
            tournament.name = self.request.get('name')
            tournament.system = self.request.get('system')
            tournament.put()
        self.redirect('/')
        
class DelTournament(webapp2.RequestHandler):
    def get(self):
        deletekeyurlstr = self.request.get('TKEY')
        deletekey = ndb.Key(urlsafe=deletekeyurlstr)
        if users.get_current_user():
            identity=users.get_current_user().user_id()
            #Check we're logged in as the owner to prevent remote deletions
            if identity == deletekey.parent().id():
                deletekey.delete()
        self.redirect('/')
        
class RunTournament(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()    
        if user:
            identity = users.get_current_user().user_id()
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            tournamentkeyurlstr = self.request.get('TKEY')
            tournamentkey = ndb.Key(urlsafe=tournamentkeyurlstr)
            tournament = tournamentkey.get()
            tables = []
            players = Player.query(ancestor=tournament.key).fetch()
            if tournament.currentround > 0:
                thisround = Round.query(Round.number == tournament.currentround).get()
                tables = Table.query(ancestor=thisround.key).fetch()
                logging.info(tables)
                logging.info(players)
            template_values = {
                'user': user,
                'tournament': tournament,
                'players':players,
                'tables':tables,
                'url': url,
                'url_linktext': url_linktext,
                }
            template = JINJA_ENVIRONMENT.get_template('run.html')
            self.response.write(template.render(template_values))            
            
class DoPairings(webapp2.RequestHandler):
    def get(self):
        tournamentkeyurlstr = self.request.get('TKEY')
        tournamentkey = ndb.Key(urlsafe=tournamentkeyurlstr)
        tournament = tournamentkey.get()
        playerlist = Player.query(ancestor=tournamentkey).fetch()
        #Generate the new round container
        thisround = Round(parent=tournamentkey)
        thisround.number = tournament.currentround + 1
        """TODO
        thisround.length = 
        thisround.scenario = """
        roundkey = thisround.put()
        #Initial random pairing?
        if thisround.number == 1:
            #for the number of tables we have (floor of players/2)
            for x in range(1,(len(playerlist)/2)+1):
                #pick a random player from the list, then remove them
                playerA = random.choice(playerlist)
                playerlist.remove(playerA)
                #and their opponent
                playerB = random.choice(playerlist)
                playerlist.remove(playerB)
                table = Table(parent=roundkey)
                table.number = x
                table.players = [playerA.key,playerB.key]
                """TODO
                table.terrain = """
                table.put()
            if playerlist:
                #There is a bye
                table = Table(parent=roundkey)
                table.number = 0
                table.players = [playerlist[0].key]
                """TODO: player score modifications"""
                table.finished = True
                table.put()
        else:
            logging.info("TODO: rounds beyond the first")
        tournament.currentround = thisround.number
        tournament.put()
        self.redirect('/run?TKEY='+tournamentkeyurlstr)    
            
            
class AddPlayer(webapp2.RequestHandler):
    def get(self):
        if users.get_current_user():
            identity=users.get_current_user().user_id()
            tournamentkeyurlstr = self.request.get('TKEY')
            tournamentkey = ndb.Key(urlsafe=tournamentkeyurlstr)
            player = Player(parent=tournamentkey)
            player.name = self.request.get('name')
            player.faction = self.request.get('faction')
            player.put()
        self.redirect('/run?TKEY='+tournamentkeyurlstr)
        
class DropPlayer(webapp2.RequestHandler):
    def get(self):
        tournamentkeyurlstr = self.request.get('TKEY')
        playerkeyurlstr = self.request.get('PKEY')
        playerkey = ndb.Key(urlsafe=playerkeyurlstr)
        if users.get_current_user():
            identity=users.get_current_user().user_id()
            if identity == playerkey.parent().parent().id():
                playerkey.delete()
        self.redirect('/run?TKEY='+tournamentkeyurlstr)
        
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/new', NewTournament),
    ('/del', DelTournament),
    ('/run', RunTournament),
    ('/pair', DoPairings),
    ('/addplayer', AddPlayer),
    ('/dropplayer', DropPlayer),
], debug=True)