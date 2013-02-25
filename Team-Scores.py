#!/usr/bin/python
"""
Calculate TrueSkill and ELO values for teams in the Planet Kubb Wiki
"""

import ConfigParser
import urllib
import urllib2
import simplejson
import datetime
import time
from simplemediawiki import MediaWiki
import math
import operator
from trueskill import *                       # http://pythonhosted.org/trueskill/


class CalcSkill():
    """ Bot to calculate TrueSkill and ELO for Planet Kubb Teams """
    config = []
    stats = {}

    def __init__(self):
        """
        Iniitalize our containers to store state information.
        """
        self.get_config()
        self.teams = {}     # We will use this to keep the scores for teams
        self.match_counter = 0
        self.stats['confirm'] = 0
        self.stats['upset'] = 0

    def get_config(self, config_file='planet-kubb.cfg'):
        try:
            self.config = ConfigParser.ConfigParser()
            self.config.read(config_file)
        except IOError:
            print "Cannot open %s." % config_file

    def UpdateWiki(self):
        """
        Write the contents of the teams dictionary back into the wiki
        """
        wiki = MediaWiki(self.config.get('PlanetKubb', 'API'))
        wiki.login(self.config.get('KubbBot', 'Username'), self.config.get('KubbBot', 'Password'))

        # We need an edit token
        c = wiki.call({'action': 'query', 'titles': 'Foo', 'prop': 'info', 'intoken': 'edit'})
        print c
        my_token = c['query']['pages']['-1']['edittoken']
        print "Edit token: %s" % my_token

        print "== Updating wiki with new scores =="
        for team in self.teams:
            print "\"%s\",%f,%f" % (team, self.teams[team].mu, self.teams[team].sigma)

            c = wiki.call({
                'action': 'sfautoedit',
                'form': 'Team',
                'target': team,
                'Team[TrueSkill mu]': "%s" % self.teams[team].mu,
                'Team[TrueSkill sigma]': "%s" % self.teams[team].sigma,
                'token': my_token})
            print c

    def ShowTeams(self):
        """
        Print out the team dictionary to see what's going on.
        """
        print "\n\nTEAM LIST"
        for team in self.teams:
            print "\"%s\",%f,%f" % (team, self.teams[team].mu, self.teams[team].sigma)

    def ShowStats(self):
        print "Confirms: %d  Upsets: %d" % (self.stats['confirm'], self.stats['upset'])

    def RunQuery(self, query):
        """
        Helper function to take a query and return the JSON data
        """

        query_param = urllib.quote(query)
        url = "http://wiki.planetkubb.com/w/api.php?action=ask&query=%s&format=json" % query_param
        # print url
        req = urllib2.Request(url, None)
        opener = urllib2.build_opener()

        f = opener.open(req)
        data = simplejson.load(f)

        # Return the count of results, and the JSON array for the results
        result_count = len(data['query']['results'])
        if result_count > 0:
            result_data = data['query']['results'].items()
        else:
            result_data = None

        return result_count, result_data

    def UpdateTrueSkill(self, team_a, team_b, winner):
        # Initialize the team Rating objects if not present
        if not team_a in self.teams:
            print "NEW TEAM: %s" % team_a
            self.teams[team_a] = Rating()
        if not team_b in self.teams:
            print "NEW TEAM: %s." % team_b
            self.teams[team_b] = Rating()

        print "SCORES BEFORE: %s %f(%f) %s %f(%f)" % (team_a, self.teams[team_a].mu, self.teams[team_a].sigma,
            team_b, self.teams[team_b].mu, self.teams[team_b].sigma)

        if ((self.teams[team_a].mu > self.teams[team_b].mu) and (team_a == winner) or
            (self.teams[team_b].mu > self.teams[team_a].mu) and (team_b == winner)):
            self.stats['confirm'] += 1
        if ((self.teams[team_a].mu > self.teams[team_b].mu) and (team_b == winner) or
            (self.teams[team_b].mu > self.teams[team_a].mu) and (team_a == winner)):
            self.stats['upset'] += 1

        if team_a == winner:
            self.teams[team_a], self.teams[team_b] = rate_1vs1(self.teams[team_a], self.teams[team_b])
        if team_b == winner:
            self.teams[team_b], self.teams[team_a] = rate_1vs1(self.teams[team_b], self.teams[team_a])
        # if tie
            #self.teams[team_a], self.teams[team_b] = rate([self.teams[team_a], self.teams[team_b]], ranks=[0,0])

        print "SCORES AFTER: %s %f(%f) %s %f(%f)" % (team_a, self.teams[team_a].mu, self.teams[team_a].sigma,
            team_b, self.teams[team_b].mu, self.teams[team_b].sigma)

    def ProcessMatch(self, team_a, team_b, winner):
        self.match_counter += 1
        print "%d. %s v. %s => WIN: %s" % (self.match_counter, team_a, team_b, winner)
        self.UpdateTrueSkill(team_a, team_b, winner)

    def ProcessBracket(self, event, bracket, stage=""):
            stage_query = ""
            if stage != "":
                stage_query = "[[Has tournament stage::%s]]" % stage
            query = ''.join(['[[Category:Match]]', '[[Has event::%s]]' % event, '[[Has bracket::%s]]' % bracket,
                stage_query, '|?Has bracket', '|?Has tournament stage', '|?Has bracket row', '|?Has winning team',
                '|?Has losing team', '|?Has team A', '|?Has team B', '|?Has winner', '|limit=500'])
            match_count, matches = self.RunQuery(query)

            if match_count > 0:
                for pagename, match in matches:
                    team_a = match['printouts']['Has team A'][0]['fulltext']
                    team_b = match['printouts']['Has team B'][0]['fulltext']
                    try:
                        winner = match['printouts']['Has winning team'][0]['fulltext']
                    except:
                        winner = None
                    self.ProcessMatch(team_a, team_b, winner)
            else:
                print "No matches found for %s %s %s." % (event, bracket, stage)

    def ProcessEvent(self, event):
        """
        Handle the matches for a single event.
        Do this in order of brackets.
        """
        brackets = ['Round Robin', 'Swedish', '2nd Consolation', 'Consolation', 'Championship']
        staged = ['2nd Consolation', 'Consolation', 'Championship']
        swedish = ['Round 1', 'Round 2', 'Round 3', 'Round 4', 'Round 5', 'Round 6', 'Round 7', 'Round 8', 'Round 9']
        stages = ['Round of 64', 'Round of 32', 'Round of 16', 'Quarterfinals', 'Semifinals', 'Third place', 'Finals']

        for bracket in brackets:
            if bracket == 'Round Robin':
                print "BRACKET: %s" % bracket
                self.ProcessBracket(event, bracket)
            if any(bracket in s for s in staged):
                for stage in stages:
                    print "BRACKET: %s STAGE: %s" % (bracket, stage)
                    self.ProcessBracket(event, bracket, stage)
            if bracket == 'Swedish':
                for stage in swedish:
                    print "BRACKET: %s STAGE: %s" % (bracket, stage)
                    self.ProcessBracket(event, bracket, stage)

    def ProcessEvents(self):
        """
        Get the list of events that we should process.
        We mainly exclude events that indicates exclusion, and ignore events that have no matches.
        """
        query = ''.join(['[[Category:Event]]', '[[Has event type::Tournament]]', '[[Exclude stats::False]]',
            '[[Has match count::>>0]]', '[[Has start date::+]]', '|?Has team count', '|?Has match count', '|?Has start date',
            '|sort=Has start date', '|order=asc'])
        event_count, events = self.RunQuery(query)

        # First sort the events by date (the SMW API should be doing this, but it isn't as of 1.9 alpha)
        if event_count > 0:
            my_events = {}
            for pagename, event in events:
                my_events[event['fulltext']] = event['printouts']['Has start date'][0]

        # Now sort the dictionary
        sorted_events = sorted(my_events.iteritems(), key=operator.itemgetter(1))

        # Now process
        for event, date in sorted_events:
            event_date = datetime.datetime.fromtimestamp(int(date))
            print "\n\nEVENT: Processing %s (%s)" % (event, event_date)
            self.ProcessEvent(event)

    def main(self):
        self.ProcessEvents()
        self.ShowTeams()
        self.ShowStats()
        self.UpdateWiki()


# Run
if __name__ == '__main__':
    bot = CalcSkill()
    bot.main()

