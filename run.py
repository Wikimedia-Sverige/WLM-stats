#!/usr/bin/python
# -*- coding: utf-8  -*-
#
# By: André Costa, Wikimedia Sverige
# License: MIT
# 2015
#
# Script to run all processes
#
#
from WLMStats import WLMStats
from WLMStatsCruncher import WLMStatsCruncher
from UsageCruncher import UsageCruncher


def run(infile, verbose=False, test=False):
    stat = WLMStats(infile, verbose=verbose, test=test)
    identifier = stat.settings['identifier']
    if test:
        identifier = u'test.%s' % identifier
    imageData = u'./output/%s_images.json' % identifier
    monumentData = u'./output/%s_monuments.json' % identifier
    muniData = u'./output/%s_muni.json' % identifier
    WLMStatsCruncher(imageData, verbose=verbose, test=test)
    WLMStatsCruncher(muniData, verbose=verbose, test=test)
    UsageCruncher(imageData, monumentData, verbose=verbose, test=test)
    print 'Done'


if __name__ == '__main__':
    import sys
    usage = '''Usage: python run.py infile option
\tfile: the json indata file (the *_images.json output of WlmStats)
\toption (optional): can be set to:
\t\tverbose:\t toggles on verbose mode with additional output to the terminal
\t\ttest:\t\t toggles on testing (a verbose and limited run)
example: python run.py ./indata/wlm-se-2015.json verbose
'''
    argv = sys.argv[1:]
    if len(argv) == 1:
        run(argv[0])
    elif len(argv) == 2:
        if argv[1] == 'test':
            run(argv[0], test=True)
        elif argv[1] == 'verbose':
            run(argv[0], verbose=True)
        else:
            print usage
    else:
        print usage
