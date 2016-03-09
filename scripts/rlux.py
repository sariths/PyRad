#!/usr/bin/env python
''' rlux.py - Compute illuminance from ray origin and direction

Drop-in replacement for the original csh script by Greg Ward.
2016 - Georg Mischler
'''
# Tant de bruit pour une omelette...
__all__ = ('main')
import os
import sys
import subprocess
import argparse

SHORTPROGN = os.path.splitext(os.path.split(sys.argv[0])[1])[0]
class Error(Exception): pass

class Rlux():
	def __init__(self, args):
		self.donothing = args.N
		self.verbose = args.V or self.donothing
		self.rtrargs = args.rtrargs
		self.octree = args.octree[0]
		self.run()

	def raise_on_error(self, actstr, e):
		raise Error('Unable to %s - %s' % (actstr, str(e)))

	def qjoin(self, sl):
		def _q(s):
			if ' ' in s or '\t' in s or ';' in s:
				return "'" + s + "'"
			return s
		return  ' '.join([_q(s) for s in sl])

	def run(self):
		rtr_cmd = 'rtrace -i+ -dv- -h- -x 1'.split() + self.rtrargs
		if self.octree:
			rtr_cmd.append(self.octree)
		rc_cmd = 'rcalc -e $1=47.4*$1+120*$2+11.6*$3 -u'.split()
		self.run_pipe(rtr_cmd, rc_cmd, 'trace rays', 'compte illuminance')

	def run_pipe(self, rtr_cmd, rc_cmd, rtr_actstr, rc_actstr):
		if self.verbose: sys.stderr.write(self.qjoin(rtr_cmd)+' | ')
		if not self.donothing:
			rtr_p = subprocess.Popen(rtr_cmd, stdout=subprocess.PIPE)
		if self.verbose:
			sys.stderr.write(self.qjoin(rc_cmd)+'\n')
		if not self.donothing:
			rc_p = subprocess.Popen(rc_cmd, stdin=rtr_p.stdout)
			rtr_p.stdout.close()
			res = rtr_p.wait()
			if res != 0:
				self.raise_on_error(rtr_actstr,
						'Nonzero exit (%d) from command [%s].'
						% (res, self.qjoin(rtr_cmd)))
			res = rc_p.wait()
			if res != 0:
				self.raise_on_error(rc_actstr,
						'Nonzero exit (%d) from command [%s].'
						% (res, self.qjoin(rc_cmd + ['>', '<tmpfile>'])))

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
        except Error as e:
                sys.stderr.write('%s: %s\n' % (SHORTPROGN, e))

