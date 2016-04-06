# coding=utf-8
# !/usr/bin/env python

"""
    objview - view RADIANCE object(s)

    This script is essentially a re-write of Axel Jacobs' objview.pl from
    http://radiance-online.org/cgi-bin/viewcvs.cgi/ray/src/util/objview.pl

    A few additional path related error checks have been added.
"""

from __future__ import division, print_function, unicode_literals
import os
import sys
import argparse
import tempfile

__all__ = ('main')
__revision__ = '$Revision: 1.0 $'


class Error(Exception): pass


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

commonOptions = ''

useGl = False
radOptions = False
glradOptions = False

lights = """
void glow dim 0 0 4 .1 .1 .15 0
dim source background 0 0 4 0 0 1 360
void light bright 0 0 3 1000 1000 1000
bright source sun1 0 0 4 1 .2 1 5
bright source sun2 0 0 4 .3 1 1 5
bright source sun3 0 0 4 -1 -.7 1 5"""


def printErrorAndExit(errorString):
    """Utility function for printing an error message and exiting"""
    print(errorString)
    print("Objview will now terminate.")
    sys.exit(-1)


class Objview(ProcMixin):
    def __init__(self, args):
        self.useGl = args.useGl
        self.upDirection = args.upDirection
        self.backFaceVisible = args.backFaceVisible
        self.viewDetials = args.viewDetails
        self.numProc = args.numProc
        self.outputDevice = args.outputDevice
        self.verboseDisplay = args.verboseDisplay
        self.radFiles = " ".join(args.Radfiles[0])

        # Perhaps this is not an elegant way of checking Null input. But it sees
        # to do the job for now..
        if self.radFiles.strip():
            fileNames = self.radFiles.split()
            for idx, fileName in enumerate(fileNames):
                if os.path.isfile(fileName) and os.path.exists(fileName):
                    fileNames[idx] = os.path.abspath(fileName)
                else:
                    printErrorAndExit("{} was either not found or is not a "
                                      "valid input for Radfiles"
                                      .format(fileName))
            self.radFiles = fileNames
        else:
            printErrorAndExit("No rad files were specified as input!")

        self.run()

    def run(self):

        outputDevice = 'x11'

        # Check if the OpenGL option was used in Windows.
        if self.useGl and sys.platform == 'win32':
            printErrorAndExit("The use of OpenGL is not supported in Windows")

        # Try creating a temp folder. Exit if not possible.
        try:
            tempDir = tempfile.mkdtemp('RAD')
        except IOError:
            printErrorAndExit("Objview could not create a temp folder.\n")

        # create strings for files that are to be written to.
        createInTemp = lambda fileName: os.path.join(tempDir, fileName)
        octreeFile = createInTemp('scene.oct')
        lightsFile = createInTemp('lights.rad')
        rifFile = createInTemp('scene.rif')
        ambFile = createInTemp('scene.amb')

        # Write lights and join to the input rad files.
        with open(lightsFile, 'w')as lightRad:
            lightRad.write(lights)
        self.radFiles.append(lightsFile)
        scene = " ".join(self.radFiles)

        # If the OS is Windows then make the path Rad friendly by switching
        # slashes and set the output device to qt.
        if sys.platform == 'win32':
            allFileNames = [scene, octreeFile, lightsFile, rifFile, ambFile]
            for idx, fileName in enumerate(allFileNames):
                allFileNames[idx] = fileName.replace('\\', '/')

            scene, octreeFile, lightsFile, rifFile, ambFile = allFileNames
            outputDevice = 'qt'

        # If the output device is specified by the user, use that.
        if self.outputDevice:
            outputDevice = self.outputDevice

        renderOptions = ''
        if self.backFaceVisible:
            renderOptions += '-bv '

        if self.numProc:
            renderOptions += '-n %s' % self.numProc

        # Create the string for rif file and write to disk.
        rifString = 'scene= %s\n' % scene
        rifString += 'EXPOSURE= 0.5\n'
        rifString += 'UP= %s\n' % (
            self.upDirection if self.upDirection else 'Z')
        rifString += 'view = %s\n' % (
            self.viewDetials if self.viewDetials else 'XYZ')
        rifString += 'OCTREE= %s\n' % octreeFile
        rifString += 'AMBF= %s\n' % ambFile
        rifString += 'render= %s' % renderOptions
        with open(rifFile, 'w') as rifData:
            rifData.write(rifString)

        # Based on user's choice select the output method.
        if self.useGl:
            cmdString = 'glrad  %s' % rifFile
        else:
            cmdString = 'rad -o %s  %s' % (outputDevice, rifFile)

        # Run !
        self.call_one(cmdString, 'Launch Objview')


def main():
    parser = argparse.ArgumentParser(add_help=False,
                                     description='Render a RADIANCE object ' \
                                                 'interactively')
    parser.add_argument('-g', action='store_true', dest='useGl',
                        help='Use OpenGL to render the scene')
    parser.add_argument('-u', action='store', dest='upDirection',
                        help='Up direction. The default '
                             'up direction vector is +Z',
                        type=str, metavar='upDirection')
    parser.add_argument('-bv', action='store_true', dest='backFaceVisible',
                        help='Enable back-face visibility in the scene.')
    parser.add_argument('-v', action='store', dest='viewDetails',
                        help='Specify view details.', type=str,
                        metavar='viewDetails')
    parser.add_argument('-N', action='store', dest='numProc',
                        help='Number of parallel processes to render the scene.',
                        type=int, metavar='numProc')
    parser.add_argument('-o', action='store', dest='outputDevice',
                        help='Specify an output device for rendering',
                        type=str, metavar='outputDevice')

    parser.add_argument('-V', '-e', action='store_false',
                        dest='verboseDisplay',
                        help='Display error messages in standard output')

    parser.add_argument('Radfiles', action='append', nargs='*',
                        help='File(s) containing radiance scene objects that are'
                             ' to be rendered interactively.')

    parser.add_argument('-H', action='help', help='Help: print this text to '
                                                  'stderr and exit.')

    if len(sys.argv) <= 1:
        sys.stdout.write(
            'No input was specified. Please see the usage instructions'
            ' below.' + '\n' * 2)
        sys.argv.append('-H')

    Objview(parser.parse_args())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.stderr.write('*cancelled*\n')
        sys.exit(1)
    except (Error) as e:
        sys.stderr.write('%s: %s\n' % (SHORTPROGN, str(e)))
        sys.exit(-1)
