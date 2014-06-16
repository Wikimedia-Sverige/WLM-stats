# -*- coding: utf-8  -*-
##WLM2011 stats getter
##Andre Costa
##2011-09-30
import os, codecs, urllib2

#import easy to use xml parser called minidom:
from xml.dom.minidom import parseString
import sys
sys.path.append("C:\Program Files\pywikibot-compat")
import wikipedia as pywikibot
import pagegenerators
'''Since output may include commas all output fields are separated by colons'''

class Prog1:
    '''Populates a two dictionaries with the bbrID and
       FornminneID along with the number of images for each ID
       Also records the first filename encountered for each ID'''
    def __init__(self):
        self.bbr_dict = {}
        self.forn_dict = {}
        self.fartyg_dict = {}
        self.bbrCounter = 0
        self.fornCounter = 0
        self.fartygCounter = 0
        self.noCounter = 0
        self.foutLog = codecs.open(u'.\\logfile2013.txt', 'w', 'utf-8')
    ##
    def finalise(self):
        self.foutLog.write('----------------------------------------\n')
        self.foutLog.write(u'BBR:  %d (%d)\n' % (self.bbrCounter, len(self.bbr_dict)))
        self.foutLog.write(u'Forn: %d (%d)\n' % (self.fornCounter, len(self.forn_dict)))
        self.foutLog.write(u'Fartyg: %d (%d)\n' % (self.fartygCounter, len(self.fartyg_dict)))
        self.foutLog.write(u'NO:   %d\n' % (self.noCounter, ))
        self.foutLog.close()
        print(u'The file %s was created' %(self.foutLog.name,))
    ##
    def dictsToFile(self):
        bbrOut = codecs.open(u'.\\BBR_dict2013.txt', 'w', 'utf-8')
        for key in self.bbr_dict.keys():
            s = u'%s:%d:%s\n' %(key, self.bbr_dict[key][0], self.bbr_dict[key][1])
            bbrOut.write(s)
        bbrOut.close
        fornOut = codecs.open(u'.\\forn_dict2013.txt', 'w', 'utf-8')
        for key in self.forn_dict.keys():
            s = u'%s:%d:%s\n' %(key, self.forn_dict[key][0], self.forn_dict[key][1])
            fornOut.write(s)
        fornOut.close
        fartygOut = codecs.open(u'.\\fartyg_dict2013.txt', 'w', 'utf-8')
        for key in self.fartyg_dict.keys():
            s = u'%s:%d:%s\n' %(key, self.fartyg_dict[key][0], self.fartyg_dict[key][1])
            fartygOut.write(s)
        fartygOut.close
        print(u'The files %s, %s and %s were created'% (bbrOut.name, fornOut.name, fartygOut.name))
    ##
    def runOnWiki(self):
        '''runs the parser on all imagepages in a given category on Wikimedia Commons'''
        pywikibot.setSite(pywikibot.getSite(u'commons', u'commons'))
        generator = None
        genFactory = pagegenerators.GeneratorFactory()
        #read in the desired category in a way which allows a default one to be given by pressing enter
        defaultCat = u'Images from Wiki Loves Monuments 2013 in Sweden'
        catTitle = raw_input(u'Category [%s]: '% defaultCat)
        catTitle = catTitle or defaultCat
        #
        genFactory.handleArg(u'-cat:'+catTitle)
        generator = genFactory.getCombinedGenerator()
        pgenerator = pagegenerators.PreloadingGenerator(pagegenerators.NamespaceFilterPageGenerator(generator, [6]), pageNumber = 100)
        for page in pgenerator:
            imagepage = pywikibot.ImagePage(page.site(), page.title())
            self.pageParser(imagepage.get(throttle = True),page.title())
        self.finalise()
        self.dictsToFile()
    ##
    ##Parses the wikipedia page for recognised WLM-tags
    def pageParser(self, page, pagename):
        pagename = pagename[len('File:'):]
        found = False      ##whether a bbr, fornmine or fartyg tag was found
        ##
        lines = page.split('\n')
        for line in lines:
            if '{{BBR|'.lower() in line.lower():               ##only parse the relevant lines
                if self.bbrParser(line, pagename):
                    self.bbrCounter += 1
                found = True
                break
            elif '{{fornminne|' in line.lower():
                if self.fornParser(line, pagename):
                    self.fornCounter += 1
                found = True
                break
            elif '{{K-Fartyg|' in line:
                self.fartygCounter += 1
                self.fartygParser(line, pagename)
                found = True
                break
        if (not found):   ##no tags found
            self.noCounter += 1
            self.foutLog.write(u'No valid tag in %s\n' %(pagename,))
    ##end of pageParser
    ##
    def bbrParser(self, line, filename): ## returns false if problematic id
        ##find the id
        testStr = '{{BBR|1 ='
        pos = line.find(testStr)
        if pos < 0:
            testStr = '{{BBR|1='
            pos = line.find(testStr)
            if pos < 0:
                testStr = '{{BBR|2=a|1='
                pos = line.find(testStr)
                if pos < 0:
                    testStr = '{{BBR|2=b|1='
                    pos = line.find(testStr)
                    if pos < 0:
                        testStr = '{{BBR|2=a|'
                        pos = line.find(testStr)
                        if pos < 0:
                            testStr = '{{BBR|'
                            pos = line.find(testStr)
                            if pos < 0:
                                self.foutLog.write(u'BBR missread: %s\n' %(line,))
                                return False
        pos = pos + len(testStr)
        line = line[pos:]
        endpos = line.find('}}')
        line = line[:endpos]
        splits = line.split('|')
        bbrID = splits[0].strip()
        ##
        ##verify id makes sense then add to dict
        try:
            int(bbrID)  ##is the id an integer
        except ValueError:
            self.foutLog.write(u'%s: is an invalid bbrID in %s\n' %(bbrID,filename))
            return False
        if(not len(bbrID) == 14) :
            self.foutLog.write(u'%s: is an invalid bbrID in %s\n' %(bbrID,filename))
            return False
        ##id is now confirmed to be a 14 digit number
        if not self.bbr_dict.has_key(bbrID):
            self.bbr_dict[bbrID] = (1, filename)
        else:
            t = self.bbr_dict[bbrID]
            num = t[0] + 1
            self.bbr_dict[bbrID] = (num, t[1])
        return True
    ##
    def fornParser(self, line, filename): ## returns false if problematic id
        ##find the id
        testStr = '{{fornminne|1 ='
        pos = line.lower().find(testStr)
        if pos < 0:
            testStr = '{{fornminne|1='
            pos = line.lower().find(testStr)
            if pos < 0:
                testStr = '{{fornminne|'
                pos = line.lower().find(testStr)
                if pos < 0:
                    self.foutLog.write(u'Fornminne missread: %s\n' %(line,))
                    return False
        pos = pos + len(testStr)
        line = line[pos:]
        endpos = line.find('}}')
        line = line[:endpos]
        splits = line.split('|')
        fornID = splits[0].strip()
        ##
        ##verify id makes sense then add to dict
        try:
            int(fornID)  ##is the id an integer
        except ValueError:
            self.foutLog.write(u'%s: is an invalid fornID in %s\n' %(fornID,filename))
            return False
        if(not len(fornID) == 14) :
            self.foutLog.write(u'%s: is an invalid fornID in %s\n' %(fornID,filename))
            return False
        ##id is now confirmed to be a 14 digit number
        if not self.forn_dict.has_key(fornID):
            self.forn_dict[fornID] = (1, filename)
        else:
            t = self.forn_dict[fornID]
            num = t[0] + 1
            self.forn_dict[fornID] = (num, t[1])
        return True
    ##
    def fartygParser(self, line, filename): 
        ##find the id
        testStr = '{{K-Fartyg|1 ='
        pos = line.find(testStr)
        if pos < 0:
            testStr = '{{K-Fartyg|1='
            pos = line.find(testStr)
            if pos < 0:
                testStr = '{{K-Fartyg|'
                pos = line.find(testStr)
                if pos < 0:
                    self.foutLog.write(u'K-Fartyg missread: %s\n' %(line,))
                    return False
        pos = pos + len(testStr)
        line = line[pos:]
        endpos = line.find('}}')
        line = line[:endpos]
        splits = line.split('|')
        fartygID = splits[0].strip()
        if not self.fartyg_dict.has_key(fartygID):
            self.fartyg_dict[fartygID] = (1, filename)
        else:
            t = self.fartyg_dict[fartygID]
            num = t[0] + 1
            self.fartyg_dict[fartygID] = (num, t[1])
    ##end of fartygParser
##end of Prog1

#Prog2 should be redone so as to be able to be the same for all types
class Prog2BBR:
    '''Goes over the sv.wiki lists and adds more info to the bbr_dictionary
       also checks if the image is currently illustrated and if not whether
       dictionary contains an appropriate image.'''
    def __init__(self, bbr_dict):#(self, dDict, prefix)
        self.bbr_dict = bbr_dict  ##= {}
        self.illLog = codecs.open(u'.\\illSuggestionsBBR.txt', 'w', 'utf-8')
        # self.setting = {'defaultCat':u'Listor över byggnadsminnen i Sverige per region', 'testStr':u'Lista över byggnadsminnen i ', 'testStr2':'Lista över kyrkliga kulturminnen i ', 'row':'{{BBR', 'header':'{{BBR-huvud', 'parser':bbrParser2}
    ##
    def finalise(self):
        self.illLog.close()
        print(u'The file %s was created' %(self.illLog.name,))
    ##
    def dictToFile(self):
        bbrOut = codecs.open(u'.\\BBR_dict2.txt', 'w', 'utf-8')
        for key in self.bbr_dict.keys():
            s = u'%s:%d:%s' %(key, self.bbr_dict[key][0], self.bbr_dict[key][1])
            if len(self.bbr_dict[key])>2:
                s+= u':%s:%s:%s:%s:%s' %(self.bbr_dict[key][2], self.bbr_dict[key][3], self.bbr_dict[key][4], self.bbr_dict[key][5], self.bbr_dict[key][6])
            s += u'\n'
            bbrOut.write(s)
        bbrOut.close
        print(u'The file %s was created' %(bbrOut.name,))
    ##
    def runOnWiki(self):
        '''runs the parser on all pages in a given category on Swedish Wikipedia'''
        site = pywikibot.getSite(u'sv', u'wikipedia')
        pywikibot.setSite(site)
        generator = None
        genFactory = pagegenerators.GeneratorFactory()
        #read in the desired category in a way which allows a default one to be given by pressing enter
        defaultCat = u'Listor över byggnadsminnen i Sverige per region'
        #catTitle = raw_input(u'Category [%s]: '% defaultCat)
        #catTitle = catTitle or defaultCat
        catTitle = defaultCat
        #
        genFactory.handleArg(u'-cat:'+catTitle)
        generator = genFactory.getCombinedGenerator()
        pgenerator = pagegenerators.PreloadingGenerator(pagegenerators.NamespaceFilterPageGenerator(generator, [0]), pageNumber = 10)
        for page in pgenerator:
            self.pageParserSV(page.get(throttle = True),page.title())
        self.finalise()
        self.dictToFile()
    ##
    def pageParserSV(self, page, pagename):
        testStr = u'Lista över byggnadsminnen i '
        typ = 'B'
        pos = pagename.find(testStr)
        if pos < 0 :
            testStr = u'Lista över kyrkliga kulturminnen i '
            typ = 'K'
        pos += len(testStr)
        lan = pagename[pos:].strip()
        ##
        lines = page.split('\n')
        i = 0
        while i < len(lines):
            if lines[i].startswith('{{BBR'):               ##only parse the relevant lines
                if not lines[i].startswith('{{BBR-huvud'):
                    i = self.bbrParser2(lines, i, lan, typ)
            i += 1
    ##end of pageParserSV
    def bbrParser2(self, lines, i, lan, typ): ## returns false if problematic id
        illustrated = False
        isInDict = False
        line = lines[i]
        ##find all parameters
        while not lines[i].startswith('| kommun'):
            i += 1
            line = lines[i]
        kommunID = line[len('| kommun = '):].strip()
        i += 1
        line = lines[i]
        latCord = line[len('| lat = '):].strip()
        i += 1
        line = lines[i]
        longCord = line[len('| long = '):].strip()
        i += 1
        line = lines[i]
        bbrID = line[len('| bbr = '):].strip()
        i += 1
        line = lines[i]
        ##match to id in bbr_dict
        if self.bbr_dict.has_key(bbrID):
            isInDict = True
        ##check if we have a pic
        if ( line.startswith('| bild') or line.startswith('|bild') ):
            splits = line.split('=')
            if ( len(splits[1].strip()) > 3):
                illustrated = True
        elif line.startswith('}}'):
            pass
        else:
            print(u'varken bild eller }} %s' %(line,))
            exit()
        ##can we add a pic if one is missing?
        if ((not illustrated) and isInDict):
        self.illLog.write(u'%s:%s:%s:[%d]:%s\n' %(lan, kommunID, bbrID, self.bbr_dict[bbrID][0], self.bbr_dict[bbrID][1]))
        ##upgrade bbr_dict
        if isInDict:
            t = self.bbr_dict[bbrID]
            self.bbr_dict[bbrID] = (t[0], t[1], lan, kommunID, latCord, longCord, typ)
        return i
    ##end of bbrParser2
##end of Prog2BBR

class Prog2FMIS:
    '''Goes over the sv.wiki lists and adds more info to the fmis_dictionary
       also checks if the image is currently illustrated and if not whether
       dictionary contains an appropriate image.'''
    def __init__(self, fmis_dict):
        self.fmis_dict = fmis_dict  ##= {}
        self.illLog = codecs.open(u'.\\illSuggestionsFMIS.txt', 'w', 'utf-8')
    ##
    def finalise(self):
        self.illLog.close()
        print('The file '+self.illLog.name+' was created')
    ##
    def dictToFile(self):
        fmisOut = codecs.open(u'.\\forn_dict2.txt', 'w', 'utf-8')
        for key in self.fmis_dict.keys():
            s = key + ':'
            s +='%d:' % self.fmis_dict[key][0]
            s += self.fmis_dict[key][1]
            if len(self.fmis_dict[key])>2:
                s+=':' + self.fmis_dict[key][2]
                s+=':' + self.fmis_dict[key][3]
                s+=':' + self.fmis_dict[key][4]
                s+=':' + self.fmis_dict[key][5]
                s+=':' + self.fmis_dict[key][6]
            s += '\n'
            fmisOut.write(s)
        fmisOut.close
        print('The file '+fmisOut.name+' was created')
    ##
    def runOnWiki(self):
        '''runs the parser on all pages in a given category on Swedish Wikipedia'''
        site = pywikibot.getSite(u'sv', u'wikipedia')
        pywikibot.setSite(site)
        generator = None
        genFactory = pagegenerators.GeneratorFactory()
        #read in the desired category in a way which allows a default one to be given by pressing enter
        defaultCat = u'Listor över fornminnen i Sverige per kommun'
        catTitle = raw_input(u'Category [%s]: ' % defaultCat)
        catTitle = catTitle or defaultCat
        #
        genFactory.handleArg(u'-catr:'+catTitle)
        generator = genFactory.getCombinedGenerator()
        pgenerator = pagegenerators.PreloadingGenerator(pagegenerators.NamespaceFilterPageGenerator(generator, [0]), pageNumber = 10)
        for page in pgenerator:
            self.pageParserSV(page.get(throttle = True),page.title())
        self.finalise()
        self.dictToFile()
    ##
    def pageParserSV(self, page, pagename):
        lan=''
        lines = page.split('\n')
        i = 0
        while i < len(lines):
            if lines[i].startswith('{{FMIS-huvud'):
                pos = lines[i].find('}}')
                lan = lines[i][len('{{FMIS-huvud|region-iso='):pos]
            elif lines[i].startswith('{{FMIS'):
                i = self.fmisParser2(lines, i, lan)
            i += 1
        #
    ##end of pageParserSV
    def fmisParser2(self, lines, i, lan): ## returns false if problematic id
        illustrated = False
        isInDict = False
        line = lines[i]
        ##find all parameters
        while not lines[i].startswith(' | typ       = '):
            i += 1
            line = lines[i]
        typ = line[len(' | typ       = '):].strip()
        i += 2
        line = lines[i]
        kommunID = line[len(' | kommun    = '):].strip()
        i += 4
        line = lines[i]
        latCord = line[len(' | lat       = '):].strip()
        i += 1
        line = lines[i]
        longCord = line[len(' | long      = '):].strip()
        i += 1
        line = lines[i]
        fmisID = line[len(' | id        = '):].strip()
        i += 1
        line = lines[i]
        ##match to id in bbr_dict
        if self.fmis_dict.has_key(fmisID):
            isInDict = True
        ##check if we have a pic
        if ( line.startswith(' | bild      = ') ):
            splits = line.split('=')
            if ( len(splits[1].strip()) > 3):
                illustrated = True
        elif line.startswith('}}'):
            pass
        else:
            print('varken bild eller }}' + line)
            exit()
        ##can we add a pic if one is missing?
        if ((not illustrated) and isInDict):
            self.illLog.write(lan+':'+kommunID+':'+fmisID+':'+ '[%d]:'%(self.fmis_dict[fmisID][0],) + self.fmis_dict[fmisID][1]+'\n')
        ##upgrade fmis_dict
        if isInDict:
            t = self.fmis_dict[fmisID]
            self.fmis_dict[fmisID] = (t[0], t[1], lan, kommunID, latCord, longCord, typ)
        return i
    ##end of fmisParser2
##end of Prog2FMIS

#Prog2Fartyg

class Prog3BBR:
    '''Goes through the sv.wiki lists and determines the ratio of illustrated
       to unillustrated entries for each municipality'''
    def __init__(self):
        self.kommun_dict = {}
    ##
    def dictsToFile3(self):
        bbrCount = codecs.open(u'.\\bbrCounter.txt', 'w', 'ISO-8859-1')
        for key in self.kommun_dict.keys():
            s = key + ':'
            s += '%d:' % (self.kommun_dict[key][0],)
            s += '%d:' % (self.kommun_dict[key][1],)
            s += self.kommun_dict[key][2] + '\n'
            bbrCount.write(s)
        bbrCount.close
        print('The file '+bbrCount.name+' was created')
    ##
    def runOnWiki(self):
        '''runs the parser on all pages in a given category on Swedish Wikipedia'''
        site = pywikibot.getSite(u'sv', u'wikipedia')
        pywikibot.setSite(site)
        generator = None
        genFactory = pagegenerators.GeneratorFactory()
        #read in the desired category in a way which allows a default one to be given by pressing enter
        defaultCat = u'Listor över byggnadsminnen i Sverige per region'
        catTitle = raw_input(u'Category [%s]: ' % defaultCat)
        catTitle = catTitle or defaultCat
        #
        genFactory.handleArg(u'-cat:'+catTitle)
        generator = genFactory.getCombinedGenerator()
        pgenerator = pagegenerators.PreloadingGenerator(pagegenerators.NamespaceFilterPageGenerator(generator, [0]), pageNumber = 10)
        for page in pgenerator:
            self.pageParserSVCount(page.get(throttle = True),page.title())
        self.dictsToFile3()
    ##
    def pageParserSVCount(self, page, pagename):
        testStr = u'Lista över byggnadsminnen i '
        pos = pagename.find(testStr)
        if pos < 0 :
            testStr = u'Lista över kyrkliga kulturminnen i '
        pos += len(testStr)
        lan = pagename[pos:].strip()
        ##
        lines = page.split('\n')
        i = 0
        while i < len(lines):
            if lines[i].startswith('{{BBR'):               ##only parse the relevant lines
                if not lines[i].startswith('{{BBR-huvud'):
                    i = self.bbrParser3(lines, i, lan)
            i += 1
    ##
    def bbrParser3(self, lines, i, lan): ## returns false if problematic id
        illustrated = False
        ##find all parameters
        while not lines[i].startswith('| kommun'):
            i += 1
        kommunID = lines[i][len('| kommun = '):].strip()
        i += 1
        while not ( lines[i].startswith('| bild') or lines[i].startswith('|bild') or lines[i].startswith('}}')):
            i += 1
        line = lines[i]
        ##check if we have a pic
        if ( line.startswith('| bild') or line.startswith('|bild') ):
            splits = line.split('=')
            if (len(splits[1].strip()) > 3):
                illustrated = True
        elif line.startswith('}}'):
            pass
        else:
            print('varken bild elle }}' + line)
            exit()
        ##update kommun_dict
        if self.kommun_dict.has_key(kommunID):  ##if id is already in dictionary
            t = self.kommun_dict[kommunID]
            num = t[0]+1
            ill = t[1]
            if illustrated:
                ill +=1
            self.kommun_dict[kommunID] = (num, ill, t[2])
        else:                                   ## if new
            ill = 0
            if illustrated:
                ill +=1
            self.kommun_dict[kommunID] = (1,ill,lan)
        return i
    ##
##end of Prog3BBR

class Prog3FMIS:
    '''Goes through the sv.wiki lists and determines the ratio of illustrated
       to unillustrated entries for each municipality'''
    def __init__(self):
        self.kommun_dict = {}
    ##
    def dictsToFile3(self):
        fmisCount = codecs.open(u'.\\fornCounter.txt', 'w', 'ISO-8859-1')
        for key in self.kommun_dict.keys():
            s = key + ':'
            s += '%d:' % (self.kommun_dict[key][0],)
            s += '%d:' % (self.kommun_dict[key][1],)
            s += self.kommun_dict[key][2] + '\n'
            fmisCount.write(s)
        fmisCount.close
        print('The file '+fmisCount.name+' was created')
    ##
    def runOnWiki(self):
        '''runs the parser on all pages in a given category on Swedish Wikipedia'''
        site = pywikibot.getSite(u'sv', u'wikipedia')
        pywikibot.setSite(site)
        generator = None
        genFactory = pagegenerators.GeneratorFactory()
        #read in the desired category in a way which allows a default one to be given by pressing enter
        defaultCat = u'Listor över fornminnen i Sverige per kommun'
        catTitle = raw_input(u'Category [%s]: ' % defaultCat)
        catTitle = catTitle or defaultCat
        #
        genFactory.handleArg(u'-catr:'+catTitle)
        generator = genFactory.getCombinedGenerator()
        pgenerator = pagegenerators.PreloadingGenerator(pagegenerators.NamespaceFilterPageGenerator(generator, [0]), pageNumber = 10)
        for page in pgenerator:
            self.pageParserSVCount(page.get(throttle = True),page.title())
        self.dictsToFile3()
    ##
    def pageParserSVCount(self, page, pagename):
        lan=''
        lines = page.split('\n')
        i = 0
        while i < len(lines):
            if lines[i].startswith('{{FMIS-huvud'):
                pos = lines[i].find('}}')
                lan = lines[i][len('{{FMIS-huvud|region-iso='):pos]
            elif lines[i].startswith('{{FMIS'):
                i = self.fmisParser3(lines, i, lan)
            i += 1
        #
    ##
    def fmisParser3(self, lines, i, lan): ## returns false if problematic id
        illustrated = False
        ##find all parameters
        while not lines[i].startswith(' | kommun    = '):
            i += 1
        kommunID = lines[i][len(' | kommun    = '):].strip()
        i += 1
        while not ( lines[i].startswith(' | bild      = ') or lines[i].startswith('}}')):
            i += 1
        line = lines[i]
        ##check if we have a pic
        if ( line.startswith(' | bild      = ') ):
            splits = line.split('=')
            if (len(splits[1].strip()) > 3):
                illustrated = True
        elif line.startswith('}}'):
            pass
        else:
            print('varken bild elle }}' + line)
            exit()
        ##update kommun_dict
        if self.kommun_dict.has_key(kommunID):  ##if id is already in dictionary
            t = self.kommun_dict[kommunID]
            num = t[0]+1
            ill = t[1]
            if illustrated:
                ill +=1
            self.kommun_dict[kommunID] = (num, ill, t[2])
        else:                                   ## if new
            ill = 0
            if illustrated:
                ill +=1
            self.kommun_dict[kommunID] = (1,ill,lan)
        return i
    ##
##end of Prog3FMIS

class Prog4:
    '''Goes through the kulturdata rdf files and extracts more parameters to add to the forn_dict'''
    def __init__(self, forn_dict={}):
        self.forn_dict = forn_dict
        self.foutLog = codecs.open(u'.\\logForn.txt', 'w', 'utf-8')
    ##
    def dictToFile(self):
        '''outputs the updated forn_dict'''
        fornOut = codecs.open(u'.\\forn_dict2_extra.txt', 'w', 'utf-8')
        for key in self.forn_dict.keys():
            s = key + ':'
            s +='%d:' % int(self.forn_dict[key][0])
            s += self.forn_dict[key][1]
            if len(self.forn_dict[key])>2:
                s+=':' + self.forn_dict[key][2]
                s+=':' + self.forn_dict[key][3]
                s+=':' + self.forn_dict[key][4]
                s+=':' + self.forn_dict[key][5]
                s+=':' + self.forn_dict[key][6]
            s += '\n'
            fornOut.write(s)
        fornOut.close
        print('The file '+fornOut.name+' was created')
    #
    def dictFromFile(self, fileName):
        '''If no dict was given at initialisation the nthis allows one to be
           created based on a file (as outputed by Prog1)'''
        #open the file for reading:
        try:
            fil = codecs.open(u'.\\'+fileName, 'r', 'utf-8')
        except IOError:
            print 'The given parameter doesn not seem to be a valid filename'
            exit()
        except:
            print 'That argument wasn\'t even a string'
            exit()
        #convert to string:
        data = fil.read()
        #close file because we dont need it anymore:
        fil.close()
        #parse lines
        lines = data.split('\n')
        for line in lines:
            entries = line.split(':')
            self.forn_dict[entries[0]] = (int(entries[1]), entries[2])
    #
    def getFromKulturarvsdata(self, id):
        '''Given a valid fornID this method retrieves the relevant rdf file from  kulturarvsdata.se
           an error cehcker should be added in case an invalid id is passed'''
        #download the file:
        try:
            fil = urllib2.urlopen('http://kulturarvsdata.se/raa/fmi/'+id)
        except urllib2.HTTPError, error: #Couldn\'t get kulturarvsdata page. Site is either down or id is invalid
            print (id+': HTTPError: ' +str(error.code))
            self.foutLog.write(id+': HTTPError: ' +str(error.code)+'\n'+ error.read()+'\n\n')
            return 0                               ##returns an integer if page not found, allowing calling program to destinguish it from valid content
        #convert to string:
        data = fil.read()
        #close file because we dont need it anymore:
        fil.close()
        return data
    #
    def getFromFile(self, fileName):
        '''Mainly for testing. This does the job of the above but taking the rdf data from a loccal file'''
        #open the file for reading:
        try:
            fil = codecs.open(u'.\\'+fileName, 'r')
        except IOError:
            print 'The given parameter doesn not seem to be a valid filename'
            exit()
        except:
            print 'That argument wasn\'t even a string'
            exit()
        #convert to string:
        data = fil.read()
        #close file because we dont need it anymore:
        fil.close()
        return data
    #
    def updateDict(self):
        '''Updates each entry in forn_dict based on rdf files at kulturarvsdata.se'''
        for key in self.forn_dict.keys():
            if not len(self.forn_dict[key])>2:
                self.fornParser(key)
        self.dictToFile()
        self.foutLog.close()
        print('The file '+self.foutLog.name+' was created')
    #
    def fornParser(self, fornID):
        '''Goes through a kulturdata rdf file and adds data to a dict entry of the format
        fornID, numImages, firstImage, lan, kommun, lat, long, typ'''
        data = self.getFromKulturarvsdata(fornID)
        if(data == 0):       ##if urlfetching failed then go to next id
            return
        #parse the xml you downloaded
        dom = parseString(data)
        #first tag - typ
        tagName = u'pres:itemLabel'
        #retrieve the first xml tag (<tag>data</tag>) that the parser finds with name tagName:
        xmlTag = dom.getElementsByTagName(tagName)[0].toxml()
        #strip off the tag (<tag>data</tag>  --->   data):
        typ=xmlTag.replace('<'+tagName+'>','').replace('</'+tagName+'>','')
        #second tag county
        tagName = u'ns5:countyName'
        xmlTag = dom.getElementsByTagName(tagName)[0].toxml()
        county=xmlTag.replace('<'+tagName+'>','').replace('</'+tagName+'>','')
        #third tag kommun
        tagName = u'ns5:municipalityName'
        xmlTag = dom.getElementsByTagName(tagName)[0].toxml()
        kommun=xmlTag.replace('<'+tagName+'>','').replace('</'+tagName+'>','')
        #fourth and fifth tag - coord, need to be careful since this doesn't always exist
        tagName = 'gml:coordinates'
        xmlTags = dom.getElementsByTagName(tagName)
        if(len(xmlTags)<1):## if no such tag
            coord = ['','']
        else:
            xmlTag = xmlTags[0].toxml()
            coords=xmlTag.replace('<'+tagName+' cs="," decimal="." ts=" ">','').replace('</'+tagName+'>','')
            coord = coords.split(',')
        if self.forn_dict.has_key(fornID):
            t = self.forn_dict[fornID]
            self.forn_dict[fornID] = (t[0], t[1], county, kommun, coord[1], coord[0], typ)
        else:
            print('You\'ve run this parser for a stand-alone ID so all I can do is print it out.\n')
            print(county+':'+kommun+':'+coord[1]+':'+coord[0]+':'+typ)
    ##
##end of Prog4
class Prog5:
    '''contains two static methods for dealing with the bbr and forn dictionaries'''
    @staticmethod
    def dictFromFile(fileName, codec='utf-8'):
        '''Reads in a and parses a file containing an dict or augmented dict, i.e. bbr_dict2.txt, forn_dict2.txt'''
        #open the file for reading:
        try:
            fil = codecs.open(u'.\\'+fileName, 'r', codec)
        except IOError:
            print 'The given parameter doesn not seem to be a valid filename'
            exit()
        except:
            print 'That argument wasn\'t even a string'
            exit()
        #convert to string:
        data = fil.read()
        #close file because we dont need it anymore:
        fil.close()
        #parse lines
        aDict = {}
        lines = data.split('\n')
        for line in lines:
            if len(line) >0:
                entries = line.split(':')
                if (len(entries)<4):##some will stil be unaugmented
                    aDict[entries[0]] = (int(entries[1]), entries[2])
                else:
                    aDict[entries[0]] = (int(entries[1]), entries[2], entries[3], entries[4], entries[5], entries[6], entries[7])
        return aDict
    #
    @staticmethod
    def dictAnalysis(aDict):
        '''Figures out entries per county and entries per type in a given dict'''
        county_dict = {}
        typ_dict = {}
        for key in aDict.keys():
            if (len(aDict[key])>4):
                num = aDict[key][0]
                county = aDict[key][2]
                typ = aDict[key][6]
                #
                if not county_dict.has_key(county):
                    county_dict[county] = (num, 1)
                else:
                    county_dict[county] = (county_dict[county][0]+num,county_dict[county][1]+1)
                if not typ_dict.has_key(typ):
                    typ_dict[typ] = (num,1)
                else:
                    typ_dict[typ] = (typ_dict[typ][0]+num,typ_dict[typ][1]+1)
        #read in the desired category in a way which allows a default one to be given by pressing enter
        fileName = input(u'Filename [e.g. u\'dictCounter_forn.txt\']: ')
        dictOut = codecs.open(u'.\\'+fileName, 'w', 'utf-8')
        for key in county_dict.keys():
            dictOut.write(key+':%d:%d\n' % (county_dict[key][0],county_dict[key][1]))
        dictOut.write('\n-----------------------------------------------------------------------------------------------\n\n')
        for key in typ_dict.keys():
            dictOut.write(key+':%d:%d\n' % (typ_dict[key][0],typ_dict[key][1]))
        dictOut.close()
        print('The file '+dictOut.name+' was created')
    #
    @staticmethod
    def dictAnalysis2(bbrDict, fornDict):
        '''Figures out entries per municipality in both dicts'''
        muni_dict = {}
        #Go thorugh BBRdict
        for key in bbrDict.keys():
            if (len(bbrDict[key])>4):
                num = bbrDict[key][0]
                muni = bbrDict[key][3]
                #
                if not muni_dict.has_key(muni):
                    muni_dict[muni] = (num, 1, 0)
                else:
                    muni_dict[muni] = (muni_dict[muni][0]+num,muni_dict[muni][1]+1, 0)
        #Go thorugh forndict
        for key in fornDict.keys():
            if (len(fornDict[key])>4):
                num = fornDict[key][0]
                muni = fornDict[key][3]
                #
                if not muni_dict.has_key(muni):
                    muni_dict[muni] = (num, 0, 1)  #completly new muni
                else:
                    muni_dict[muni] = (muni_dict[muni][0]+num,muni_dict[muni][1],muni_dict[muni][2]+1)
        #read in the desired filename in a way which allows a default one to be given by pressing enter
        fileName = input(u'Filename [e.g. u\'muniCounter.txt\']: ')
        dictOut = codecs.open(u'.\\'+fileName, 'w', 'utf-8')
        dictOut.write('##id:total_number_of_images:num_unique_bbr:num_unique_forn\n')
        for key in muni_dict.keys():
            dictOut.write(key+':%d:%d:%d\n' % (muni_dict[key][0],muni_dict[key][1],muni_dict[key][2]))
        dictOut.close()
        print('The file '+dictOut.name+' was created')
    #
##End of Prog5
