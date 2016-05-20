#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Genambpos: A script to generate markers where ambient sampling occured.

A python rewrite of original Perl script by John Mardaljevic.

The perl script can be found here:
http://radiance-online.org/cgi-bin/viewcvs.cgi/ray/src/util/genambpos.pl?revision=2.7&view=markup

Related documentation can be found here:
http://climate-based-daylighting.com/lib/exe/fetch.php?media=tech_note_003.pdf

"""

from __future__ import division, print_function, unicode_literals
import os
import sys
import argparse

# __all__ = ('main')

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

from pyradlib.pyrad_proc import Error, ProcMixin, PIPE

SHORTPROGN = os.path.splitext(os.path.basename(sys.argv[0]))[0]

ambientFormat = """
void glow posglow
0
0
4 ${agr} ${agg} ${agb} 0

posglow sphere position${recno}
0
0
4 ${  px  } ${  py  } ${  pz  } ${ psiz }
"""

posGradFormat = """
void glow arrglow
0
0
4 ${wt*agr} ${wt*agg} ${wt*agb} 0

arrglow cone pgarrow${recno}
0
0
8
    ${    cx0    }	${    cy0    }	${    cz0    }
    ${    cx1    }	${    cy1    }	${    cz1    }
    ${   cr0   }	0

void brightfunc pgpat
2 posfunc ambpos.cal
0
6 ${ px } ${ py } ${ pz } ${ pgx } ${ pgy } ${ pgz }

pgpat glow pgval
0
0
4 ${avr} ${avg} ${avb} 0

void mixfunc pgeval
4 pgval void ellipstencil ambpos.cal
0
9 ${ px } ${ py } ${ pz } ${ux/r0} ${uy/r0} ${uz/r0} ${vx/r1} ${vy/r1} ${vz/r1}

pgeval polygon pgellipse${recno}
0
0
12
    ${   px1   } ${   py1   } ${   pz1   }
    ${   px2   } ${   py2   } ${   pz2   }
    ${   px3   } ${   py3   } ${   pz3   }
    ${   px4   } ${   py4   } ${   pz4   }
"""

posGradFormatAppend = """
void glow tipglow
0
0
4 ${2*agr} ${2*agg} ${2*agb} 0

tipglow sphere atip
0
0
4 ${   cx1   } ${   cy1   } ${   cz1   } ${psiz/7}
"""

dirGradFormat = """
void brightfunc dgpat
2 dirfunc ambpos.cal
0
9 ${ px } ${ py } ${ pz } ${ nx } ${ ny } ${ nz } ${ dgx } ${ dgy } ${ dgz }

dgpat glow dgval
0
0
4 ${avr} ${avg} ${avb} 0

dgval ring dgdisk${recno}a
0
0
8
	${ px+dgx*.0002 } ${ py+dgy*.0002 } ${ pz+dgz*.0002 }
	${ dgx } ${ dgy } ${ dgz }
	0	${  r0/2  }

dgval ring dgdisk${recno}b
0
0
8
    ${ px-dgx*.001 } ${ py-dgy*.001 } ${ pz-dgz*.001 }
    ${ -dgx } ${ -dgy } ${ -dgz }
    0	${  r0/2  }"""


class Genambpos(ProcMixin):
    def __init__(self, args):
        self.ambientFile = args.AmbientFile[0]
        self.level = int(args.level) if args.level is not None else -1
        self.radius = ['-e', 'psiz:%s' % args.radius] if args.radius else []
        self.scalingFactor = float(args.scalingFactor)if args.scalingFactor is not None else 0.25
        self.position = args.position
        self.direct = args.direct
        self.minwt = float(args.minwt)if args.minwt is not None else 0.5001 ** 6

        self.posGradFormat = posGradFormat
        self.posGradFormatAppend = posGradFormatAppend
        self.ambientFormat = ambientFormat
        self.dirGradFormat = dirGradFormat

        self.run()

    def run(self):
        if os.path.exists(self.ambientFile):
            ambientAccValue = self.getAmbientAccValue()
            self.scalingFactor *= ambientAccValue

            lookambCmd = ['lookamb', '-h', '-d', self.ambientFile]

            rcalcCmd = ['rcalc',
                        '-e ',
                        'LV:{0};MW:{1};SF:{2}'.format(self.level, self.minwt,
                                                      self.scalingFactor),
                        '-f', 'rambpos.cal', '-e','cond=acond'] + \
                       self.radius + ['-o',  ambientFormat]

            self.call_two(lookambCmd, rcalcCmd,
                          'retrieve ambient values through lookamb',
                          'generate rad files with rcalc',
                          out=sys.stdout)

            if self.position:
                if self.direct:
                    posGradFormat = self.posGradFormat + self.posGradFormatAppend

                    rcalcCmdPos = rcalcCmd[:-1]+ [posGradFormat]

                    self.call_two(lookambCmd, rcalcCmdPos,
                                  'retrieve ambient values through lookamb',
                                  'generate rad files with rcalc for position option',
                                  out=sys.stdout)

            if self.direct:
                rcalcCmdDir = rcalcCmd[:6]+['cond=dcond','-o',dirGradFormat]

                self.call_two(lookambCmd,rcalcCmdDir,
                              'retrieve ambient values through lookamb',
                              'generate rad files with rcalc for direct option')

        else:
            self.raise_on_error('read ambient file',
                                'Either no file was specified or the specified '
                                'path does not exist.')

    def getAmbientAccValue(self):
        getinfoCmd = ['getinfo', self.ambientFile]
        ambInfo = self.call_one(getinfoCmd,
                                'retrive scene information from ambient file.',
                                out=PIPE)
        infoList = ambInfo.stdout.read().split()

        if '-aa' not in infoList:
            self.raise_on_error('read ambient accuracy in ambient file header',
                                '-aa value was missing in the header.')
        ambientAccValLocn = infoList.index('-aa') + 1
        ambientAccValue = float(infoList[ambientAccValLocn])

        if ambientAccValue < 0.00001:
            self.raise_on_error(
                'checking for correct -aa (ambient accuracy) value',
                '-aa value is %s, which is is invalid.' % ambientAccValue)
        return ambientAccValue


def main():
    parser = argparse.ArgumentParser(add_help=False,
                                     description='Generate markers where ambient '
                                                 'sampling occured')

    parser.add_argument('-l', action='store', dest='level',
                        help='level')
    parser.add_argument('-w', action='store', dest='minwt',
                        help='minwt')
    parser.add_argument('-r', action='store', dest='radius',
                        help='radius')
    parser.add_argument('-s', action='store', dest='scalingFactor',
                        help='scaling factor')
    parser.add_argument('-p', action='store_true', dest='position',
                        help='position')
    parser.add_argument('-d', action='store_true', dest='direct',
                        help='direct')
    parser.add_argument('AmbientFile', action='append',
                        help='full path of the ambient file that is to be '
                             'analyzed.')
    parser.add_argument('-H', action='help',
                        help='Help: print this text to stderr'
                             'and exit.')

    Genambpos(parser.parse_args())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.stderr.write('*cancelled*\n')
        sys.exit(1)
    except (Error) as e:
        sys.stderr.write('%s: %s\n' % (SHORTPROGN, str(e)))
        sys.exit(-1)
