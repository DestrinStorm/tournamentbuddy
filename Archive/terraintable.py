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
class Results(webapp2.RequestHandler):
    def post(self):
        self.response.write('<br>')
        for x in range(int(cgi.escape(self.request.get('numtables')))):
        	self.response.write(str(x+1)+' ')
		self.response.write(random.choice(terraintable[random.choice(regions)]))
		self.response.write('<br>')
        self.response.write('</pre></body></html>')