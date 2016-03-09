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

SHORTPROGN = os.path.splitext(os.path.split(sys.argv[0])[1])[0]
class Error(Exception): pass

class Phisto():
	def __init__(self, args):
		self.donothing = args.N
		self.verbose = args.V or self.donothing
		self.imgfiles = args.picture[0]
		if not self.donothing:
			self.tmpfile = tempfile.TemporaryFile()
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
		pv_cmd = ['pvalue', '-o', '-h', '-H', '-df', '-b']
		if not self.imgfiles:
			pf_cmd = ['pfilt', '-1', '-x', '128', '-y', '128', '-p', '1']
			self.pipe_to_tmp(pf_cmd, pv_cmd,
					'extract image values', 'filter image values')
		else:
			for fname in self.imgfiles: # check first
				if not os.path.isfile(fname):
					raise_on_error('open file "%s"' % fname, 'File not found.')
			for fname in self.imgfiles:
				pf_cmd = ['pfilt', '-1', '-x', '128', '-y', '128',
					'-p', '1', fname]
				self.pipe_to_tmp(pf_cmd, pv_cmd,
						'extract image values', 'filter image values')
		self.run_calcprocs()

	def pipe_to_tmp(self, pf_cmd, pv_cmd, pf_actstr, pv_actstr):
		fn = self.tmpfile
		if self.verbose: sys.stderr.write(self.qjoin(pf_cmd)+' | ')
		if not self.donothing:
			pf_p = subprocess.Popen(pf_cmd, stdout=subprocess.PIPE)
		if self.verbose:
			sys.stderr.write(self.qjoin(pv_cmd + ['>', '<tmpfile>'])+'\n')
		if not self.donothing:
			pv_p = subprocess.Popen(pv_cmd,
					stdin=pf_p.stdout, stdout=self.tmpfile)
			pf_p.stdout.close()
			res = pf_p.wait()
			if res != 0:
				self.raise_on_error(pf_actstr,
						'Nonzero exit (%d) from command [%s].'
						% (res, self.qjoin(pf_cmd)))
			res = pv_p.wait()
			if res != 0:
				self.raise_on_error(pv_actstr,
						'Nonzero exit (%d) from command [%s].'
						% (res, self.qjoin(pv_cmd + ['>', '<tmpfile>'])))

	def pipe_from_tmp(self, cmd_1, cmd_2, actstr_1, actstr_2):
		if self.verbose: sys.stderr.write(self.qjoin(cmd_1)+' | ')
		if not self.donothing:
			self.tmpfile.seek(0)
			p1 = subprocess.Popen(cmd_1,
					stdin=self.tmpfile, stdout=subprocess.PIPE)
		if self.verbose: sys.stderr.write(self.qjoin(cmd_2)+'\n')
		if not self.donothing:
			p2 = subprocess.Popen(cmd_2, stdin=p1.stdout,stdout=subprocess.PIPE)
			p1.stdout.close()
			res = p1.wait()
			if res != 0:
				self.raise_on_error(actstr_1,
						'Nonzero exit (%d) from command [%s].'
						% (res, self.qjoin(cmd_1)))
			res = p2.wait()
			if res != 0:
				self.raise_on_error(actstr_2,
						'Nonzero exit (%d) from command [%s].'
						% (res, self.qjoin(cmd_2 + ['>', fn])))
			return p2.stdout.read().strip()

	def run_calcprocs(self):
		lmin_t_cmd = ['total', '-if', '-l']
		lmin_rc_cmd = ['rcalc', '-e', 'L=$1*179;$1=if(L-1e-7,log10(L)-.01,-7)']
		lmin = self.pipe_from_tmp(lmin_t_cmd, lmin_rc_cmd,
			'extract lower limit', 'compute minimum')
		lmax_t_cmd = ['total', '-if', '-u']
		lmax_rc_cmd = ['rcalc', '-e', '$1=log10($1*179)+.01']
		lmax = self.pipe_from_tmp(lmax_t_cmd, lmax_rc_cmd,
			'extract upper limit', 'compute maximum')
		if lmin is None: # dry run, display dummy values
			lmin = '<Lmin>'
			lmax = '<Lmax>'
		else: # Py3 wants unicode for verbose display
			lmin = lmin.decode()
			lmax = lmax.decode()
		rc_cmd = ['rcalc', '-if', '-e', 'L=$1*179;cond=L-1e-7;$1=log10(L)']
		hi_cmd = ['histo', lmin, lmax, '777']
		res = self.pipe_from_tmp(rc_cmd, hi_cmd,
			'extract records', 'compute histogram')
		if not self.donothing:
			# The Py3 stdout file object doesn't accept bytes.
			# The low-level shortcut circumvents any further processing.
			os.write(1, res)
			os.write(1, b'\n')

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

