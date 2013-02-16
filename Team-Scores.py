#!/usr/bin/python
"""
Calculate TrueSkill and ELO values for teams in the Planet Kubb Wiki
"""

import urllib
import urllib2
import simplejson
import datetime
from simplemediawiki import MediaWiki
from trueskill import *                       # http://pythonhosted.org/trueskill/


class CalcSkill():
    """ Bot to calculate TrueSkill and ELO for Planet Kubb Teams """

    def __init__(self):
        """
        Iniitalize our containers to store state information.
        """
        self.teams = {}     # We will use this to keep the scores for teams

    def UpdateWiki(self):
        """
        Write the contents of the teams dictionary back into the wiki
        """
        print "Stub here for writing to the wiki."
        return True

    def ShowTeams(self):
        """
        Print out the team dictionary to see what's going on.
        """
        print "== Team Scores =="
        print "Team, MU, Sigma"
        for team in self.teams:
            print "\"%s\",%f,%f" % (team, self.teams[team].mu, self.teams[team].sigma)

    def RunQuery(self, query):
        """
        Helper function to take a query and return the JSON data
        """

        query_param = urllib.quote_plus(query)
        url = "http://wiki.planetkubb.com/w/api.php?action=ask&query=%s&format=json" % query_param
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
            print "''Iniializing team reating for %s.''" % team_a
            self.teams[team_a] = Rating()
        if not team_b in self.teams:
            print "''Iniializing team reating for %s.''" % team_b
            self.teams[team_b] = Rating()

        if team_a == winner:
            self.teams[team_a], self.teams[team_b] = rate_1vs1(self.teams[team_a], self.teams[team_b])
        if team_b == winner:
            self.teams[team_b], self.teams[team_a] = rate_1vs1(self.teams[team_b], self.teams[team_a])
        # if tie
            #self.teams[team_a], self.teams[team_b] = rate([self.teams[team_a], self.teams[team_b]], ranks=[0,0])

        print "Post match scores: %s %f %s %f" % (team_a, self.teams[team_a].mu, team_b, self.teams[team_b].mu)

    def ProcessMatch(self, team_a, team_b, winner):
        print "%s v. %s => WIN: %s" % (team_a, team_b, winner)
        self.UpdateTrueSkill(team_a, team_b, winner)

    def ProcessBracket(self, event, bracket):
            query = ''.join(['[[Category:Match]]', '[[Has event::%s]]' % event, '[[Has bracket::%s]]' % bracket,
                '|?Has bracket', '|?Has tournament stage', '|?Has bracket row', '|?Has winning team',
                '|?Has losing team', '|?Has team A', '|?Has team B', '|?Has winner'])
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
                print "  No matches found for %s %s." % (event, bracket)

    def ProcessEvent(self, event):
        """
        Handle the matches for a single event.
        Do this in order of brackets.
        """
        brackets = ['Round Robin', 'Swedish', '2nd Consolation', 'Consolation', 'Championship']
        for bracket in brackets:
            print "=== Processing %s bracket. ===" % bracket
            self.ProcessBracket(event, bracket)

    def ProcessEvents(self):
        """
        Get the list of events that we should process.
        We mainly exclude events that indicates exclusion, and ignore events that have no matches.
        """
        query = ''.join(['[[Category:Event]]', '[[Has event type::Tournament]]', '[[Exclude stats::False]]',
            '[[Has match count::>>0]]', '|?Has team count', '|?Has match count', '|?Has start date',
            '|sort=Has start date', '|order=asc'])
        event_count, events = self.RunQuery(query)

        if event_count > 0:
            for pagename, event in events:
                print "== Processing %s ==" % event['fulltext']
                event_date = datetime.datetime.fromtimestamp(int(event['printouts']['Has start date'][0]))
                print "Start date: %s  Team count: %d  Match count: %d" % (event_date.ctime(), event['printouts']['Has team count'][0], event['printouts']['Has match count'][0])
                self.ProcessEvent(event['fulltext'])

    def main(self):
        self.ProcessEvents()
        self.ShowTeams()
        self.UpdateWiki()


# Run
if __name__ == '__main__':
    bot = CalcSkill()
    bot.main()

