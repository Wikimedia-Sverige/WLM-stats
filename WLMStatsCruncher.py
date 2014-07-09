#!/usr/bin/python
# -*- coding: utf-8  -*-
#
# By: André Costa, Wikimedia Sverige
# License: MIT
# 2014
#
# Statistics cruncher for Wiki Loves Monuments in Sweden
# a reboot of the WLM stats-getter (WLM2011, 2011-09-30)
# designed to crunch the data from WLMStats.py
#
#
#Random notes
#Ladda json:
#Kan inte göra en initial "unik" sökning. Då år, uppladdare etc. skiljer sig.

#För var statistiktyp (ex. användare)

#users = {}
#for k,v in imagestats.iteritems():
	#user, monument_id = v[user], v[idno]
	#if not user in users.keys():
		#users[user]={}
	#if not monument_id in users[user].key():
		#users[user][monument_id] = 1
	#else:
		#users[user][monument_id] += 1

#Then:
#no users:					len(users)
#no unique objects per user:	len(users[user])
#no images per user:			
#							sum=0
#							for k,v in users[user].iteritems():
#								sum +=v

#in images [u'monument_id', u'muni', u'copyright', u'title', u'problematic', u'created', u'in_list', u'county', u'uploader', u'photographer', u'monument_type']

import codecs, ujson
import datetime #for timestamps  in log
import dataDicts #redo as json?

class WLMStatsCruncher(object):
    def versionInfo(self):
        '''Version specific variables'''
        self.scriptversion = u'0.1'
        self.scriptname = u'WLM_Statistics_Cruncher'
        self.WLMStatsVersion = u'0.1' # the version of WLMStats for which the cruncher was designed

    def loadVariables(self, test):
        '''semi-stable variables which are not project specific'''
        self.logFilename = u'¤WLMStatsCruncher.log'
        self.output = "output/crunch-"
        self.reqKeys = [u'type', u'data', u'WLMStatsVersion']
        self.supportedTypes = ['images',]
        
    def __init__(self, filename, verbose=False, test=False):
        '''Sets up environment, loads data file, triggers run/test
           :param filename: the *-images.json output of WlmStats
        '''
        self.versionInfo()
        varErrors = self.loadVariables(test)
        if varErrors:
            self.log.write(u'%s\n' %varErrors)
            exit(1)
        self.log = codecs.open(self.logFilename, 'a', 'utf-8')
        
        #Open infile, check validity and store data as self.indata
        try:
            fIn = codecs.open(filename, 'r', 'utf-8')
            jIn = ujson.load(fIn)
            #check necessary keys are present
            if not all(k in jIn.keys() for k in self.reqKeys):
                raise MyException(u'Indata missing one (at least) of the reguired keys. Found: %s' %', '.join(jIn.keys()))
            ##check verison number agrees with self.WLMStatsVersion
            if jIn['WLMStatsVersion'] != self.WLMStatsVersion:
                raise MyException(u'Wrong WLMStatsVersion. Expected: %s, found: %s' %(self.WLMStatsVersion, jIn['WLMStatsVersion']))
            ##check type in self.supportedTypes and set self.indataType
            self.indataType = jIn['type']
            if not self.indataType in self.supportedTypes:
                raise MyException(u'Wrong indataType. Found: %s' %jIn['type'])
            self.indata = jIn['data'] 
        except MyException, e:
            if verbose:
                print u'Error reading input file: %s\n' %e
            self.log.write(u'Error reading input file: %s\n' %e)
            exit(1)
        #confirm succesful load to log together with timestamp
        self.log.write(u'-----------------------\n%s: Successfully started %srun.\n' %(datetime.datetime.utcnow(), 'test ' if test else ''))
        
        try:
            self.fCrunch  = codecs.open(u'%s.json' %self.output, 'w', 'utf-8')
        except IOError, e:
            self.log.write(u'Error creating output files: %s\n' %e)
            exit(1)
        
        #ready to run
        
        #run
        try:
            if test:
                self.run(verbose=True, testing=True)
            else:
                self.run(verbose=verbose)
        except MyException, e:
            if verbose:
                print u'Terminated prematurely, please check log file'
            self.log.write(u'Error during run: %s\n' %e)
            exit(1)
        else:
            #confirm sucessful ending to log together with timestamp
            if verbose:
                print u'Successfully reached end of run'
            self.log.write(u'%s: Successfully reached end of %srun.\n' %(datetime.datetime.utcnow(), 'test ' if test else ''))
        #done
        self.log.close()
    
    def run(self, datatype=None, verbose=False, testing=False):
        '''will essentially only be a list of called functions dealing 
        with each bit and then outputting it.
        Checks self.indataType to decide which list to follow'''
        
        self.analyseUsers()
        
        #Done
    
    def analyseUsers(self):
        users, blanks = self.analyseSimple('uploader')
        
        #test
        ##no. usets = len(users)
        ##no. images (per user) = len(users[user])
        ##no uniques (per user) = sum(users[user].values())
        self.log.write('\n\nno. users: %d\n' %len(users))
        self.log.write('no. blanks: %d\n' %blanks)
        self.log.write('no. images\tno. uniques\tusername\n')
        for k, v in users.iteritems():
            self.log.write('%d\t%d\t%s\n' %(sum(v.values()), len(v), k))
    
    def analyseSimple(self, key):
        '''analyses how many images (total and unique) there are for a given key
        return: a tuple (results, blanks) where
            results is a dict with {key:{monument_id:images-with-that-id-and-key}}
            blanks is the total number of images without a valid monuent_id
        raises: MyException if key not found'''
        if not key in self.indata.values()[0].keys():
            raise MyException('analyseSimple() called with invalid key %s' %key)
        results = {}
        blanks = 0
        for k,v in self.indata.iteritems():
            value, monument_id = v[key], unicode(v['monument_id'])
            #skip any entries without valid monument_id
            if monument_id == '[]':
                blanks +=1
                continue
            if not value in results.keys():
                results[value]={}
            if not monument_id in results[value].keys():
                results[value][monument_id] = 1
            else:
                results[value][monument_id] += 1
        return results, blanks

class MyException(Exception):
    pass

if __name__ == '__main__':
    import sys
    usage = '''Usage: python Cruncher.py infile option
\tfile: the json indata file
\toption (optional): can be set to:
\t\tverbose:\t toggles on verbose mode with additional output to the terminal
\t\ttest:\t\t toggles on testing (a verbose and limited run)
example: python WLMStatsCruncher.py "./output/wlm-se.test-images.json" verbose
'''
    argv = sys.argv[1:]
    if len(argv) == 1:
        WLMStatsCruncher(argv[0])
    elif len(argv) == 2:
        if argv[1] == 'test':
            WLMStatsCruncher(argv[0], test=True)
        elif argv[1] == 'verbose':
            WLMStatsCruncher(argv[0], verbose=True)
        else:
            print usage
    else:
        print usage
#EoF
