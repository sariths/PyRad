# coding=utf-8
import sys
import importlib
import os
import time

def runPyRadCmd(scriptName,commandVal,scriptDir='scripts'):
    sys.path.append(scriptDir)
    importlib.import_module(scriptName) #Raise and crash if not in place.

    scriptDirAbs = os.path.abspath(scriptDir)
    scriptNameAbs = os.path.join(scriptDirAbs,scriptName+'.py')

    print("{} started at {}\n".format(scriptName,time.ctime()))

    os.system("python {} {}".format(scriptNameAbs,commandVal))

    print("\n{} terminated at {}".format(scriptName,time.ctime()))

radCmd = 'falsecolor'
inputs = r'-i C:\Users\Sarith\Desktop\blueYellow.HDR > C:\Users\Sarith\Desktop\test.hdr'
# inputs = '-H'
runPyRadCmd(radCmd,inputs)


# phisto()
