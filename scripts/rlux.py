#!/usr/bin/env python
''' rlux.py - Compute illuminance from ray origin and direction

Drop-in replacement for the original csh script by Greg Ward.
2016 - Georg Mischler
'''
# Tant de bruit pour une omelette...
__all__ = ('main')
import os
import sys
import argparse

if __name__ == '__main__' and not getattr(sys, 'frozen', False):
	_rp = os.environ.get('RAYPATH')
	if not _rp:
		print('No RAYPATH, unable to find support library'); sys.exit(-1)
	for _p in _rp.split(os.path.pathsep):
		if os.path.isdir(os.path.join(_p, 'pyradlib')):
			if _p not in sys.path: sys.path.insert(0, _p)
			break
	else:
		print('Support library not found on RAYPATH'); sys.exit(-1)

from pyradlib.pyrad_proc import Error, ProcMixin

SHORTPROGN = os.path.splitext(os.path.basename(sys.argv[0]))[0]

class Rlux(ProcMixin):
	def __init__(self, args):
		self.donothing = args.N
		self.verbose = args.V or self.donothing
		self.rtrargs = args.rtrargs
		self.octree = args.octree[0]
		self.run()

	def run(self):
		rtr_cmd = 'rtrace -i+ -dv- -h- -x 1'.split() + self.rtrargs
		if self.octree:
			rtr_cmd.append(self.octree)
		rc_cmd = 'rcalc -e $1=47.4*$1+120*$2+11.6*$3 -u'.split()
		self.call_two(rtr_cmd, rc_cmd, 'trace rays', 'compte illuminance')

def main():
	''' This is a command line script and not currently usable as a module.
	Use the -H option for instructions.'''
	parser = argparse.ArgumentParser(add_help=False,
		description='Compute illuminance from ray origin and direction',
		epilog='Accepts "px py pz  dx dy dz" vectors on stdin, '
		'produces illuminance values on stdout.')
	parser.add_argument('-N', action='store_true',
		help='Do nothing (implies -V)')
	parser.add_argument('-V', action='store_true',
		help='Verbose: print commands to execute to stderr')
	parser.add_argument('-H', action='help',
		help='Help: print this text to stderr and exit')
	parser.add_argument('rtrargs', action='append', nargs='*',
		metavar='rtrarg', help='Rtrace arguments')
	parser.add_argument('octree', action='append', nargs='?',
		metavar='octree', help='Octree file to process (else stdin)')
	args = parser.parse_known_args() 
	opts = args[0]
	rtrargs = args[1]
	if len(opts.rtrargs[0]) == 1 and opts.octree[0] is None:
		# will exhaust 'octree' before 'rtrarg'
		opts.octree[0] = opts.rtrargs[0][0]
		del opts.rtrargs[0][0]
	if opts.octree[0] and not os.path.isfile(opts.octree[0]):
		parser.error('No such file (%s)' % opts.octree[0])
	if opts.rtrargs[0] and opts:
		parser.error('Unknown rtrace arguments (%s)'%' '.join(opts.rtrargs[0]))
	opts.rtrargs = rtrargs
	Rlux(opts)

if __name__ == '__main__':
	try: main()
	except KeyboardInterrupt:
		sys.stderr.write('*cancelled*\n')
		sys.exit(1)
	except Error as e:
		sys.stderr.write('%s: %s\n' % (SHORTPROGN, e))
		sys.exit(-1)

