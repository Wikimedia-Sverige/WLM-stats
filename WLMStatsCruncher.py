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
#in images [u'monument_id', u'muni', u'copyright', u'title', u'problematic', u'created', u'in_list', u'county', u'uploader', u'photographer', u'monument_type']

import codecs, ujson
import datetime #for timestamps  in log
import dataDicts #redo as json?
import operator #only used by sortedDict

class WLMStatsCruncher(object):
    def versionInfo(self):
        '''Version specific variables'''
        self.scriptversion = u'0.1'
        self.scriptname = u'WLM_Statistics_Cruncher'
        self.WLMStatsVersion = u'0.1' # the version of WLMStats for which the cruncher was designed

    def loadVariables(self, test):
        '''semi-stable variables which are not project specific'''
        self.logFilename = u'¤WLMStatsCruncher.log'
        self.output = "analysis/"
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
        
        self.analyseUsers() #images per user
        self.analyseGeo()   #images per county/muni and type
        self.analyseObjects(   #most popular images per type
            self.analyseType()[0] #images per type
        )
        
        #Done
    
    def analyseSimple(self, key, lable=None, output=True):
        '''analyses how many images (total and unique) there are for each object of a given type/key
        the type must be a simple string
        return: a tuple (results, blanks) where
            results is a dict with {key:{monument_id:images-with-that-id-and-key}}
            blanks is the total number of images without a valid monuent_id
        raises: MyException if key not found
        
        to use:
            users, blanks = self.analyseSimple('uploader')
            no._objects_of_that_type = len(users)
            no._images_per_user      = len(users[user])
            no._uniques_per_user     = sum(users[user].values())
        '''
        if not lable:
            lable = key
        if not key in self.indata.values()[0].keys():
            raise MyException('analyseSimple() called with invalid key %s' %key)
        results = {}
        blanks = 0
        for k,v in self.indata.iteritems():
            value, monument_ids = v[key], v['monument_id']
            #skip any entries without valid monument_id or value
            if any(k in ([],'') for k in (value, monument_ids)):
                blanks +=1
                continue
            if not value in results.keys():
                results[value]={}
            for m_id in monument_ids:
                monument_id = ';'.join(m_id)
                if not monument_id in results[value].keys():
                    results[value][monument_id] = 1
                else:
                    results[value][monument_id] += 1
        if output:
            self.outputSimple(lable, results, blanks)
        
        return results, blanks
    
    def outputSimple(self,lable,results,blanks):
        '''simple csv output for data from analyseSimple'''
        #output
        f = codecs.open(u'%s%s.csv' %(self.output, lable), 'w', 'utf-8')
        f.write('#Note that the same image can be counted in multiple types/ids\n')
        f.write('#no. %s: %d\n' %(lable, len(results)))
        f.write('#no. blanks: %d\n' %blanks)
        f.write('#%s|no. images|no. uniques\n' %(lable))
        for k, v in results.iteritems():
            f.write('%s|%d|%d\n' %(k, sum(v.values()), len(v)))
        f.close()
        
    def analyseUsers(self, output=True):
        return self.analyseSimple('uploader','users',output=output)
    
    def analyseType(self, output=True):
        '''Stats per type, both images and unique objects'''
        results = {}
        blanks = 0
        for k,v in self.indata.iteritems():
            monument_type, monument_ids = v['monument_type'], v['monument_id']
            #skip any entries without valid monument_id or value
            if any(k in([],'') for k in (monument_type, monument_ids)):
                blanks +=1
                continue
            for m in monument_type:
                if not m in results.keys():
                    results[m]={}
                for m_id in monument_ids:
                    monument_id = ';'.join(m_id)
                    if not monument_id in results[m].keys():
                        results[m][monument_id] = 1
                    else:
                        results[m][monument_id] += 1
        if output:
            self.outputSimple('types', results, blanks)
        
        return results, blanks
    
    def analyseObjects(self, results, top=3):
        '''takes output from analyseType and creates top lists for each type'''
        f = codecs.open(u'%stoplists.csv' %self.output, 'w', 'utf-8')
        f.write('#Note that ties are not resolved\n')
        f.write('#type|idno|images\n')
        for t, v in results.iteritems():
            sortedV = sortedDict(v)
            for i in range(0,top):
                f.write(u'%s: %s %d\n' %(t, sortedV[i][0].split(';')[1], sortedV[i][1]))
        f.close()
        
        
    def analyseGeo(self):
        '''Stats per county/muni, both totals and by type, both images and unique objects'''
        results = {}
        blanks = 0
        monument_types = []
        for k,v in self.indata.iteritems():
            try:
                muni, county, monument_type, monument_ids = v['muni'], v['county'], v['monument_type'], v['monument_id']
            except KeyError:
                #some images don't have county/muni
                #TODO: better that WLMStats outputs empty values
                blanks +=1
                continue
            #skip any entries without valid monument_id or value
            if any(k in([],'') for k in (muni, county, monument_type, monument_ids)):
                blanks +=1
                continue
            if not county in results.keys():
                results[county]={}
            if not muni in results[county].keys():
                results[county][muni]={}
            for m in monument_type:
                if not m in monument_types:
                    monument_types.append(m)
                if not m in results[county][muni].keys():
                    results[county][muni][m]={}
                for m_id in monument_ids:
                    monument_id = ';'.join(m_id)
                    if not monument_id in results[county][muni][m].keys():
                        results[county][muni][m][monument_id] = 1
                    else:
                        results[county][muni][m][monument_id] += 1
        
        #output
        fMuni = codecs.open(u'%sgeo-muni.csv' %self.output, 'w', 'utf-8')
        fCounty = codecs.open(u'%sgeo-county.csv' %self.output, 'w', 'utf-8')
        header = u'#Note that the same image can be counted in multiple types/ids\n#no. blanks: %d' %blanks
        #for each county/muni we want overall/by_type totals and uniques
        by_type_row=''
        for t in monument_types:
            by_type_row += '|%s_images|%s_uniques' %(t,t)
        #lables
        fMuni.write('%s\n#muni_code|muni_name|total_images|total_uniques%s\n' % (header, by_type_row))
        fCounty.write('%s\n#county_code|county_name|total_images|total_uniques%s\n' % (header, by_type_row))
        
        for county in results.keys():
            c_images = dict.fromkeys(monument_types,0)
            c_uniques = dict.fromkeys(monument_types,0)
            for muni in results[county].keys():
                m_images = dict.fromkeys(monument_types,0)
                m_uniques = dict.fromkeys(monument_types,0)
                for t in monument_types:
                    if not t in results[county][muni].keys():
                        continue
                    m_uniques[t] += len(results[county][muni][t])
                    m_images[t] += sum(results[county][muni][t].values())
                #types done
                by_type_row = ''
                for t in monument_types:
                    by_type_row += '|%d|%d' %(m_images[t], m_uniques[t])
                    c_images[t] += m_images[t]
                    c_uniques[t] += m_uniques[t]
                fMuni.write('%s|%s|%d|%d%s\n' % (muni, dataDicts.muni_code2Name[muni.lstrip('0')], sum(m_images.values()), sum(m_uniques.values()), by_type_row))
            #munis done
            by_type_row = ''
            for t in monument_types:
                by_type_row += '|%d|%d' %(c_images[t], c_uniques[t])
            fCounty.write('%s|%s|%d|%d%s\n' % (county, dataDicts.county_code2Name[county[len('se-'):].upper()], sum(c_images.values()), sum(c_uniques.values()), by_type_row))
        #counties done
        fMuni.close()
        fCounty.close()
        
        return results, blanks

def sortedDict(ddict):
    '''turns a dict into a sorted list of tuples'''
    sorted_ddict = sorted(ddict.iteritems(), key=operator.itemgetter(1), reverse=True)
    return sorted_ddict
        
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
