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
# @TODO - maybe
#   Retrieve info for objects not in lists
#       Would require lookup against K-samsök etc.
#   Retrieve information about type (kyrka, byggnad, fornminnestyp)
#       Would require going trhough lists, and K-samsök

import codecs, ujson
import datetime #for timestamps  in log
import WikiApi as wikiApi
import HeritageApi as heritageApi
import re #only used for wikitext parsing

class WLMStats(object):
    def versionInfo(self):
        '''Version specific variables'''
        self.scriptversion = u'0.21'
        self.scriptname = u'WLM_Statistics'
        self.infoTemplate = [u'Template:Information',] #supported info templates - based on what is suppported by parseImageInfo
        self.commonsMetadataExtension = 1.2 # the version of the extention for which the script was designed
    
    def loadVariables(self, infile, test):
        '''semi-stable variables which are not project specific'''
        self.logFilename = u'¤WLMStats.log'
        self.heritage_siteurl = 'https://tools.wmflabs.org/heritage/api'
        self.commons_siteurl = 'https://commons.wikimedia.org'
        self.gcmlimit = 250 #Images to process per API request in ImageInfo
        self.output = "output/"
        self.settings_file = infile
        self._test_gcmlimit = 5
        self._test_limit = 15
        
        #distingusih testdata
        if test:
            self.output += u'test.'
            self.settings_file = u'settings.test.json'
        
        #load settings file
        requiredKeys = ['types', 'cats', 'date', 'identifier'] #keys which are explicitly called later
        try:
            f = codecs.open(self.settings_file, 'r', 'utf-8')
            self.settings = ujson.load(f)
            f.close()
            if not set(requiredKeys).issubset(set(self.settings.keys())) :
                raise KeyError("missing one of the required keys!: %s" %', '.join(requiredKeys))
        except IOError, e:
            return u'Error opening settings file: %s' %e
            exit(1)
        except (ValueError, KeyError), e:
            return u'Error processing settings file as the expected json. Are you sure it is still valid?: %s' %e
            exit(1)
        
        #lable output with identifier
        self.output += self.settings['identifier']
        
        #load dataDict file
        try:
            f = codecs.open('dataDicts.json','r','utf8')
            self.dataDicts = ujson.load(f)
            f.close()
        except IOError, e:
            return u'Error opening dataDicts file: %s' %e
            exit(1)

    def __init__(self, infile, verbose=False, test=False):
        '''Sets up environment, loads project file, triggers run/test
           Requires no parameters:
        '''
        self.versionInfo()
        varErrors = self.loadVariables(infile, test)
        self.log = codecs.open(self.logFilename, 'a', 'utf-8')
        if varErrors:
            self.log.write(u'%s\n' %varErrors)
            exit(1)
        self.images = {} #container for all the imageinfo, using pageid as its key
        
        #confirm succesful load to log together with timestamp
        self.log.write(u'-----------------------\n%s: Successfully started %srun.\n' %(datetime.datetime.utcnow(), 'test ' if test else ''))
        
        #Look for config file and connect to apis
        scriptidentify = u'%s/%s' %(self.scriptname,self.scriptversion)
        try:
            import config
            self.hApi = heritageApi.HeritageApi.setUpApi(user=config.user, site=self.heritage_siteurl, scriptidentify=scriptidentify, verbose=verbose)
            self.cApi = wikiApi.WikiApi.setUpApi(user=config.user, password=config.password, site=self.commons_siteurl, scriptidentify=scriptidentify, verbose=verbose) 
        except ImportError:
            from getpass import getpass #not needed if config file exists
            user=getpass(u'Username:')
            self.hApi = heritageApi.HeritageApi.setUpApi(user=user, site=self.heritage_siteurl, scriptidentify=scriptidentify, verbose=verbose)
            self.cApi = wikiApi.WikiApi.setUpApi(user=user, password=getpass(), site=self.commons_siteurl, scriptidentify=scriptidentify, verbose=verbose)
        
        #Create output files (so that any errors occur before the actual run)
        #TODO cleaner variablenames one only json is outputted
        try:
            self.fMonumentsDump = codecs.open(u'%s_monuments.json' %self.output, 'w', 'utf-8')
            self.fMuniDump = codecs.open(u'%s_muni.json' %self.output, 'w', 'utf-8')
            self.fImagesDump = codecs.open(u'%s_images.json' %self.output, 'w', 'utf-8')
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
        #TODO return errors
        muniStatsRaw = {}
        for k, v in self.settings['types'].iteritems():
            if v['per_muni']:
                self.hApi.getMuniStatistics(table=v['table'], muniStats=muniStatsRaw, debug=False)
        #analyse and output
        self.fMuniDump.write(ujson.dumps({
            'WLMStatsVersion':self.scriptversion,
            'type':'munis',
            'data':muniStatsRaw,
            'settings':self.settings
            }))
        
        #get all heritage_objects from heritage api and repackage to have table+id as key in dict
        #TODO return errors
        monuments = self.getAllMonuments(verbose=verbose, testing=testing)
        #output to .json file + make it possible to run from this point
        self.fMonumentsDump.write(ujson.dumps({
            'WLMStatsVersion':self.scriptversion,
            'type':'monuments',
            'data':monuments,
            'settings':self.settings
            }))
        #self.fMonumentsDump.write(ujson.dumps(monuments))
        self.fMonumentsDump.close()
        
        #get all images for the relevant categories, parse the image info
        ##set monument_type(s) using any tracker categories (empty if none found)
        try:
            self.getAllImages(verbose=verbose, testing=testing)
        except MyException, e:
            return e
        #output to .state file + make it possible to run from this point
        #self.fState.write(ujson.dumps(self.images))
        
        #getContent for each image to identify idno
        self.getAllIds(verbose=verbose, testing=testing)
        #output to .state file + make it possible to run from this point
        #self.fState.write(ujson.dumps(self.images))
        
        #check all images to see if in monuments
        #use this to set in_list:True/False
        for k in self.images:
            idnos = self.images[k]['monument_id']
            for idno in idnos:
                if idno in monuments.keys():
                    self.images[k]['in_list'] = True
                    self.images[k]['muni'] = self.dataDicts['muni_name2code'][monuments[idno]['muni']].zfill(4) if monuments[idno]['muni'] in self.dataDicts['muni_name2code'].keys() else monuments[idno]['muni']
                    self.images[k]['county'] = monuments[idno]['county']
                    break #no need to check later ids
        
        #output to .json file + make it possible to run from this point
        self.fImagesDump.write(ujson.dumps({
            'WLMStatsVersion':self.scriptversion,
            'type':'images',
            'data':self.images,
            'settings':self.settings
            }))
        #self.fImagesDump.write(ujson.dumps(self.images))
        self.fImagesDump.close()
        
        #consider looking in external database for items with not_in_list:true
        #output to .state file + make it possible to run from this point
        
        return None

    def getAllMonuments(self, testing=False, verbose=False):
        '''get all heritage_objects from heritage api and return as a dict
        with (country, id) as key
        :return: dict with (country, id):{muni, illustrated, lon, lat, county, source}
        '''
        table_to_type = {}
        monumentDump = []
        for k, v in self.settings['types'].iteritems():
            table_to_type[v['table']] = k
            monumentDump += self.hApi.getAllEntries(table=v['table'], verbose=verbose)
        
        #clean up
        monuments = {}
        for m in monumentDump:
            #m = {u'name': u'[[Vaholms bro]] (Sk\xf6vde Vaholm 3:1)', u'municipality': u'Sk\xf6vde', u'country': u'se-bbr', u'image': u'Tidan vid vaholms brohus.JPG', u'lon': 14.00023, u'adm1': u'se-o', u'source': u'https://sv.wikipedia.org/w/index.php?title=Lista_\xf6ver_byggnadsminnen_i_V\xe4stra_G\xf6talands_l\xe4n&redirect=no&useskin=monobook&oldid=25114690', u'lat': 58.58737, u'id': u'21000001001755'}
            iid = (table_to_type[m['country']], m['id'])
            monuments[iid] = {
                'muni':        m['municipality'],
                'illustrated': m['image'] != '',
                'image':       m['image'],
                'lon':         m['lon'],
                'lat':         m['lat'],
                'county':      m['adm1'],
                'source':      m['source'][m['source'].find(u'='):m['source'].find(u'&')]
            }
        return monuments

    def getAllImages(self, testing=False, verbose=False):
        '''get all images from commons api. Parse the information and return as a dict
        with (pageid) as key
        :
        '''
        imageInfo={}
        for basecat in self.settings['cats']:
            if verbose:
                print u'Retrieving ImageInfo for %s...' %basecat
            getImageInfosError = self.getImageInfos(basecat, imageInfo=imageInfo, verbose=verbose, testing=testing)
            if getImageInfosError:
                self.log.write(u'Terminating: Error retrieving imageInfos: %s\n' %getImageInfosError)
                #at this point we most likely do not want to continue
                if verbose: 
                    print u'Terminated prematurely, please check log file'
                raise MyException(u'Terminating: Error retrieving imageInfos: %s\n' %getImageInfosError)
        
        #use tracker categories to set types
        typeCategories = {}
        for k, v in self.settings['types'].iteritems():
            if 'commons_cat' in v.keys():
                typeCategories[v['commons_cat']] = k
        
        #parse all ImageInfos
        if verbose:
            print u'Parsing ImageInfo...'
        counter = 0
        for k,v in imageInfo.iteritems():
            counter +=1
            if verbose and (counter%250)==0:
                print u'parsed %d out of %d' %(counter, len(imageInfo))
            errorType, errorMessage = self.parseImageInfo(v, typeCategories)
            if errorType != None:
                if errorType: #critical
                    self.log.write(u'Terminating: error parsing imageInfos: %s\n' %errorMessage)
                    if verbose:
                        print u'Terminated prematurely, please check log file'
                    raise MyException(u'Terminating: error parsing imageInfos: %s\n' %errorMessage)
                else: #minor
                    self.log.write(u'Skipping: error parsing imageInfos: %s\n' %errorMessage)
        
    def getAllIds(self, testing=False, verbose=False):
        '''add idno to all images with monument_type(s)'''
        #for each image getContent()
        ##if one of the  monument_type(s) has url_promised=false then also need to retrieve prop:wikitext otherwise just prop:templates|externallinks
        ### if url_promised
        #### for each monument_type identify all matching id's from externallinks
        ### if !url_promised
        #### check that right template is present. If so then isolate template and id in wikitext (most likely needs a specific parser)
        #use monument_type+id and extmetadata to isolate relevant data
        ## if monument_type+id not in heritage_objects then add not_in_list:true
        if verbose:
            print u'Retrieving content...'
        counter = 0
        unsupported = []
        for k in self.images.keys():
            counter +=1
            if verbose and (counter%100)==0:
                print u'Retrieved %d out of %d' %(counter, len(self.images))
                
            #check if object has monument_type(s)
            if not self.images[k]['monument_type']:
                unsupported.append(k)
                continue
            url_promised = True
            for t in self.images[k]['monument_type']:
                if not self.settings['types'][t]['url_promised']:
                    url_promised = False
            
            #get content for that pageID (can only retrieve one at a time)
            content, getContentError = self.getContent(k, getwikitext=not(url_promised))
            if not getContentError:
                getContentError = self.parseContent(k, content)
                if not getContentError:
                    continue
            #only reached if encountered error
            self.log.write(u'Error retrieving/parsing content for PageId %d (%s), removing from dataset: %s\n' %(k, self.images[k]['title'], getContentError))
            unsupported.append(k)
            
        #remove problematic entries
        for k in unsupported:
            #del self.images[k]
            self.images[k]['problematic']=True

#Start of Europeana.py fork - some methods may be overly complicated for this purpose
    def getImageInfos(self, maincat, imageInfo={}, verbose=False, testing=False):
        '''given a single category this queries the MediaWiki api for the parsed content of that page
           returns None on success otherwise an error message.'''
        #TODO needs more error handling (based on api replies)
        #TODO. Can get id and type from category+sortkey (for the commons_cat). WOuld this remove the need for page parsing?
        ## i.e. scan all commons_cat and store pageid {type:id}. It only allows one id per type and image though
        ## /w/api.php?action=query&list=categorymembers&format=json&cmtitle=Category%3AProtected%20buildings%20in%20Sweden%20with%20known%20IDs&cmprop=ids%7Ctitle%7Csortkeyprefix&cmlimit=10
        #Allows overriding gcmlimit for testing
        gcmlimit = self.gcmlimit
        if testing:
            gcmlimit = self._test_gcmlimit
        
        #test that category exists and check number of entries
        #/w/api.php?action=query&prop=categoryinfo&format=json&titles=Category%3AImages%20from%20Wiki%20Loves%20Monuments%202013%20in%20Sweden
        jsonr = self.cApi.httpGET("query", [('prop', 'categoryinfo'),
                                        ('titles', maincat.encode('utf-8'))
                                       ])
        jsonr = jsonr['query']['pages'].iteritems().next()[1]
        #check for error
        if 'missing' in jsonr.keys():
            return u'The category "%s" does not exist' %maincat
        total = jsonr['categoryinfo']['files']
        if verbose:
            print u'The category "%s" contains %d files and %d subcategories (the latter will not be checked)' %(maincat, total, jsonr['categoryinfo']['subcats'])
        
        #then start retrieving info
        #/w/api.php?action=query&prop=imageinfo&format=json&iiprop=user%7Cextmetadata&iilimit=1&generator=categorymembers&gcmtitle=Category%3AImages%20from%20Wiki%20Loves%20Monuments%202013%20in%20Sweden&gcmprop=title&gcmnamespace=6&gcmlimit=50
        jsonr = self.cApi.httpGET("query", [('prop', 'imageinfo'),
                                        ('iiprop', 'user|extmetadata'),
                                        ('iilimit', '1'),
                                        ('generator', 'categorymembers'),
                                        ('gcmprop', 'title'),
                                        ('gcmnamespace', '6'),
                                        ('gcmlimit', str(gcmlimit)),
                                        ('gcmtitle', maincat.encode('utf-8'))
                                       ])
        #store (part of) the json
        imageInfo.update(jsonr['query']['pages']) # a dict where pageId is the key
        
        #while continue get the rest
        counter = 0
        while('query-continue' in jsonr.keys()):
            counter += gcmlimit
            if verbose: 
                print u'Retrieved %d out of %d (roughly)' %(counter, total)
            jsonr = self.cApi.httpGET("query", [('prop', 'imageinfo'),
                                            ('iiprop', 'user|extmetadata'),
                                            ('iilimit', '1'),
                                            ('generator', 'categorymembers'),
                                            ('gcmprop', 'title'),
                                            ('gcmnamespace', '6'),
                                            ('gcmlimit', str(gcmlimit)),
                                            ('gcmcontinue',jsonr['query-continue']['categorymembers']['gcmcontinue']),
                                            ('gcmtitle', maincat.encode('utf-8'))
                                           ])
            #store (part of) json
            imageInfo.update(jsonr['query']['pages'])
            if testing and counter >self._test_limit:
                break #shorter runs for testing
        
        #sucessfully reached end
        return None
    
    def getContent(self, pageId, getwikitext=False):
        '''given a pageId this queries the MediaWiki api for the parsed content of that page
           returns tuple (content, errorInfo) where errorInfo is None on success'''
        props = u'templates|externallinks'
        if getwikitext:
            props = u'templates|externallinks|wikitext'
        #/w/api.php?action=parse&format=json&pageid=27970534&prop=categories%7Ctemplates%7Cexternallinks
        jsonr = self.cApi.httpGET("parse", [('prop', props.encode('utf-8')),
                                        ('pageid', str(pageId))
                                       ])
            
        #check for error
        if 'error' in jsonr.keys():
            return (None, jsonr['error']['info'])
        elif 'parse' in jsonr.keys():
            return (jsonr['parse'], None)
        else:
            return (None, u'API parse reply did not contain "error"-key but also not "parse"-key. Unexpected and probably means something went really wrong')
    
    def parseImageInfo(self, imageJson, typeCategories):
        '''parse a single page in imageInfo reply from the API
           returns: tuple (error-type, errorMessage) where:
           * a successful test returns (None,None)
           * a critical error (stopping the program) returns (True, Message)
           * a minor error (skip this item) returns (False, Message)
        '''
        #Issues:
        ## Is more content validation needed?
        ## Filter out more credit stuff
        ## filter out more description stuff
        
        #outer info
        pageId = imageJson['pageid']
        title = imageJson['title'][len('File:'):].strip()
        
        #swithch to inner info
        imageJson = imageJson['imageinfo'][0]
        
        #checks prior to continuing
        if not imageJson['extmetadata']['CommonsMetadataExtension']['value'] == self.commonsMetadataExtension: #no guarantee that metadata is treated correctly if any other version
            #would probably want to stop whole process
            return (True, u'This uses a different version of the commonsMetadataExtension than the one the script was designed for. Expected: %s; Found: %s' %(self.commonsMetadataExtension, imageJson['extmetadata']['CommonsMetadataExtension']['value']))
        if pageId in self.images.keys(): #check if image already in dictionary
            #would probably only want to skip this image (or deal with it)
            return (False, u'pageId (%s) already in data: old:%s new:%s' %(pageId, self.images[pageId]['title'], title))
        
        #Prepare data object, not sent directly to data[pageId] in case errors are discovered downstream
        obj = {'title':title, 'in_list': False, 'monument_id': [], 'monument_type': [], 'problematic': False}
        
        #listing potentially interesting fields
        user        = imageJson['user'] #as backup for later field. Note that this is the latest uploader, not necessarily the original one.
        datePlain   = imageJson['extmetadata']['DateTime']['value'].strip() if u'DateTime' in imageJson['extmetadata'].keys() else None
        dateDig     = imageJson['extmetadata']['DateTimeDigitized']['value'].strip() if u'DateTimeDigitized' in imageJson['extmetadata'].keys() else None
        dateOrig    = imageJson['extmetadata']['DateTimeOriginal']['value'].strip() if u'DateTimeOriginal' in imageJson['extmetadata'].keys() else None
        dateMeta    = imageJson['extmetadata']['DateTimeMetadata']['value'].strip() if u'DateTimeMetadata' in imageJson['extmetadata'].keys() else None
        licenseShortName = imageJson['extmetadata']['LicenseShortName']['value'].strip() if u'LicenseShortName' in imageJson['extmetadata'].keys() else None
        licenseurl  = imageJson['extmetadata']['LicenseUrl']['value'].strip() if u'LicenseUrl' in imageJson['extmetadata'].keys() else None
        artist      = imageJson['extmetadata']['Artist']['value'].strip() if u'Artist' in imageJson['extmetadata'].keys() else None
        copyrighted = imageJson['extmetadata']['Copyrighted']['value'].strip() if u'Copyrighted' in imageJson['extmetadata'].keys() else None #if PD
        categories  = imageJson['extmetadata']['Categories']['value'].strip().split('|') if u'Categories' in imageJson['extmetadata'].keys() else None #if PD
        
        #Post processing:
        ## compare user with artist, Note that this is the oposit to the Europeana implementation
        obj['uploader'] = None #Only contains a value if also included in artist
        if artist:
            obj['photographer'] = self.linkCleanup(artist)
            if user in artist:
                obj['uploader'] = user
            else: 
                if '.org/wiki/User:' in obj['photographer']:
                    #normally means image has been touched by other user afterwards
                    obj['uploader'] = obj['photographer'][obj['photographer'].find('.org/wiki/User:')+len('.org/wiki/User:'):obj['photographer'].find('"',obj['photographer'].find('.org/wiki/User:'))]
                else:
                    obj['uploader'] = obj['photographer']
        elif user: #if only uploader is given
            #should this be allowed?
            obj['photographer'] = None
            obj['uploader'] = user
            return (False, u'%s did not have any information about the creator apart from uploader (%s)' %(title,obj['uploader']))
        else: #no indication of creator
            return (False, u'%s did not have any information about the creator' %title)
        
        #For some reason '&' can get returned as %26
        obj['uploader'] = obj['uploader'].replace('%26','&')
        
        ## Deal with licenses
        if licenseurl:
            if licenseurl.startswith(u'http://creativecommons.org/licenses/'):
                obj[u'copyright'] = licenseShortName
            elif licenseurl.startswith(u'http://creativecommons.org/publicdomain/'):
                obj[u'copyright'] = 'PD'
            else:
                return (False, u'%s did not have a CC-license URL and is not PD: %s (%s)' %(title, licenseurl, licenseShortName))
        else:
            if copyrighted == u'False':
                obj[u'copyright'] = 'PD'
            else:
                return (False, u'%s did not have a license URL and is not PD: %s' %(title, licenseShortName))
        
        ## isolate date giving preference to dateOrig
        if dateOrig: #the date as described in the description
            #format (timestamp is optional): <time class="dtstart" datetime="2013-08-26">26 August  2013</time>, 09:51:00
            needle = u'<time class="dtstart" datetime='
            if needle in dateOrig: 
                dateOrig = dateOrig[dateOrig.find(needle):]
                date = dateOrig.split('"')[3]
                obj['created'] = date
            elif u'<time' in dateOrig: #weird
                return (False, u'%s did not have a recognised datestamp: %s' %(title, dateOrig))
            else: #just plain text
                self.log.write(u'%s has plain text date: %s\n'%(title, dateOrig))
                obj['created'] = dateOrig
        elif dateDig and dateDig != u'0000:00:00 00:00:00':
            obj['created'] = dateDig
        elif datePlain and datePlain != u'0000:00:00 00:00:00':
            obj['created'] = datePlain
        elif dateMeta and dateMeta != u'0000:00:00 00:00:00':
            obj['created'] = dateMeta
        else:
            obj['created'] = u''
        
        #identify type based on category
        if categories:
            for k, v in typeCategories.iteritems():
                if k in categories:
                    obj['monument_type'].append(v)
        
        #successfully reached the end
        self.images[pageId] = obj
        return (None, None)
    
    def parseContent(self, pageId, contentJson):
        '''parse a single parse reply from the API
           with the aim of identifying the institution links, non-maintanance categories and used templates.
           adds to data: categories (list), sourcelinks (list)
           returns: None on success otherwise an error message
           '''
        #structure up info as simple lists
        templates = []
        for t in contentJson['templates']:
            if 'exists' in t.keys(): templates.append(t['*'])
        extLinks = contentJson['externallinks'] #not really needed
        wikitext = ''
        if 'wikitext' in contentJson.keys():
            wikitext = contentJson['wikitext']['*']
        
        #Checking that the information structure is supported
        supported = False
        for t in self.infoTemplate:
            if t in templates:
                supported = True
        if not supported:
            return u'Does not contain a supported information template'
        
        #Isolate the source templates and identify the source links
        #self.images[monument_type] = lista
        for mt in self.images[pageId]['monument_type']:
            url_patterns = self.settings['types'][mt]['url_pattern']
            found = False
            for e in extLinks:
                for u in url_patterns:
                    if e.startswith(u):
                        self.images[pageId][u'monument_id'].append((mt, e[len(u):].strip()))
                        found = True
            if not found: #need to do something with the wikitext
                #no id found for a monument_type known to be present
                type_template = self.settings['types'][mt]['commons_template']
                if (u'Template:' +type_template) in templates: #check that template is actually there
                    tags = []
                    #regex and replace to
                    ##convert to lowercase (to avoid problem with capitalisation of first letter of template)
                    ##replace '{{template:' by '{{' (sometimes still used)
                    ## remove any whitespace between '{{' and template name
                    ## remove any whitespace before '|'
                    wikitext = re.sub(r'{{[(template:|\s) ]*', '{{', re.sub(r'[\s]*\|', '|', wikitext.lower()))
                    
                    #search for {{templatename| to remove false positives (e.g. {{templatename-not|) and ensure there is always at least one parameter
                    while wikitext.find(('{{'+type_template+'|').lower()) >=0: 
                        wikitext = wikitext[wikitext.find(('{{'+type_template+'|').lower())+len('{{'):] #crop until first tag, incl. brackets to avoid loop
                        tags.append(wikitext[:wikitext.find('}}')]) # isolate first tag
                        
                    if tags:
                        #assumes id is first parameter (without an alias) (true for 2014 and before)
                        for t in tags:
                            idNo = None
                            vals = t.split('|')
                            if len(vals) < 2:
                                continue
                            elif not '=' in vals[1]: #first one is template name
                                idNo = vals[1].strip()
                                self.images[pageId][u'monument_id'].append((mt, vals[1].strip()))
                            else:
                                for v in vals[1:]:
                                    p = v.split('=')
                                    if p[0].strip() == '1':
                                        idNo = p[1].strip()
                                        break
                            #store idNo or return error
                            if idNo:
                                self.images[pageId][u'monument_id'].append((mt, idNo))
                            else:
                                return u'categorised as %s, with template %s, and tag %s but idNo could not be isolated' %(mt, type_template, t)
                    else:
                        return u'categorised as %s, with template %s but tag could not be isolated' %(mt, type_template)
                else:
                    return u'categorised as %s but no template/url present' %mt
        
        #successfully reached the end
        return None
    
    def linkCleanup(self, text):
        '''given a text which may contain links this cleans them up by removing internal classes
           The primary objective of this is to make the description field shorter and the photographer field more uniform.
        '''
        linkClasses = [u'class="new"', u'class="extiw"', u'class="external free"', u'class="mw-redirect"']
        redlink = {u'find':(u'&amp;action=edit&amp;redlink=1',u'/w/index.php?title='), u'replace':(u'',u'/wiki/')}
        
        #link classes - these can simply be replaced
        for l in linkClasses:
            text = text.replace(l,u'')
        
        #redlinks - first tuple needs to be present and is replaced by second tuple
        if (redlink['find'][0] in text) and (redlink['find'][1] in text):
            text = text.replace(redlink['find'][0],redlink['replace'][0]).replace(redlink['find'][1],redlink['replace'][1])
        
        return text.replace('  ',' ') #replacing double-whitespace
#End of Europeana.py fork

class MyException(Exception):
    pass

if __name__ == '__main__':
    import sys
    usage = '''Usage: python WLMStats.py infile option
\tinfile must be a json settings file
\toption (optional): can be set to:
\t\tverbose:\t toggles on verbose mode with additional output to the terminal
\t\ttest:\t\t toggles on testing (a verbose and limited run)'''
    argv = sys.argv[1:]
    if len(argv) == 1:
        WLMStats(argv[0])
    elif len(argv) == 2:
        if argv[1] == 'test':
            WLMStats(argv[0], test=True)
        elif argv[1] == 'verbose':
            WLMStats(argv[0], verbose=True)
        else:
            print usage
    else:
        print usage
#EoF
