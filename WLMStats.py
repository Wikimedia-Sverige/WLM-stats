#!/usr/bin/python
# -*- coding: utf-8  -*-
#
# By: André Costa, Wikimedia Sverige
# License: MIT
# 2014
#
# Statistics retriever for Wiki Loves Monuments in Sweden
# a reboot of the WLM stats-getter (WLM2011, 2011-09-30)
# based heavily on the EuropeanaHarvest
#
## Notes that should live elsewhere
#settings file
##{
##  "bbr": {
##	"table"           : "se-bbr", #table name in heritage (without lang code)
##	"defaultWPCat"    : [u"Listor över fornminnen i Sverige per kommun"], #list of kategories on sv.wp containing the lists
##  "commons_cat"     : "Protected buildings in Sweden with known IDs",   #tracking category on commons
##	"commons_template": "BBR",  #template on commons indicating an image is of this type
##	"url_prefix"      : "http://kulturarvsdata.se/raa/fmi/html/",  #url pattern prefixing the id (if there is a postfix or the id is modified (e.g. whitespace removed) then this needs to be expanded)
##	"per_muni"        : true,     #false if objects are not sorted by municipality (e.g. se-ship)
##  "url_promised"    : true      #false if external link cannot be used for ALL objects
##  },

import codecs, ujson
import datetime #for timestamps  in log
import WikiApi as wikiApi
import HeritageApi as heritageApi
import dataDicts #redo as json?

class WLMStats(object):
    def versionInfo(self):
        '''Version specific variables'''
        self.scriptversion = u'0.1'
        self.scriptname = u'WLM_Statistics'
        self.infoTemplate = [u'Template:Information',] #supported info templates - based on what is suppported by parseImageInfo
        self.commonsMetadataExtension = 1.2 # the version of the extention for which the script was designed
    
    def loadVariables(self, test):
        '''semi-stable variables which are not project specific'''
        self.logFilename = u'WLMStats.log'
        self.heritage_siteurl = 'https://tools.wmflabs.org/heritage/api'
        self.commons_siteurl = 'https://commons.wikimedia.org'
        self.output = "output/wlm-se"
        self.settings_file = u'settings.json'
        self._test_gcmlimit = 5
        self._test_limit = 15

        
        #distingusih testdata
        if test:
            self.output += u'.test'
            self.settings_file = u'settings.test.json'
        
        #load settings file
        try:
            f = codecs.open(self.settings_file, 'r', 'utf-8')
            self.settings = ujson.load(f)
            f.close()
        except IOError, e:
            return u'Error opening settings file: %s' %e
            exit(1)
        except (ValueError, KeyError), e:
            return u'Error processing settings file as the expected json. Are you sure it is still valid?: %s' %e
            exit(1)

    def __init__(self, verbose=False, test=False):
        '''Sets up environment, loads project file, triggers run/test
           Requires no parameters:
        '''
        self.versionInfo()
        varErrors = self.loadVariables(test)
        self.log = codecs.open(self.logFilename, 'a', 'utf-8')
        if varErrors:
            self.log.write(u'%s\n' %varErrors)
            exit(1)
        self.data = {} #container for all the info, using pageid as its key
        
        #confirm succesful load to log together with timestamp
        self.log.write(u'-----------------------\n%s: Successfully started %srun.\n' %(datetime.datetime.utcnow(), 'test ' if test else ''))
        
        #Look for config file and connect to apis
        scriptidentify = u'%s/%s' %(self.scriptname,self.scriptversion)
        try:
            import config
            self.hApi = heritageApi.HeritageApi.setUpApi(user=config.user, site=self.heritage_siteurl, scriptidentify=scriptidentify, verbose=verbose)
            #self.wpApi = wikiApi.WikiApi.setUpApi(user=config.user, password=config.password, site=self.commons_siteurl, scriptidentify=scriptidentify, verbose=verbose) 
        except ImportError:
            from getpass import getpass #not needed if config file exists
            user=getpass(u'Username:')
            self.hApi = heritageApi.HeritageApi.setUpApi(user=user, site=self.heritage_siteurl, scriptidentify=scriptidentify, verbose=verbose)
            #self.wpApi = wikiApi.WikiApi.setUpApi(user=user, password=getpass(), site=self.commons_siteurl, scriptidentify=scriptidentify, verbose=verbose)
        
        #Create output files (so that any errors occur before the actual run)
        try:
            self.fState= codecs.open(u'%s.state' %self.output, 'w', 'utf-8')
            self.fMuni= codecs.open(u'%s-muni.csv' %self.output, 'w', 'utf-8')
        except IOError, e:
            self.log.write(u'Error creating output files: %s\n' %e)
            exit(1)
        
        #ready to run
        
        #run
        if test:
            runError = self.run(verbose=True, testing=True)
        else:
            runError = self.run(verbose=verbose)
        
        if runError:
            self.log.write(u'Error during run: %s\n' %runError)
            exit(1)
        
        #confirm sucessful ending to log together with timestamp
        self.log.write(u'%s: Successfully reached end of %srun.\n' %(datetime.datetime.utcnow(), 'test ' if test else ''))
        self.log.close()

    def run(self, verbose=False, testing=False):
        '''Runs through the specified categories, sets up a dict with the imageinfo for each image
           then checks the parsed content for each image page to identify any of the specified id-templates
           and if found stores the associate sourcelink.
        '''
        
        #get the by muni statistics for all types with per_muni=true
        muniStatsRaw = {}
        for k, v in self.settings.iteritems():
            if v['per_muni']:
                self.hApi.getMuniStatistics(table=v['table'], muniStats=muniStatsRaw, debug=False)
        #analyse and output
        self.outputCSV(self.analyseMuniStatistics(muniStatsRaw), self.fMuni)
        
        #get all heritage_objects from heritage api
        monuments = {}
        for k, v in self.settings.iteritems():
            monuments[k] = self.hApi.getAllEntries(table=v['table'], verbose=True)
        #output to .state file + make it possible to run from this point
        ##repackage to have table+id as key in dict
        
        #getImageInfos() for the relevant category - don't need iiprop:mime|url just iiprop:user|extmetadata
        ##set monument_type(s) using any tracker categories (if none found then add monument_type:missing
        #output to .state file + make it possible to run from this point
        
        #for each image getContent(),
        ##if one of the  monument_type(s) has url_promised=false then also need to retrieve prop:wikitext otherwise just prop:templates|externallinks
        ### if url_promised
        #### for each monument_type identify all matching id's from externallinks
        ### if !url_promised
        #### check that right template is present. If so then isolate template and id in wikitext (most likely needs a specific parser)
        #use monument_type+id and extmetadata to isolate relevant data
        ## if monument_type+id not in heritage_objects then add not_in_list:true
        #output to .state file + make it possible to run from this point
        
        #consider looking in external database for items with not_in_list:true
        #output to .state file + make it possible to run from this point
        
        #analyse image data on both an individual level and on a per-unique-id basis and output to
        ##output to csv(s) (f?)
        
        return None
    
    def analyseMuniStatistics(self, muniStatsRaw):
        '''analyses hApi.getMuniStatistics results and returns output formated for outputCSV()'''
        #muniStatsRaw now has the form MuniName': {table1: {'illustrated': int, 'total': int, 'coords': int}, u'table2': ...
        muniStats = {}
        for k, v in muniStatsRaw.iteritems():
            muniStats[k] = {
                'muni_code': dataDicts.muni_name2code[k].zfill(4) if k in dataDicts.muni_name2code.keys() else None,
                'muni_name': k
                }
            aggregate = {}
            for t, vv in v.iteritems():
                total = vv['total']
                for prop, val in vv.iteritems():
                    if prop in aggregate.keys():
                        aggregate[prop] += val
                    else:
                        aggregate[prop] = val
                    muniStats[k][u'%s-%s' %(t,prop)] = '%d' %val
                    if prop == 'total':continue
                    if total == 0:
                        muniStats[k][u'%s-%s-percentage' %(t,prop)] = None
                    else:
                        muniStats[k][u'%s-%s-percentage' %(t,prop)] = '%.3f' %(val/float(total))
            total = aggregate['total']
            for prop, val in aggregate.iteritems():
                muniStats[k][u'sum-%s' %(prop)] = '%d' %val
                if prop == 'total':continue
                if total == 0:
                    muniStats[k][u'sum-%s-percentage' %(prop)] = None
                else:
                    muniStats[k][u'sum-%s-percentage' %(prop)] = '%.3f' %(val/float(total))
        
        #set up _structure
        muniStats['_structure'] = {}
        for k, v in muniStats.iteritems().next()[1].iteritems():
            muniStats['_structure'][k] = False
        return muniStats
    
    def outputCSV(self, data, f):
        '''output the given data as a "|"-separated csv
        (new line characters are replaced by ¤ and "|"-symbols by "!")
        data must be a dict with a _structure-key
        the _structure object should be a dict with the same structure as
        the real objects but the value should be True for any properties
        which are lists.
        No non-duplicated information should be stored in the name of
        the main keys.
        '''
        #consider using _structure to tag ints and floats
        
        #analyse structure and output header
        key_names = data['_structure'].keys()
        list_keys=[]
        for k, v in data['_structure'].iteritems():
            if v: list_keys.append(k)
        f.write(u'#%s\n' %'|'.join(key_names))
        
        #output data
        for k,v in data.iteritems():
            if k == '_structure': continue
            for kk, vv in v.iteritems():
                if vv is None:
                    v[kk] = ''
                if kk in list_keys:
                    v[kk] = ';'.join(v[kk])
                v[kk] = v[kk].replace('|','!').replace('\n',u'¤')
            #output in same order as header
            vals = []
            for kk in key_names:
                try:
                    vals.append(v[kk])
                except KeyError, e: #no guarantee that each column exist for each row
                    vals.append('')
            f.write(u'%s\n' %'|'.join(vals))
        f.close()


if __name__ == '__main__':
    import sys
    usage = '''Usage: python WLMStats.py option
\toption (optional): can be set to:
\t\tverbose:\t toggles on verbose mode with additional output to the terminal
\t\ttest:\t\t toggles on testing (a verbose and limited run)'''
    argv = sys.argv[1:]
    if len(argv) == 0:
        WLMStats()
    elif len(argv) == 1:
        if argv[0] == 'test':
            WLMStats(test=True)
        elif argv[0] == 'verbose':
            WLMStats(verbose=True)
        else:
            print usage
    else:
        print usage
#EoF
