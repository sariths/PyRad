#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    objview - Make a nice multi-view picture of an object

    This script is a re-write of Greg Ward's original c-shell script. The script
    can be found at: https://github.com/NREL/Radiance/blob/master/src/util/objpict.csh


    Sarith Subramaniam <sarith@sarith.in>,2016.
"""

from __future__ import division, print_function, unicode_literals
import os
import sys
import argparse
import tempfile
import shutil

__all__ = ('main')

if __name__ == '__main__' and not getattr(sys, 'frozen', False):
    _rp = os.environ.get('RAYPATH')
    if not _rp:
        print('No RAYPATH, unable to find support library');
        sys.exit(-1)
    for _p in _rp.split(os.path.pathsep):
        if os.path.isdir(os.path.join(_p, 'pyradlib')):
            if _p not in sys.path: sys.path.insert(0, _p)
            break
    else:
        print('Support library not found on RAYPATH');
        sys.exit(-1)

from pyradlib.pyrad_proc import Error, ProcMixin


SHORTPROGN = os.path.splitext(os.path.basename(sys.argv[0]))[0]

testRoom = """
void plastic wall_mat 0 0 5 .681 .543 .686 0 .2
void light bright 0 0 3 3000 3000 3000
bright sphere lamp0 0 0 4 4 4 -4 .1
bright sphere lamp1 0 0 4 4 0 4 .1
bright sphere lamp2 0 0 4 0 4 4 .1
wall_mat polygon box.1540 0 0 12
                  5                 -5                 -5
                  5                 -5                  5
                 -5                 -5                  5
                 -5                 -5                 -5
wall_mat polygon box.4620 0 0 12
                 -5                 -5                  5
                 -5                  5                  5
                 -5                  5                 -5
                 -5                 -5                 -5
wall_mat polygon box.2310 0 0 12
                 -5                  5                 -5
                  5                  5                 -5
                  5                 -5                 -5
                 -5                 -5                 -5
wall_mat polygon box.3267 0 0 12
                  5                  5                 -5
                 -5                  5                 -5
                 -5                  5                  5
                  5                  5                  5
wall_mat polygon box.5137 0 0 12
                  5                 -5                  5
                  5                 -5                 -5
                  5                  5                 -5
                  5                  5                  5
wall_mat polygon box.6457 0 0 12
                 -5                  5                  5
                 -5                 -5                  5
                  5                 -5                  5
                  5                  5                  5
"""

class Objpict(ProcMixin):
    pass

def main():
    parser = argparse.ArgumentParser(add_help=False,
                                     description='Make a nice multi-view picture'
                                                 ' of an object')

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.stderr.write('*cancelled*\n')
        sys.exit(1)
    except (Error) as e:
        sys.stderr.write('%s: %s\n' % (SHORTPROGN, str(e)))
        sys.exit(-1)
