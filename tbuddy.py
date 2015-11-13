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

JINJA_ENVIRONMENT.filters['formatdatetime']=formatdatetime
JINJA_ENVIRONMENT.filters['getplayercount']=getplayercount
JINJA_ENVIRONMENT.filters['isFinished']=isFinished

def user_key(user_id):
    """Constructs a Datastore key for a user entity."""
    return ndb.Key('User', user_id)

ROUND_LENGTHS = {15:30,25:50,35:70,50:100,75:120,100:150,150:200,200:250}
SCENARIOS = ['Destruction','Two Fronts','Close Quarters','Fire Support','Incoming','Incursion','Outflank','Recon']
MAXGROUP = 50

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
    opponents = ndb.KeyProperty(repeated=True)
    scorelist = ndb.IntegerProperty(repeated=True)
    cplist = ndb.IntegerProperty(repeated=True)
    pcdestlist = ndb.IntegerProperty(repeated=True)
    score = ndb.ComputedProperty(lambda self: sum(self.scorelist))
    cp = ndb.ComputedProperty(lambda self: sum(self.cplist))
    pcdest = ndb.ComputedProperty(lambda self: sum(self.pcdestlist))
    sos = ndb.IntegerProperty(default=0)
    bye = ndb.BooleanProperty(default=False)
    pairedDown = ndb.BooleanProperty(default=False)
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
            for player in players:
                logging.info(player.opponents)
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
                }
            template = JINJA_ENVIRONMENT.get_template('run.html')
            self.response.write(template.render(template_values))            
            
class DoPairings(webapp2.RequestHandler):
    def pairPlayers(self, p1key, p2key, openTable, roundkey):
        player1 = p1key.get()
        player2 = p2key.get()
        logging.info("Pairing players %s and %s"%(player1.name, player2.name))

        player1.opponents.append(p2key)
        if player1.score > player2.score:
            player1.pairedDown = True
        player1.put()
        
        player2.opponents.append(p1key)
        if player2.score > player1.score:
            player2.pairedDown = True
        player2.put()
        
        table = Table(parent=roundkey)
        table.number = openTable
        table.players = [p1key,p2key]
        """TODO
        table.terrain ="""
        table.put()
        
    def assignBye(self, p1key, roundkey):
        byeplayer = p1key.get()
        logging.info( "%s got the bye"%byeplayer.name)
        table = Table(parent=roundkey)
        table.number = 0
        table.players = [p1key]
        #Grant the player bye scores for round 1
        byeplayer.scorelist.append(1)
        byeplayer.cplist.append(3)
        tournament = roundkey.parent().get()
        byeplayer.pcdestlist.append(int(math.ceil(tournament.pointsize/2.0)))
        byeplayer.bye = True
        byeplayer.put()
        table.finished = True
        table.put()
    
    def get(self):
        logging.info("Starting the pairing process")
        tournamentkeyurlstr = self.request.get('TKEY')
        tournamentkey = ndb.Key(urlsafe=tournamentkeyurlstr)
        tournament = tournamentkey.get()
        playerlist = Player.query(ancestor=tournamentkey).fetch()
        playerkeylist = []
        logging.info(playerlist)
        #Generate the new round container
        thisround = Round(parent=tournamentkey)
        thisround.number = tournament.currentround + 1
        thisround.length = ROUND_LENGTHS[tournament.pointsize] + random.choice([5,10,15,-5,-10,-15])
        thisround.scenario = random.choice(SCENARIOS)
        roundkey = thisround.put()
        #INITILISATION
        startingTable = 1
        openTable = startingTable
        #Contains lists of players sorted by how many points they currently have
        pointLists = {}
        #Contains a list of points in the event from high to low
        pointTotals = []
        #Counts our groupings for each point amount
        countPoints = {}
        #Add all players to pointLists
        for player in playerlist:
            #If this point amount isn't in the list, add it
            if "%s_1"%player.score not in pointLists:
                pointLists["%s_1"%player.score] = []
                countPoints[player.score] = 1
            
            #Breaks the players into groups of their current points up to the max group allowed.
            #Smaller groups mean faster calculations
            if len(pointLists["%s_%s"%(player.score, countPoints[player.score])]) > MAXGROUP:
                countPoints[player.score] += 1
                pointLists["%s_%s"%(player.score, countPoints[player.score])] = []
            #Add the NDB key of our player to the correct group
            pointLists["%s_%s"%(player.score, countPoints[player.score])].append(player.key)
            #and the list of all playerkeys
            playerkeylist.append(player.key)
        logging.info(pointLists)
        #Add all points in use to pointTotals
        for points in pointLists:
            pointTotals.append(points)
            
        #Sort our point groups based on points
        pointTotals.sort(reverse=True, key=lambda s: int(s.split('_')[0]))
        logging.info( "Point toals after sorting high to low are: %s"%pointTotals)
        
        #Firstly lets deal with the bye situation
        #Do we have an uneven number of players involved?
        if len(playerlist) % 2 > 0:
            #yep, find the lowest scored player who hasn't yet been byed
            pointTotalsIndex = -1
            while pointTotalsIndex < 0:
                playerkeysAtThisLevel = pointLists[pointTotals[pointTotalsIndex]]
                logging.info(pointTotals[pointTotalsIndex])
                logging.info(playerkeysAtThisLevel)
                #sift out those who have already been byed
                #copy for iteration
                keysforiteration = playerkeysAtThisLevel
                logging.info(keysforiteration)
                for playerkey in keysforiteration:
                #the fuck is going on in this loop?  It doesn't always run for every item in the iteration list
                    player = playerkey.get()
                    logging.info(player)
                    if player.bye:
                        logging.info("already had a bye, removing")
                        playerkeysAtThisLevel.remove(playerkey)
                logging.info(playerkeysAtThisLevel)
                #anyone left?
                if len(playerkeysAtThisLevel) > 0:
                    #yep, pick someone
                    byePlayerkey = random.choice(playerkeysAtThisLevel)
                    #remove them from the pointslist so we don't try and pair them again
                    pointLists[pointTotals[pointTotalsIndex]].remove(byePlayerkey)
                    playerkeylist.remove(byePlayerkey)
                    #log it
                    self.assignBye(byePlayerkey, roundkey)
                    #set our index so we can escape
                    pointTotalsIndex = 0
                else:
                    #nope, move up the scorechart
                    pointTotalsIndex -= 1
        
        #That's the bye dealt with, pair everyone else
        #Create the graph object and add all players to it
        bracketGraph = nx.Graph()
        bracketGraph.add_nodes_from(playerkeylist)
        
        logging.info(playerkeylist)
        logging.info(bracketGraph.nodes())

        #Create edges between all players in the graph who haven't already played
        #general approach: 2 tier matching graph, players with the same score are given tier 1 weighting (11-20)
        #players that differ by one scoring boundary have a tier 2 weighting (1-10)
        #then run an optimised weight match algorithm to generate pairings
        for playerkey,opponentkey in it.combinations(bracketGraph.nodes(),2):
            player = playerkey.get()
            if opponentkey not in player.opponents:
                #these two haven't played yet
                opponent = opponentkey.get()
                #Are these players at the same points level?
                if player.score == opponent.score:
                    #sure are, weight these two as 'tier 1' match
                    wgt = random.randint(11, 20)
                #Are they within one score bracket of each other?
                elif abs(pointTotals.index("%s_1"%player.score) - pointTotals.index("%s_1"%opponent.score)) < 2:
                    #yep, maybe, check higher score person hasn't been paired down already then assign tier 2 match
                    if player.score > opponent.score:
                        if not(player.pairedDown):
                            wgt = random.randint(1, 10)
                    else:
                        if not(opponent.pairedDown):
                            wgt = random.randint(1, 10)
                #Create edge
                bracketGraph.add_edge(playerkey, opponentkey, weight=wgt)

        #Generate pairings from the created graph
        #maxcardinality ensures maximum matchups are generated, regardless of weighting
        pairings = nx.max_weight_matching(bracketGraph,maxcardinality=True)

        logging.info(bracketGraph.edges(data= True))
        logging.info(pairings)

        #Actually pair the players based on the matching we found
        for p in pairings:
            logging.info(p)
            if p in playerkeylist:
                logging.info(pointLists[points])
                self.pairPlayers(p, pairings[p], openTable, roundkey)
                openTable += 1
                playerkeylist.remove(p)
                playerkeylist.remove(pairings[p])

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
                #TODO: Calculate SOS
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
            player.opponents = []
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