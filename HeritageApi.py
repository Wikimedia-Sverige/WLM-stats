#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Module for connecting to the Heritage API
# Mainly set up to reuse pycurl setup from WikiApi
# and hide api calls behind functions

#----------------------------------------------------------------------------------------

import WikiApi as wikiApi

class HeritageApi(wikiApi.WikiApi):
    '''
    When possible connect through the api
    Need to override setUpApi
    Should replace login/token/logout by dummyfunction to prevent these from being executed
    '''
    
    #dummy functions to prevent these from being executed
    def login(self, userName, userPass, verbose=True): dummyFunction(u'login')
    def setToken(self, token, verbose=True): dummyFunction(u'setToken')
    def setEditToken(self, verbose=True): dummyFunction(u'setEditToken')
    def clearEditToken(self): dummyFunction(u'clearEditToken')
    def logout(self): dummyFunction(u'logout')
    def dummyFunction(self, name):
        print u'%s() not supported by HeritageApi' %name
        exit(2)
        
    @classmethod
    def setUpApi(cls, user, site, scriptidentify=u'WLM_Statistics/0.5', verbose=False):
        '''
        Creates a HeritageApi object
        '''
        #Provide url and identify (using e-mail)
        heritage = cls('%s/api.php' %site, user, scriptidentify)
        return heritage
    
    def apiaction(self, action, form=None):
        return self._apiurl + "?action=" + action + "&format=json"
    
    def getMuniStatistics(self, table, muniStats=None, debug=False):
        '''
        Fetches a list of the statistics for the specified table/country 
        for each municipality.
        :param table: the value for stcountry e.g. se-bbr
        :return: a dict of municipalities containing table statistics (as dicts)
        '''
        if muniStats is None:
            muniStats = {}
        jsonr = self.httpGET("statisticsdb", [('limit', '0'),
                                              ('stcountry', table.encode('utf-8'))]
                                           , debug=debug)
        if debug:
            print u'getMuniStatistics(): table=%s\n' %table
            print jsonr
        
        #find errors
        if len(jsonr) != 1 or not u'monuments' in jsonr.keys():
            print u'HeritageApi is not happy getMuniStatistics(%s) got %s' %(table, josnr)
            return None
        
        for m in jsonr['monuments']:
            if not m['municipality'] in muniStats.keys():
                muniStats[m['municipality']] = {}
            muniStats[m['municipality']][table] ={
                'total':int(m['st_total']),
                'illustrated':int(m['st_image']),
                'coords':int(m['st_coordinates'])
                }
        
        return muniStats
        
    def getAllEntries(self, table, entries=None, limit=5000, debug=False, verbose=True):
        '''
        Fetches a list of the objects in for the specified table/country 
        :param table: the value for srcountry e.g. se-bbr
        :param limit: how many values to request in one go (defaults to 5000)
        :return: list of monument objects (dicts) with the following parameters
           "country|id|name|adm1|municipality|lat|lon|image|source" where
               adm1: is county
               source: is the permanent url of the list article
        '''
        if entries is None:
            entries = []
        
        jsonr = self.httpGET("search", [('srcountry', table.encode('utf-8')),
                                        ('props', u'country|id|name|adm1|municipality|lat|lon|image|source'),
                                        ('limit', unicode(limit))]
                                     , debug=debug)
        if debug:
            print u'getAllEntries(): lang=%s\n' %lang
            print jsonr
        
        #find errors
        if len(jsonr) == 0 or not u'monuments' in jsonr.keys():
            print u'HeritageApi is not happy getMuniStatistics(%s) got %s' %(table, josnr)
            return None
        
        monuments = jsonr['monuments']
        
        #these are returned 100 at a time so now get the rest
        while 'continue' in jsonr.keys():
            if verbose:
                print 'Retrieved %d objects' %len(monuments)
            jsonr = self.httpGET("search", [('srcountry', table.encode('utf-8')),
                                            ('props', u'country|id|name|adm1|municipality|lat|lon|image|source'),
                                            ('limit', unicode(limit)),
                                            ('srcontinue', jsonr['continue']['srcontinue'].encode('utf-8'))]
                                         , debug=debug)
            if not u'monuments' in jsonr.keys():
                print 'That was unexpected.' #ok so maybee the message could be a bit more informative
                return None
            monuments += jsonr['monuments']
        
        return monuments
    
#End of HeritageApi()
