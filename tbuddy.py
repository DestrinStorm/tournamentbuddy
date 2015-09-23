import os
import cgi
import urllib
import random
import math
import pypair
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
        logging.info(finished)
        if not(table.finished):
            finished = False
    logging.info(finished)
    return finished

JINJA_ENVIRONMENT.filters['formatdatetime']=formatdatetime
JINJA_ENVIRONMENT.filters['getplayercount']=getplayercount
JINJA_ENVIRONMENT.filters['isFinished']=isFinished

def user_key(user_id):
    """Constructs a Datastore key for a user entity."""
    return ndb.Key('User', user_id)

ROUND_LENGTHS = {15:30,25:50,35:70,50:100,75:120,100:150,150:200,200:250}
SCENARIOS = ['Destruction','Two Fronts','Close Quarters','Fire Support','Incoming','Incursion','Outflank','Recon']

#START NDB data models
class Tournament(ndb.Model):
    """Model for representing a tournament."""
    name = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)
    system = ndb.StringProperty(indexed=False)
    pointsize = ndb.IntegerProperty(default=50)
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
    name = ndb.StringProperty()
    faction = ndb.StringProperty(indexed=False,choices=['Cryx','Cygnar','Khador','Protectorate of Menoth','Retribution of Scyrah','Convergence of Cyriss','Mercenaries','Circle Orboros','Legion of Everblight','Skorne','Trollbloods','Minions'])
    scorelist = ndb.IntegerProperty(repeated=True)
    cplist = ndb.IntegerProperty(repeated=True)
    pcdestlist = ndb.IntegerProperty(repeated=True)
    score = ndb.ComputedProperty(lambda self: sum(self.scorelist))
    cp = ndb.ComputedProperty(lambda self: sum(self.cplist))
    pcdest = ndb.ComputedProperty(lambda self: sum(self.pcdestlist))
    sos = ndb.IntegerProperty(default=0)
#END NDB data models

class MainPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            identity = users.get_current_user().user_id()
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            #get list of tournaments owned by this user
            tournaments = Tournament.query(ancestor=user_key(identity)).order(-Tournament.date).fetch()
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
                ndb.delete_multi(ndb.Query(ancestor=deletekey).iter(keys_only = True))
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
            thisround = []
            players = Player.query(ancestor=tournament.key).order(-Player.score, -Player.sos, -Player.cp, -Player.pcdest, Player.name).fetch()
            if tournament.currentround > 0:
                thisround = Round.query(Round.number == tournament.currentround).get()
                tables = Table.query(ancestor=thisround.key).order(Table.number).fetch()
            template_values = {
                'user': user,
                'tournament': tournament,
                'players':players,
                'tables':tables,
                'thisround':thisround,
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
        thisround.length = ROUND_LENGTHS[tournament.pointsize] + random.choice([5,10,15,-5,-10,-15])
        thisround.scenario = random.choice(SCENARIOS)
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
                byeplayer = playerlist[0]
                table = Table(parent=roundkey)
                table.number = 0
                table.players = [byeplayer.key]
                #Grant the player bye scores for round 1
                byeplayer.scorelist.append(1)
                byeplayer.cplist.append(3)
                byeplayer.pcdestlist.append(int(math.ceil(tournament.pointsize/2.0)))
                byeplayer.put()
                table.finished = True
                table.put()
        else:
            #Rounds beyond the first
            #a range = currentround gives us all possible score levels to iterate on
            tablenumber = 0
            for y in reversed(range(thisround.number):
                #find all players with y as their score
                scorelevelplayers = []
                for player in playerlist:
                    if player.score == y:
                        scorelevelplayers.append(player)
                    #pick a random player from the list, then remove them
                    playerA = random.choice(scorelevelplayers)
                    scorelevelplayers.remove(playerA)
                    #and their opponent = but we need to make sure they haven't played before
                    #grab all the times playerA has played
                    qry = Table.query(Table.players == playerA.key)
                    #pull out all player keys and put in a set to remove duplicates
                    opponentsOfA = set(qry.fetch())
                    #delete playerA
                    opponentsOfA.remove(playerA.key)
                    #cut down the potential opponent list
                    scorelevelminusopponents = scorelevelplayers
                    for player in scorelevelminusopponents:
                        if player.key in opponentsOfA:
                            scorelevelminusopponents.remove(player)
                    playerB = random.choice(scorelevelminusopponents)
                    scorelevelplayers.remove(playerB)
                    #what table should this be?  
                    table = Table(parent=roundkey)
                    table.number = tablenumber + 1
                    table.players = [playerA.key,playerB.key]
                    """TODO
                    table.terrain = """
                    table.put()
                if scorelevelplayers:
                #someone is getting paired down
                    lowerscorelevelplayers = []
                    for player in playerlist:
                        if player.score == y-1:
                            lowerscorelevelplayers.append(player)
                    #pick a random player from the list, then remove them
            if playerlist:
                #There is a bye
        tournament.currentround = thisround.number
        tournament.put()
        self.redirect('/run?TKEY='+tournamentkeyurlstr)    

class Results(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()    
        if user:
            identity = users.get_current_user().user_id()
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            tablekeyurlstr = self.request.get('TABKEY')
            tablekey = ndb.Key(urlsafe=tablekeyurlstr)
            table = tablekey.get()
            thisround = tablekey.parent().get()
            tournament = thisround.key.parent().get()
            players = []
            for player in table.players:
                players.append(player.get())
            template_values = {
                'user': user,
                'tournament': tournament,
                'thisround': thisround,
                'players':players,
                'table':table,
                'url': url,
                'url_linktext': url_linktext,
                }
            template = JINJA_ENVIRONMENT.get_template('results.html')
            self.response.write(template.render(template_values))            

class ResultsSubmit(webapp2.RequestHandler):
    def get(self):
        if users.get_current_user():
            tablekeyurlstr = self.request.get('TABKEY')
            table = ndb.Key(urlsafe=tablekeyurlstr).get()
            thisround = table.key.parent().get()
            logging.info(thisround.number)
            #Add in player scores
            winnerkeyurlstr = self.request.get('win')        
            cps = self.request.get_all('cps')
            pcdest = self.request.get_all('pcdest')
            players = []
            for player in table.players:
                players.append(player.get())
            for x in range(2): 
                if len(players[x].scorelist) == thisround.number:
                    if players[x].key.urlsafe() == winnerkeyurlstr:
                        players[x].scorelist[thisround.number-1] = 1
                    else:
                        players[x].scorelist[thisround.number-1] = 0
                    players[x].cplist[thisround.number-1] = (int(cps[x]))
                    players[x].pcdestlist[thisround.number-1] = (int(pcdest[x]))
                else:
                    if players[x].key.urlsafe() == winnerkeyurlstr:
                        players[x].scorelist.append(1)
                    else:
                        players[x].scorelist.append(0)
                    players[x].cplist.append(int(cps[x]))
                    players[x].pcdestlist.append(int(pcdest[x]))
                #also sort out SOS
                players[x].put()
            #Mark the table as finished
            table.finished = True
            table.put()
            tournamentkeyurlstr = table.key.parent().parent().urlsafe()
            self.redirect('/run?TKEY='+tournamentkeyurlstr)
        
class ChangePoints(webapp2.RequestHandler):
    def get(self):
        if users.get_current_user():
            identity=users.get_current_user().user_id()
            tournamentkeyurlstr = self.request.get('TKEY')
            tournamentkey = ndb.Key(urlsafe=tournamentkeyurlstr)
            tournament = tournamentkey.get()
            newpoints = int(self.request.get('points'))
            tournament.pointsize = newpoints
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
    ('/results', Results),
    ('/resultssubmit', ResultsSubmit),
    ('/changepoints', ChangePoints),
], debug=True)