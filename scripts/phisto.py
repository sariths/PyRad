#!/usr/bin/env python
''' phisto.py - Compute foveal histogram for picture set

Drop-in replacement for the original csh script by Greg Ward.
2016 - Georg Mischler
'''
__all__ = ('main')
import sys
import os
import tempfile
import subprocess
import argparse

from pyradlib.pyrad_proc import Error, ProcMixin

SHORTPROGN = os.path.splitext(os.path.split(sys.argv[0])[1])[0]

class Phisto(ProcMixin):
	def __init__(self, args):
		self.donothing = args.N
		self.verbose = args.V or self.donothing
		self.imgfiles = args.picture[0]
		if not self.donothing:
			self.tmpfile = tempfile.TemporaryFile()
		self.run()

	def run(self):
		pf_cmd = ['pfilt', '-1', '-x', '128', '-y', '128', '-p', '1']
		pv_cmd = ['pvalue', '-o', '-h', '-H', '-df', '-b']
		if not self.imgfiles:
			self.call_two(pf_cmd, pv_cmd,
					'extract image values', 'filter image values',
					out=self.tmpfile)
		else:
			for fname in self.imgfiles: # check first
				if not os.path.isfile(fname):
					self.raise_on_error('open file "%s"' % fname,
							'File not found.')
			for fname in self.imgfiles:
				p = self.call_two(pf_cmd + [fname], pv_cmd,
						'extract image values', 'filter image values',
						out=self.tmpfile)
		self.run_calcprocs()

	def run_calcprocs(self):
		lmin_t_cmd = ['total', '-if', '-l']
		lmin_rc_cmd = ['rcalc', '-e', 'L=$1*179;$1=if(L-1e-7,log10(L)-.01,-7)']
		if not self.donothing: self.tmpfile.seek(0)
		lmin_proc = self.call_two(lmin_t_cmd, lmin_rc_cmd,
			'extract lower limit', 'compute minimum',
			_in=self.tmpfile, out=subprocess.PIPE)
		lmax_t_cmd = ['total', '-if', '-u']
		lmax_rc_cmd = ['rcalc', '-e', '$1=log10($1*179)+.01']
		if not self.donothing: self.tmpfile.seek(0)
		lmax_proc = self.call_two(lmax_t_cmd, lmax_rc_cmd,
			'extract upper limit', 'compute maximum',
			_in=self.tmpfile, out=subprocess.PIPE)
		if self.donothing: # dry run, display dummy values
			lmin = '<Lmin>'
			lmax = '<Lmax>'
		else: # Py3 wants unicode for verbose display
			lmin = lmin_proc[1].stdout.read().strip()
			lmax = lmax_proc[1].stdout.read().strip()
			lmin = lmin.decode()
			lmax = lmax.decode()
		rc_cmd = ['rcalc', '-if', '-e', 'L=$1*179;cond=L-1e-7;$1=log10(L)']
		hi_cmd = ['histo', lmin, lmax, '777']
		if not self.donothing: self.tmpfile.seek(0)
		res_proc = self.call_two(rc_cmd, hi_cmd,
			'extract records', 'compute histogram',
			_in=self.tmpfile)

def main():
	''' This is a command line script and not currently usable as a module.
	Use the -H option for instructions.'''
	parser = argparse.ArgumentParser(add_help=False,
		description='Compute foveal histogram for picture set')
	parser.add_argument('-N', action='store_true',
		help='Do nothing (implies -V)')
	parser.add_argument('-V', action='store_true',
		help='Verbose: print commands to execute to stderr')
	parser.add_argument('-H', action='help',
		help='Help: print this text to stderr and exit')
	parser.add_argument('picture', action='append', nargs='*',
		help='HDR image files to analyze (else stdin)')
	Phisto(parser.parse_args())

if __name__ == '__main__':
        try: main()
        except KeyboardInterrupt:
                sys.stderr.write('*cancelled*\n')
        except Error as e:
                sys.stderr.write('%s: %s\n' % (SHORTPROGN, e))

