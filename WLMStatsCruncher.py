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
# @TODO
#   Add title to any output which includes monument_id?
#   Add support for muni analysis
#   Add support for monument analysis
#

import codecs, ujson
import datetime #for timestamps  in log
import operator #only used by sortedDict
import common as common

class WLMStatsCruncher(object):
    def versionInfo(self):
        '''Version specific variables'''
        self.scriptversion = u'0.21'
        self.scriptname = u'WLM_Statistics_Cruncher'
        self.WLMStatsVersion = u'0.21' # the version of WLMStats for which the cruncher was designed

    def loadVariables(self, test):
        '''semi-stable variables which are not project specific'''
        self.logFilename = u'¤WLMStatsCruncher.log'
        self.output = "analysis/"
        self.commons_siteurl = 'https://commons.wikimedia.org'
        self.reqKeys = [u'type', u'data', u'WLMStatsVersion', u'settings']
        self.supportedTypes = ['images', 'munis']
        
        #load dataDict file
        try:
            f = codecs.open('dataDicts.json','r','utf8')
            self.dataDicts = ujson.load(f)
            f.close()
        except IOError, e:
            return u'Error opening dataDicts file: %s' %e
            exit(1)
        
    def __init__(self, filename, verbose=False, test=False):
        '''Sets up environment, loads data file, triggers run/test
           :param filename: the *_images.json output of WlmStats
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
            #load date
            self.settingDate = jIn['settings']['date']   #should be gotten from source file
            self.output += jIn['settings']['identifier'] #from source settings file @NOTE does not take test. into account
        except MyException, e:
            if verbose:
                print u'Error reading input file: %s\n' %e
            self.log.write(u'Error reading input file: %s\n' %e)
            exit(1)
        #confirm succesful load to log together with timestamp
        self.log.write(u'-----------------------\n%s: Successfully started %srun.\n' %(datetime.datetime.utcnow(), 'test ' if test else ''))
        
        #ready to run
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
        '''will essentially only be a list of called functions dealing 
        with each bit and then outputting it.
        Checks self.indataType to decide which list to follow'''
        
        if self.indataType == 'images':
            self.analyseUsers(detailed=True) #images per user
            self.analyseGeo()   #images per county/muni and type
            self.analyseType()  #images per type
            self.analyseObjects(top=3) #most popular images per type
            self.analyseLicense() #which licenses were used
            self.analyseDates()   #when were the images created
            self.analyseListStatus() #are the imags in lists?
        elif self.indataType == 'munis':
            self.analyseMuniStatistics()
        
        #Done
    
    def analyseSimple(self, key, lable=None, output=True):
        '''analyses how many images (total and unique) there are for each object of a given type/key
        the type must be a simple string
        return: a tuple (results, blanks) where
            results is a dict with {key:{monument_id:images-with-that-id-and-key}}
            blanks is the total number of images without a valid key (e.g. monument_id, user)
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
        f = codecs.open(u'%s_%s.csv' %(self.output, lable), 'w', 'utf-8')
        f.write('#Note that the same image can be counted in multiple types/ids\n')
        f.write('#no. %s: %d\n' %(lable, len(results)))
        f.write('#no. blanks: %d\n' %blanks)
        f.write('#%s|no. images|no. uniques\n' %(lable))
        for k, v in results.iteritems():
            f.write('%s|%d|%d\n' %(k, sum(v.values()), len(v)))
        f.close()
    
    def analyseUsers(self, output=True, detailed=False):
        if not detailed:
            return self.analyseSimple('uploader','users',output=output)
            
        #else
        results, blanks = self.analyseSimple('uploader','users',output=output)
        userinfo = self.getUserInfo(results.keys())
        
        #output
        if output:
            f = codecs.open(u'%s_users.csv' %self.output, 'w', 'utf-8')
            f.write('#no. users: %d\n' %len(results))
            f.write('#no. blanks: %d\n' %blanks)
            f.write('#user|no. images|no. uniques|registration|edits|gender|emailable\n')
            for k, v in results.iteritems():
                if not k in userinfo.keys():
                    k = k.replace('_',' ') #Since these are automatically converted for API, but should remain in other cases
                f.write('%s|%d|%d|%s|%s|%s|%s\n' %(k, sum(v.values()), len(v), userinfo[k]['reg'], userinfo[k]['edits'], userinfo[k]['gender'], userinfo[k]['emailable']))
            f.close()
        
        return results, blanks, userinfo

    def analyseLicense(self, output=True):
        return self.analyseSimple('copyright','licenses',output=output)
        
    def analyseListStatus(self, output=True):
        results = {}
        blanks = 0
        for k,v in self.indata.iteritems():
            listStatus, monument_type, monument_ids = v['in_list'], v['monument_type'], v['monument_id']
            #skip any entries without valid monument_id or value
            if any(k in([],'') for k in (listStatus, monument_type, monument_ids)):
                blanks +=1
                continue
            for m in monument_type:
                if not m in results.keys():
                    results[m]={}
                if not listStatus in results[m].keys():
                    results[m][listStatus]={}
                for m_id in monument_ids:
                    monument_id = ';'.join(m_id)
                    if not monument_id in results[m].keys():
                        results[m][listStatus][monument_id] = 1
                    else:
                        results[m][listStatus][monument_id] += 1
        if output:
            #output
            f = codecs.open(u'%s_listStatus.csv' %self.output, 'w', 'utf-8')
            f.write('#Note that the same image can be counted in multiple types/ids\n')
            f.write('#no. blanks: %d\n' %blanks)
            f.write('#type|listStatus|no. images|no. uniques\n')
            for typ in results.keys():
                for k, v in results[typ].iteritems():
                    f.write('%s|%s|%d|%d\n' %(typ, k, sum(v.values()), len(v)))
            f.close()
        
        return results, blanks
    
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
                    if not m_id[0] == m:  # skip id's related to different typw
                        continue
                    monument_id = ';'.join(m_id)
                    if not monument_id in results[m].keys():
                        results[m][monument_id] = 1
                    else:
                        results[m][monument_id] += 1
        if output:
            self.outputSimple('types', results, blanks)
        
        return results, blanks
    
    def analyseObjects(self, top=3, output=True):
        results  = self.analyseType()[0]
        '''takes output from analyseType and creates top lists for each type'''
        if not output:
            return None
        f = codecs.open(u'%s_toplists.csv' %self.output, 'w', 'utf-8')
        f.write('#Note that ties are not resolved\n')
        f.write('#type|idno|images\n')
        for t, v in results.iteritems():
            sortedV = sortedDict(v)
            for i in range(0,top):
                f.write(u'%s|%s|%d\n' %(t, sortedV[i][0].split(';')[1], sortedV[i][1]))
        f.close()
    
    def analyseDates(self, output=True):
        wlm_date = (int(self.settingDate[:4]), int(self.settingDate[5:]))
        #Spcial bins
        current = u'current (%s)' %self.settingDate
        since_last = u'since_last (%d-%s – %s)' %(wlm_date[0]-1, str(wlm_date[1]).zfill(2), current)
        rest_of_last_year = u'rest_of_last_year (%d – %d-%s)' %(wlm_date[0]-1, wlm_date[0]-1,str(wlm_date[1]).zfill(2))
        results = {current:0, since_last:0, rest_of_last_year:0}
        blanks = 0
        for k,v in self.indata.iteritems():
            date_raw = v['created']
            #skip any entries without valid monument_id or value
            if date_raw == '' or len(date_raw)<4:
                blanks +=1
                continue
            #prepare dates
            month = 0
            if not common.is_number(date_raw[:4]):
                date = ('text','text')
            else:
                if len(date_raw) >= 7:
                        month = int(date_raw[5:7])
                date = (int(date_raw[:4]),month)
            
            #binning
            if date == wlm_date:
                #the current competition
                results[current] += 1
            elif (date[0] == wlm_date[0] and date[1] < wlm_date[1]) or (date[0] == wlm_date[0]-1 and date[1] > wlm_date[1]):
                #since last competition
                results[since_last] += 1
            elif date[0] == wlm_date[0]-1:
                #the rest of that year
                results[rest_of_last_year] += 1
            else:
                if not str(date[0]) in results.keys():
                    results[str(date[0])] = 1
                else:
                    results[str(date[0])] += 1
        if output:
            #to simple to be outputSimple()
            f = codecs.open(u'%s_dates.csv' %self.output, 'w', 'utf-8')
            f.write('#no. dates: %d\n' %len(results))
            f.write('#no. blanks: %d\n' %blanks)
            f.write('#dates|no. images\n')
            for k, v in results.iteritems():
                f.write('%s|%d\n' %(k, v))
            f.close()
        
    def analyseGeo(self, output=True):
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
        #leave now if no output is needed
        if not output:
            return results, blanks
        #output
        fMuni = codecs.open(u'%s_geo-muni.csv' %self.output, 'w', 'utf-8')
        fCounty = codecs.open(u'%s_geo-county.csv' %self.output, 'w', 'utf-8')
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
                fMuni.write('%s|%s|%d|%d%s\n' % (muni, self.dataDicts['muni_code2Name'][muni.lstrip('0')], sum(m_images.values()), sum(m_uniques.values()), by_type_row))
            #munis done
            by_type_row = ''
            for t in monument_types:
                by_type_row += '|%d|%d' %(c_images[t], c_uniques[t])
            fCounty.write('%s|%s|%d|%d%s\n' % (county, self.dataDicts['county_code2Name'][county[len('se-'):].upper()], sum(c_images.values()), sum(c_uniques.values()), by_type_row))
        #counties done
        fMuni.close()
        fCounty.close()
        
        return results, blanks
        
    def getUserInfo(self, users, verbose=False):
        '''
        get aditional info about the uploaders
        this requires the wikiapi
        '''
        #TODO: Move to wikiApi
        import WikiApi as wikiApi
        maxUsers = 50
        #Look for config file and connect to api
        scriptidentify = u'%s/%s' %(self.scriptname,self.scriptversion)
        try:
            import config
            cApi = wikiApi.WikiApi.setUpApi(user=config.user, password=config.password, site=self.commons_siteurl, scriptidentify=scriptidentify, verbose=verbose) 
        except ImportError:
            from getpass import getpass #not needed if config file exists
            user=getpass(u'Username:')
            cApi = wikiApi.WikiApi.setUpApi(user=user, password=getpass(), site=self.commons_siteurl, scriptidentify=scriptidentify, verbose=verbose)
        
        #query
        d={}
        
        #query allows a maximum of maxUsers per go
        while len(users) > 0:
            batch = users[:maxUsers]
            users = users[maxUsers:]
            
            jsonr = cApi.httpGET("query", [('list', 'users'),
                                           ('usprop', 'editcount|registration|gender|emailable'),
                                           ('ususers', '|'.join(batch).encode('utf-8'))
                                          ])
            #should test for valid response here
            for user in jsonr['query']['users']:
                if 'missing' in user.keys() or 'invalid' in user.keys():
                    d[user['name']] = {'reg':'-', 'edits':'-', 'gender':'-', 'emailable':'-'}
                    continue
                d[user['name']] = {'reg':user['registration'],'edits':user['editcount'],'gender':user['gender'],'emailable':False}
                if user['registration']: #this can be null
                    #if a date exists then crop to year-month
                    d[user['name']]['reg'] = user['registration'][:7]
                if 'emailable' in user.keys():
                    d[user['name']]['emailable'] = True
        #done
        return d

    def analyseMuniStatistics(self, output=True):
        '''analyses hApi.getMuniStatistics results and returns output formated for outputCSV()'''
        #self.indata has the form MuniName': {table1: {'illustrated': int, 'total': int, 'coords': int}, u'table2': ...
        allowed_props = [u'illustrated', u'coords'] #allowed properties, in addition to total
        muniStats = {}
        allowed_types = []
        for k, v in self.indata.iteritems():
            muniStats[k] = {
                'muni_code': self.dataDicts['muni_name2code'][k].zfill(4) if k in self.dataDicts['muni_name2code'].keys() else None,
                'muni_name': k
                }
            aggregate = {'total':0}
            for prop in allowed_props:
                aggregate[prop] = 0
            muniStats[k]['types'] = {}
            for t, vv in v.iteritems():
                if not t in allowed_types:
                    allowed_types.append(t)
                total = vv['total']
                muniStats[k]['types'][t] = {'total': '%d' %total}
                aggregate['total'] += total
                for prop in allowed_props:
                    val = vv[prop]
                    aggregate[prop] += val
                    muniStats[k]['types'][t][prop] = '%d' %val
                    if total == 0:
                        muniStats[k]['types'][t][u'%s-percentage' %prop] = '%.3f' %float('NaN')
                    else:
                        muniStats[k]['types'][t][u'%s-percentage' %prop] = '%.3f' %(val/float(total))
            total = aggregate['total']
            muniStats[k]['sum'] = {'total': '%d' %total}
            for prop in allowed_props:
                val = aggregate[prop]
                muniStats[k]['sum'][prop] = '%d' %val
                if total == 0:
                    muniStats[k]['sum'][u'%s-percentage' %prop] = '%.3f' %float('NaN')
                else:
                    muniStats[k]['sum'][u'%s-percentage' %prop] = '%.3f' %(val/float(total))
        
        if output:
            #output
            f = codecs.open(u'%s_coverage.csv' %self.output, 'w', 'utf-8')
            header_row = [u'sum_total', ]
            for prop in allowed_props:
                header_row.append(u'sum_%s' %prop)
                header_row.append(u'sum_%s-percentage' %prop)
            for t in allowed_types:
                header_row.append(u'%s_total' %t)
                for prop in allowed_props:
                    header_row.append(u'%s_%s' %(t, prop))
                    header_row.append(u'%s_%s-percentage' %(t, prop))
            f.write(u'#municipality code|municipality name|county|%s\n' %'|'.join(header_row))
            #need to generate list type/prop list here and then keep same order
            #possibly using from Collections import SortedDict as SortedDict
            for k, v in muniStats.iteritems():
                muni_row = [muniStats[k]['sum']['total'],]
                for prop in allowed_props:
                    muni_row.append(muniStats[k]['sum'][prop])
                    muni_row.append(muniStats[k]['sum'][u'%s-percentage' %prop])
                for t in allowed_types:
                    if t in muniStats[k]['types'].keys(): #If type is not present then fill with zeroes
                        muni_row.append(muniStats[k]['types'][t]['total'])
                        for prop in allowed_props:
                            muni_row.append(muniStats[k]['types'][t][prop])
                            muni_row.append(muniStats[k]['types'][t][u'%s-percentage' %prop])
                    else:
                        muni_row.append('0')
                        for prop in allowed_props:
                            muni_row.append('0') #prop
                            muni_row.append('0') #prop-percentage
                f.write('%s|%s|%s|%s\n' %(v['muni_code'], k, self.dataDicts['muni_code2county_code'][v['muni_code'].lstrip('0')], '|'.join(muni_row)))
            f.close()

def sortedDict(ddict):
    '''turns a dict into a sorted list of tuples'''
    sorted_ddict = sorted(ddict.iteritems(), key=operator.itemgetter(1), reverse=True)
    return sorted_ddict
        
class MyException(Exception):
    pass

if __name__ == '__main__':
    import sys
    usage = '''Usage: python WLMStatsCruncher.py infile option
\tfile: the json indata file (the *_images.json output of WlmStats)
\toption (optional): can be set to:
\t\tverbose:\t toggles on verbose mode with additional output to the terminal
\t\ttest:\t\t toggles on testing (a verbose and limited run)
example: python WLMStatsCruncher.py ./output/wlm-se.test_images.json verbose
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
