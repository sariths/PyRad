#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
objpict - render image of RADIANCE object(s)

This script is a re-write of Greg Ward's c-shell script of the same name. The
script can be found here:
https://github.com/NREL/Radiance/blob/master/src/util/objpict.csh

"""

from __future__ import division,print_function,unicode_literals
import os
import sys
import argparse
import shutil
import tempfile


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

from pyradlib.pyrad_proc import Error, ProcMixin,PIPE


SHORTPROGN = os.path.splitext(os.path.basename(sys.argv[0]))[0]


#Geometry that surrounds the radiance objects being rendered.
contextScene="""
void plastic wall_mat 0 0 5 .681 .543 .686 0 .2
void light bright 0 0 3 3000 3000 3000
bright sphere lamp0 0 0 4 4 4 -4 .1
bright sphere lamp1 0 0 4 4 0 4 .1
bright sphere lamp2 0 0 4 0 4 4 .1

wall_mat polygon box.1540
    0 0 12
    5 -5 -5     5 -5 5     -5 -5 5     -5 -5 -5

wall_mat polygon box.4620
    0 0 12
    -5 -5 5     -5 5 5     -5 5 -5     -5 -5 -5

wall_mat polygon box.2310
    0 0 12
    -5 5 -5     5 5 -5     5 -5 -5     -5 -5 -5

wall_mat polygon box.3267
    0 0 12
    5 5 -5     -5 5 -5     -5 5 5     5 5 5

wall_mat polygon box.5137
    0 0 12
    5 -5 5     5 -5 -5     5 5 -5     5 5 5

wall_mat polygon box.6457
    0 0 12
    -5 5 5     -5 -5 5     5 -5 5     5 5 5
"""



class Objpict(ProcMixin):
    def __init__(self,args):
        self.radFiles = args.RadFiles[0]
        self.donothing = args.N
        self.verbose = args.V or self.donothing

        self.tempdir = None
        try:
            self.run()
        finally:
            if self.tempDir:
                shutil.rmtree(self.tempDir)

    def run(self):
        if self.radFiles:
            self.createTemp()
            self.createSingleRadFile()
            radScaleTransValues = self.runSetupCalcs()
            self.runCalcProcs(**radScaleTransValues)

    def createTemp(self):
        """Create temporary files and directories needed for objpict"""
        try:
            self.tempDir = tempfile.mkdtemp('RAD')
        except IOError as e:
            self.raise_on_error("Create a temp folder", e)

        createInTemp = lambda fileName: os.path.join(self.tempDir, fileName)
        self.inputRad = createInTemp('input.rad')
        self.octree = createInTemp('octree.oct')
        self.testRoom = createInTemp('testRoom.rad')

        with open(self.testRoom,'w') as testRoom:
            testRoom.write(contextScene)

    def createSingleRadFile(self):
        """Merge all the input rad files into a single rad file."""
        try:
            with open(self.inputRad, 'w')as inputRadData:
                for radFile in self.radFiles:
                    with open(radFile) as currentRadFile:
                        for lines in currentRadFile:
                            inputRadData.write(lines)
        except IOError as e:
            self.raise_on_error(
                'write radiance file %s to a temp file' % radFile, e)

    def runSetupCalcs(self):
        """Launch getbbox and get dimensions, scaling values and transform
        coordinates for creating images."""

        getBboxCmd = ['getbbox', '-h', self.inputRad]
        radDimensions = self.call_one(getBboxCmd,
                                      'get the extents of the Rad files', out=PIPE)

        radDimensions = radDimensions.stdout.read().split()
        xMin, xMax, yMin, yMax, zMin, zMax = map(float, radDimensions)

        # Get the max axis aligned dimension. Calc the transformation coords and
        # scale value for the rad files.
        maxSize = max(xMax - xMin, yMax - yMin, zMax - zMin)
        scaleSize = 1 / maxSize
        xTr = -0.5 * (xMin + xMax)
        yTr = -0.5 * (yMin + yMax)
        zTr = -0.5 * (zMin + zMax)

        return {'transformCoord':map(str,(xTr,yTr,zTr)),
                'scale':str(scaleSize)}

    def runCalcProcs(self,transformCoord=None,scale=None):
        xformCmd = ['xform','-t']+transformCoord+['-s',scale,self.inputRad]
        octreeCmd = ['oconv',self.testRoom]

        # self.call_two(xformCmd,octreeCmd,
        #               'transform,scale and then combine the rad files with context',
        #               'create the octree',
        #               out=self.octree)

        xformFile = os.path.join(self.tempDir,'xform.rad')
        self.call_one(xformCmd,'transform,scale and then combine the rad files with context',
                      out=xformFile)

        self.call_one(octreeCmd+[xformFile],'create the octree',out=self.octree)

        xRes=yRes = '1024'
        rpictList = ['rpict','-av','0.2','0.2','0.2','-x',xRes,'-y',yRes]

        #using split because these strings were copied from the original csh script.
        view1 = '-vtl -vp 2 .5 .5 -vd -1 0 0 -vh 1 -vv 1'.split()
        view2 = '-vtl -vp .5 2 .5 -vd 0 -1 0 -vh 1 -vv 1'.split()
        view3 = '-vtl -vp .5 .5 2 -vd 0 0 -1 -vu -1 0 0 -vh 1 -vv 1'.split()
        view4 = '-vp 3 3 3 -vd -1 -1 -1 -vh 20 -vv 20'.split()

        # This will be used for naming files
        viewDict = {'right.hdr': view1, 'front.hdr': view2, 'down.hdr': view3,
                    'oblique.hdr': view4}
        #convert keys to fileNames
        # viewDict = {os.path.join(self.tempDir,key):value for key,value in viewDict.items()}

        fd = {}
        for fileKey,viewInfo in viewDict.items():
            fileName = os.path.join(self.tempDir,fileKey)
            rpictCmd = rpictList+viewInfo+[self.octree]
            self.call_one(rpictCmd,"create %s"%fileName,out=fileName)
            fd[fileKey]=fileName
        #Get the x,y,z dimensions of all the rad files (taken together.)

        pcomposCmd = ['pcompos',fd['down.hdr'],'0',xRes,fd['oblique.hdr'],xRes,yRes,
                      fd['right.hdr'],'0','0',fd['front.hdr'],xRes,'0']

        pfiltCmd = ['pfilt','-1','-r','0.6','-x','/2','-y','/2']

        self.call_two(pcomposCmd,pfiltCmd,'composite four views into one image',
                      'filter and resize the image')

def main():

    parser = argparse.ArgumentParser(add_help=False,
                                     description='Make a nice multi-view picture'
                                                 ' of an object')

    parser.add_argument('RadFiles', action='append', nargs='+',
                        help='File(s) containing radiance scene objects that'
                             ' are to be rendered.')
    parser.add_argument('-H', action='help', help='Help: print this text to '
                                                  'stderr and exit.')
    parser.add_argument('-N', action='store_true',
                        help='Do nothing (implies -V)')
    parser.add_argument('-V', action='store_true',
                        help='Verbose: print commands to execute to stderr')
    Objpict(parser.parse_args())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.stderr.write('*cancelled*\n')
        sys.exit(1)
    except (Error) as e:
        sys.stderr.write('%s: %s\n' % (SHORTPROGN, str(e)))
        sys.exit(-1)
