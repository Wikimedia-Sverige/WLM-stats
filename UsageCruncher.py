#!/usr/bin/python
# -*- coding: utf-8  -*-
#
# By: André Costa, Wikimedia Sverige
# License: MIT
# 2014
#
# Small extra module to compare image use in tables to images uploaded
# in the competition. Could be integrated into WLMStatsCruncher if all
# files were analysed at once
# 
# @TODO:
# Integrate in main cruncher
#
import codecs, ujson
import datetime #for timestamps  in log

class UsageCruncher(object):
    def versionInfo(self):
            '''Version specific variables'''
            self.scriptversion = u'0.21'
            self.scriptname = u'WLM_Usage_Cruncher'
            self.WLMStatsVersion = u'0.21' # the version of WLMStats for which the cruncher was designed
    
    def loadVariables(self, test):
        '''semi-stable variables which are not project specific'''
        self.logFilename = u'¤WLMUsageCruncher.log'
        self.output = "analysis/"
        self.commons_siteurl = 'https://commons.wikimedia.org'
        self.reqKeys = [u'type', u'data', u'WLMStatsVersion', u'settings']
        self.supportedTypes = ['images','monuments']
        
        #load dataDict file
        try:
            f = codecs.open('dataDicts.json','r','utf8')
            self.dataDicts = ujson.load(f)
            f.close()
        except IOError, e:
            return u'Error opening dataDicts file: %s' %e
            exit(1)
    
    def load(self, filename, verbose=False, test=False):
        '''loads and returns data file
           :param filename: the *_X.json output of WlmStats
        '''
        #Open infile, check validity and store data as indata
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
            indataType = jIn['type']
            if not indataType in self.supportedTypes:
                raise MyException(u'Wrong indataType. Found: %s' %jIn['type'])
            indata = jIn['data'] 
            #load date- yes these will be overwritten
            self.settingDate = jIn['settings']['date']   #should be gotten from source file
        except MyException, e:
            if verbose:
                print u'Error reading input file: %s\n' %e
            self.log.write(u'Error reading input file: %s\n' %e)
            exit(1)
        #confirm succesful load to log together with timestamp
        self.log.write(u'%s: Successfully loaded %s-file.\n' %(datetime.datetime.utcnow(), indataType))
        return indata, jIn['settings']['identifier']

    def __init__(self, imagesFile, monumentsFile, verbose=False, test=False):
        self.versionInfo()
        self.imagesFile = imagesFile
        self.monumentsFile = monumentsFile
        varErrors = self.loadVariables(test)
        if varErrors:
            self.log.write(u'%s\n' %varErrors)
            exit(1)
        self.log = codecs.open(self.logFilename, 'a', 'utf-8')
        self.log.write(u'-----------------------\n')
        
        self.images, identifier = self.load(self.imagesFile)
        self.monuments, identifier = self.load(self.monumentsFile)
        self.output += identifier
        
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
    
    def run(self, verbose=False, testing=False):
        #make a list of all wlm filenames
        wlm_images = []
        for k, v in self.images.iteritems():
            wlm_images.append(v['title'])
        
        counter = {}
        used_wlm = {}
        #compare to files used in lists/database
        for k, v in self.monuments.iteritems():
            if v['image']:
                #key is a string encoded tuple so need to break part out
                key = k.split("u'")[1].split("'")[0]
                if key in counter.keys():
                    counter[key].append(v['image'])
                else:
                    counter[key] = [v['image'],]
                if v['image'] in wlm_images:
                    if key in used_wlm.keys():
                        used_wlm[key].append(v['image'])
                    else:
                        used_wlm[key] = [v['image'],]
        #first crunch
        uniques = len(set([item for sublist in used_wlm.values() for item in sublist]))
        #https://stackoverflow.com/questions/952914/making-a-flat-list-out-of-list-of-lists-in-python
        #output
        f = codecs.open(u'%s_usage.csv' %self.output, 'w', 'utf-8')
        f.write('#Note that the same image can be cusd by multiple objects and types\n')
        f.write('#no. of uniques irrelevant of type: %d\n' %uniques)
        f.write('#type|no. images used|no. uniques used|total used images\n')
        for k, v in used_wlm.iteritems():
            f.write('%s|%d|%d|%d\n' %(k, len(v), len(set(v)), len(counter[k])))
        f.close()
        
        
class MyException(Exception):
    pass

if __name__ == '__main__':
    import sys
    usage = '''Usage: python UsageCruncher.py imagefile monumentsfile
\timagefile: the json indata file (the *_images.json output of WlmStats)
\tmonumentsfile: the json indata file (the *_monuments.json output of WlmStats)
example: python UsageCruncher.py ./output/wlm-se-2012_images.json ./output/wlm-se-2012_monuments.json
'''
    argv = sys.argv[1:]
    if len(argv) == 2:
        UsageCruncher(argv[0], argv[1])
    else:
        print usage
#EoF    l   
