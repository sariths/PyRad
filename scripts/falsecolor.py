#!/usr/bin/env python
'''falsecolor.py - Make a false color Radiance picture

Drop-in replacement for the original Perl script by Greg Ward.
2002 - 2016 Georg Mischler
'''
__all__ = ['main']

import os
import sys
import math
import tempfile
import argparse
import subprocess

from pyradlib.proc_mixin import ProcMixin

SHORTPROGN = os.path.splitext(os.path.split(sys.argv[0])[1])[0]

defaults = {
	'name':     SHORTPROGN,
	'label':    'cd/m2',
	'pal':		'def',
	'redv':     '{pal}_red(v)',
	'grnv':     '{pal}_grn(v)',
	'bluv':     '{pal}_blu(v)',
	'picture':  '-',
	'cpict':    '',
	'docont':   None,
	'doposter': False,
	'doextrem': None,
	'needfile': False,
	'showpal':  False,
	'mult':       179,
	'scale':     1000,
	'decades':      0,
	'ndivs':        8,
	'loff':         0,
	'legwidth':   100,
	'legheight':  200,
	'donothing':False,
	'verbose':  False,
}

PC0_CAL = '''{ generated by falsecolor.py }
PI : 3.14159265358979323846;
scale : %(scale)s;
mult : %(mult)s;
ndivs : %(ndivs)s;
gamma : 2.2;

or(a,b) : if(a,a,b);
EPS : 1e-7;
neq(a,b) : if(a-b-EPS,1,b-a-EPS);
btwn(a,x,b) : if(a-x,-1,b-x);
clip(x) : if(x-1,1,if(x,x,0));
frac(x) : x - floor(x);
boundary(a,b) : neq(floor(ndivs*a+.5),floor(ndivs*b+.5));


spec_red(x) = 1.6*x - .6;
spec_grn(x) = if(x-.375, 1.6-1.6*x, 8/3*x);
spec_blu(x) = 1 - 8/3*x;

pm3d_red(x) = sqrt(x) ^ gamma;
pm3d_grn(x) = (x*x*x) ^ gamma;
pm3d_blu(x) = clip(sin(2*PI*clip(x))) ^ gamma;

hot_red(x) = clip(3*x) ^ gamma;
hot_grn(x) = clip(3*x - 1) ^ gamma;
hot_blu(x) = clip(3*x - 2) ^ gamma;

eco_red(x) = clip(2*x) ^ gamma;
eco_grn(x) = clip(2*(x-0.5)) ^ gamma;
eco_blu(x) = clip(2*(0.5-x)) ^ gamma;

interp_arr2(i,x,f):(i+1-x)*f(i)+(x-i)*f(i+1);
interp_arr(x,f):if(x-1,if(f(0)-x,interp_arr2(floor(x),x,f),f(f(0))),f(1));

def_redp(i):select(i,0.18848,0.05468174,
0.00103547,8.311144e-08,7.449763e-06,0.0004390987,0.001367254,
0.003076,0.01376382,0.06170773,0.1739422,0.2881156,0.3299725,
0.3552663,0.372552,0.3921184,0.4363976,0.6102754,0.7757267,
0.9087369,1,1,0.9863);
def_red(x):interp_arr(x/0.0454545+1,def_redp);

def_grnp(i):select(i,0.0009766,2.35501e-05,
0.0008966244,0.0264977,0.1256843,0.2865799,0.4247083,0.4739468,
0.4402732,0.3671876,0.2629843,0.1725325,0.1206819,0.07316644,
0.03761026,0.01612362,0.004773749,6.830967e-06,0.00803605,
0.1008085,0.3106831,0.6447838,0.9707);
def_grn(x):interp_arr(x/0.0454545+1,def_grnp);

def_blup(i):select(i,0.2666,0.3638662,0.4770437,
0.5131397,0.5363797,0.5193677,0.4085123,0.1702815,0.05314236,
0.05194055,0.08564082,0.09881395,0.08324373,0.06072902,
0.0391076,0.02315354,0.01284458,0.005184709,0.001691774,
2.432735e-05,1.212949e-05,0.006659406,0.02539);
def_blu(x):interp_arr(x/0.0454545+1,def_blup);

isconta = if(btwn(0,v,1),or(boundary(vleft,vright),boundary(vabove,vbelow)),-1);
iscontb = if(btwn(0,v,1),btwn(.4,frac(ndivs*v),.6),-1); 

ra = 0;
ga = 0;
ba = 0;

in = 1;

ro = if(in,clip(%(parsed_redv)s),ra);
go = if(in,clip(%(parsed_grnv)s),ga);
bo = if(in,clip(%(parsed_bluv)s),ba);
'''

PC1_CAL = '''{ generated by falsecolor.py }
norm : mult/scale/le(1);

v = map(li(1)*norm);

vleft = map(li(1,-1,0)*norm);
vright = map(li(1,1,0)*norm);
vabove = map(li(1,0,1)*norm);
vbelow = map(li(1,0,-1)*norm);

map(x) = x;

ra = ri(nfiles);
ga = gi(nfiles);
ba = bi(nfiles);
'''

PALETTES = ('def', 'spec', 'pm3d', 'hot', 'eco')

class Error(Exception): pass

class Falsecolor(ProcMixin):
	def __init__(self, **params):
		self.params = defaults.copy()
		self.params.update(params)
		self.donothing = params.get('donothing', False)
		self.verbose = params.get('verbose', False)
		self.tmpdir = None
		self.picfn = None
		self.configure_subprocess()
		self.make_tempfnames()
		self.autoscale()
		self.gen_pcargs()
		try: self.run()
		finally:
			if 1:
				if self.tmpdir and os.path.isdir(self.tmpdir):
					for fn in os.listdir(self.tmpdir):
						os.unlink(os.path.join(self.tmpdir, fn))
					os.rmdir(self.tmpdir)

	def raise_on_error(self, actstr, e):
		raise Error('Unable to %s - %s' % (actstr, str(e)))

	def run(self):
		self.create_calfiles()
		if self.params['showpal']:
			self.create_palettes()
			return
		extrema = False
		legend = True
		if self.params['legwidth'] <= 20 or self.params['legheight'] <= 40:
			self.params['legwidth'] = 0
			self.params['legheight'] = 0
			self.params['loff'] = 0
			legend = False
			if self.verbose:
				sys.stderr.write('### Legend label too small to show\n')
		else:
			self.create_scolpic()
			self.create_slabpics()
		if self.params['doextrem']:
			self.compute_extrema()
			extrema = True
		self.combine_pictures(extrema=extrema, legend=legend)

	def compute_extrema(self):
		pex_cmd = ['pextrem', '-o', self.params['picture']]
		if self.donothing: # bogus values for demonstration purposes
			mins = '758 475 8.045565e-02 6.217769e-02 6.119852e-02'
			maxs = '550 314 4.328220e+01 4.294798e+01 4.361643e+01'
		else:
			pex_proc = self.call_one(pex_cmd,  'compute extrema',
					out=subprocess.PIPE)
			mins = pex_proc.stdout.readline()
			maxs = pex_proc.stdout.readline()
			pex_proc.stdout.close()
		minl = mins.split()
		if len(minl) != 5:
			self.raise_on_error('determine extrema',
					'Invalid minimum data from pextrem')
		self.params['minposx'] = int(minl[0]) + self.params['legwidth']
		self.params['minposy'] = int(minl[1])
		minr, ming, minb = map(float, minl[2:])
		minval = (minr*0.27 + ming*0.67 + minb*0.06) * self.params['mult']
		maxl = maxs.split()
		if len(maxl) != 5:
			self.raise_on_error('determine extrema',
					'Invalid maximum data from pextrem')
		self.params['maxposx'] = int(maxl[0]) + self.params['legwidth']
		self.params['maxposy'] = int(maxl[1])
		maxr, maxg, maxb = map(float, maxl[2:])
		maxval = (maxr*0.27 + maxg*0.67 + maxb*0.06) * self.params['mult']
		cmd = ('psign -s -0.15 -a 2 -h 16 %.4g' % minval).split()
		self.call_one(cmd,'create minimum label',out=self.params['minvpic_fn'])
		cmd = ('psign -s -0.15 -a 2 -h 16 %.4g' % maxval).split()
		self.call_one(cmd,'create maximum label',out=self.params['maxvpic_fn'])

	def create_scolpic(self):
		fn = self.params['scolpic_fn']
		cmd = (['pcomb'] + self.params['pc0args']
				+ ['-e', 'v=(y+0.5)/yres;vleft=v;vright=v',
				'-e', 'vbelow=(y-0.5)/yres;vabove=(y+1.5)/yres',
				'-x', str(self.params['legwidth']),
				'-y', str(self.params['legheight']), ])
		self.call_one(cmd, 'create scale colors', out=fn)

	def create_slabpics(self):
		psign_ilines = [self.params['label']]
		decades = self.params['decades']
		ndivs = self.params['ndivs']
		scale = self.params['scale']
		for i in range(ndivs):
			y = (ndivs - 0.5 - i) / ndivs
			if decades:
				y2 = (10 ** ((y - 1) * decades))
			else: y2 = y
			psign_ilines.append('%.1f' % (scale * y2))
		height = math.floor(self.params['legheight']/self.params['ndivs']+0.5)
		psign_cmd = ('psign -s -0.15 -cf 1 1 1 -cb 0 0 0 -h %d'%height).split()

		psign_proc = self.call_one(psign_cmd, 'create scale labels',
				_in=subprocess.PIPE, out=self.params['slabpic_fn'])
		for line in psign_ilines:
			# Py3 text is unicode, convert to ASCII
			bline = (line + '\n').encode()
			psign_proc.stdin.write(bline)
		psign_proc.stdin.close()
		# now we can wait for it
		res = psign_proc.wait()
		if res != 0:
			self.raise_on_error(actstr,
					'Nonzero exit (%d) from command [%s].'
					% (res, self.qjoin(displ)))
		invert_cmd = ['pcomb', '-e', 'lo=1-gi(1)', self.params['slabpic_fn']]
		invert_proc = self.call_one(invert_cmd, 'create inverted label',
			out=self.params['slabinvpic_fn'])


	def make_tempfnames(self):
		if self.donothing:
			self.tmpdir = tempfile.mktemp()
		else:
			try: self.tmpdir = tempfile.mkdtemp()
			except Exception as e:
				self.raise_on_error('create temp directory', str(e))
		self.pc0fn = os.path.join(self.tmpdir, 'pc0.cal')
		self.pc1fn = os.path.join(self.tmpdir, 'pc1.cal')
		if self.params['needfile'] and self.params['picture'] == '-':
			self.picfn = os.path.join(self.tmpdir, 'stdin.hdr')
			self.params['picture'] = self.picfn
			if not self.donothing:
				with open(self.picfn, 'wb') as f:
					# Circumvent the unicode based stdin file object for Py3
					infd = sys.stdin.fileno()
					chunk = os.read(infd, 10000)
					while chunk:
						f.write(chunk)
						chunk = os.read(infd, 10000)
		self.params['scolpic_fn'] = os.path.join(self.tmpdir, 'scol.hdr')
		self.params['slabpic_fn'] = os.path.join(self.tmpdir, 'slab.hdr')
		self.params['slabinvpic_fn'] = os.path.join(self.tmpdir, 'slabinv.hdr')
		self.params['minvpic_fn'] = os.path.join(self.tmpdir, 'minv.hdr')
		self.params['maxvpic_fn'] = os.path.join(self.tmpdir, 'maxv.hdr')
		self.params['combpic_fn'] = os.path.join(self.tmpdir, 'comb.hdr')

	def combine_pictures(self, extrema, legend):
		pcB_cmd = (['pcomb'] + self.params['pc0args'] + self.params['pc1args']
				+ [self.params['picture']])
		if self.params.get('cpict'):
			pcB_cmd.append(self.params['cpict'])
		pcP_cmd = ['pcompos']
		if legend:
			leg_add = [
				self.params['scolpic_fn'], '0', '0',
				'+t', '0.1',
				self.params['slabinvpic_fn'], '2', str(self.params['loff']-1),
				'-t', '0.5',
				self.params['slabpic_fn'], '0', str(self.params['loff']),]
			pcP_cmd.extend(leg_add)
		pcP_cmd.extend(['-', str(self.params['legwidth']), '0',])
		if extrema:
			extr_add = [self.params['minvpic_fn'],
				str(self.params['minposx']), str(self.params['minposy']),
				self.params['maxvpic_fn'],
				str(self.params['maxposx']), str(self.params['maxposy']), ]
			pcP_cmd.extend(extr_add)
		self.call_two(pcB_cmd, pcP_cmd, 
				'combine final picture','compose final picture')

	def create_calfiles(self):
		if self.donothing: return
		try:
			f0 = open(self.pc0fn, 'w')
			f0.write(PC0_CAL % self.params)
			f0.close()
			f1 = open(self.pc1fn, 'w')
			f1.write(PC1_CAL)
			f1.close()
		except Exception as e:
			self.raise_on_error('create temporary cal files', str(e))

	def autoscale(self):
		scale = self.params.get('scale')
		if isinstance(scale, str) and scale.strip()[0] in 'aA':
			histo_cmd = ['phisto', self.params['picture']]
			hi_proc = self.call_one(histo_cmd, 'create scaling histogram',
					out=subprocess.PIPE)
			# apparently we want the second highest histogram value
			histo = hi_proc.stdout.readlines()[-2]
			hi_proc.stdout.close()
			logmax = float(histo.split()[0])
			self.params['scale'] = self.params['mult'] / 179 * 10** logmax

	def create_palettes(self):
		if self.params['showpal']:
			comb_cmdl = ['pcompos', '-a', '1']
			for pal in PALETTES:
				fcimg = os.path.join(self.tmpdir, '%s.hdr' % pal)
				lbimg = os.path.join(self.tmpdir, '%s_label.hdr' % pal)
				ps_cmd = ('psign -cb 0 0 0 -cf 1 1 1 -h 20 %s'% pal).split()
				self.call_one(ps_cmd, 'create sub-label', out=lbimg)

				pcb_cmd = ['pcomb', '-f', self.pc0fn, '-e', 'v=x/256', '-e',
						'ro=clip(%s_red(v));'
						'go=clip(%s_grn(v));'
						'bo=clip(%s_blu(v));' % (pal,pal,pal),
						'-x', '256', '-y', '30']
				self.call_one(pcb_cmd, 'create sub-image', out=fcimg)
				comb_cmdl.extend((fcimg, lbimg))
			self.call_one(comb_cmdl, 'compose palette image')

	def gen_pcargs(self):
		pc0argl = ['-f', self.pc0fn]
		pc1argl = ['-f', self.pc1fn]
		params = self.params
		for k,pk,vk in (('-r', 'parsed_redv', 'redv'),
			('-g', 'parsed_grnv', 'grnv'), ('-b', 'parsed_bluv', 'bluv'),):
			try: 
				params[pk] = params[vk].format(**params)
			except (KeyError, IndexError):
				raise Error('Invalid substitution in %s: "%s"'
						% (k, params[vk]))
		if params['docont']:
			pc0argl.extend(['-e', 'in=iscont%s' % params['docont']])
		elif params['doposter']:
			pc0argl.extend(['-e', 'ro={pal}_red(seg(v));'
					'go={pal}_grn(seg(v));'
					'bo={pal}_blu(seg(v));'.format( **params),
					'-e', 'seg(x)=(floor(v*ndivs)+.5)/ndivs'])
		if not params['cpict']:
			pc1argl.extend(['-e', 'ra=0;ga=0;ba=0'])
		elif params['cpict'] == params['picture']:
			params['cpict'] == ''
		decades = params['decades']
		if decades > 0:
			pc1argl.extend(['-e',
					'map(x)=kf(x-10^-%(decades)s,log10(x)/%(decades)s+1,0)'
					% {'decades':decades}])
		params['pc0args'] = pc0argl
		params['pc1args'] = pc1argl

def asciistr(s):
	for c in s:
		if not 31 < ord(c) < 127:
			raise argparse.ArgumentTypeError('value must be ASCII')
	return s

def main():
	''' This is a command line script and not currently usable as a module.
		Use the -H option for instructions.'''
	parser = argparse.ArgumentParser(add_help=False,
		description='Make a false color Radiance picture' )
	parser.add_argument('-i', action='store', nargs=1,
			metavar='picture', dest='picture',
			help='Input picture (default stdin)')
	parser.add_argument('-p', action='store', nargs=1,
			metavar='picture', dest='cpict',
			help='Use picture as background')
	parser.add_argument('-ip','-pi', action='store', nargs=1,
			metavar='pic', dest='__ipict__',
			help='Use picture as both input and background')

	contgr = parser.add_mutually_exclusive_group()
	contgr.add_argument('-cl', action='store_true', 
			dest='__cl__', help='Create contour lines')
	contgr.add_argument('-cb', action='store_true', 
			dest='__cb__', help='Create contour bands')
	contgr.add_argument('-cp', action='store_true', 
			dest='doposter', help='Posterize')

	parser.add_argument('-n', action='store', nargs=1,
			metavar='ndivs', dest='ndivs', type=int,
			help='Number of contours (default %d)' % defaults['ndivs'])
	parser.add_argument('-e', action='store_true', 
			dest='__doextrem__', help='Print extrema points to output picture')

	parser.add_argument('-l', action='store', nargs=1,
			metavar='label', dest='label', type=asciistr,
			help=('Text of legend label (ASCII, default "%s")'
				% defaults['label']))
	parser.add_argument('-lw', action='store', nargs=1,
			metavar='legwidth', dest='legwidth', type=int,
			help='Width of legend label (default %d px)' % defaults['legwidth'])
	parser.add_argument('-lh', action='store', nargs=1,
			metavar='legheight', dest='legheight', type=int,
		help='Height of legend label (default %d px)' % defaults['legheight'])

	parser.add_argument('-s', action='store', nargs=1,
			metavar='scale', dest='__scale__', type=float,
		help='Linear luminance scale (default %d)' % defaults['scale'])
	parser.add_argument('-log', action='store', nargs=1,
			metavar='decades', dest='decades', type=int,
		help='Use log mapping over decades (default linear)')
	parser.add_argument('-m', action='store', nargs=1,
			metavar='mult', dest='mult', type=int,
		help='Multiplier from Radiance (default %d)' % defaults['mult'])

	parser.add_argument('-r', action='store', nargs=1,
			metavar='redv', dest='redv', type=str,
			help='Mapping to red component (experts only)')
	parser.add_argument('-g', action='store', nargs=1,
			metavar='grnv', dest='grnv', type=str,
			help='Mapping to green component (experts only)')
	parser.add_argument('-b', action='store', nargs=1,
			metavar='bluv', dest='bluv', type=str,
			help='Mapping to blue component (experts only)')
	parser.add_argument('-pal', action='store', nargs=1,
			metavar='pal', dest='pal', type=str, choices=PALETTES,
			help='Color palette to use (default "%s")' % defaults['pal'])
	parser.add_argument('-palettes', action='store_true', dest='__palettes__',
			help='Combine swatches of all built-in palettes in one'
			' picture (ignores all other options)')

	parser.add_argument('-N', action='store_true', dest='donothing',
		help='Do nothing (implies -V)')
	parser.add_argument('-V', action='store_true', dest='verbose',
		help='Verbose: print commands to execute to stderr')
	parser.add_argument('-H', action='help',
		help='Help: print this text to stderr and exit')
	args = parser.parse_args()

	params = defaults.copy()
	for key,v in vars(args).items():
		if v is None:
			continue
		if key.startswith('__'):
			if v: # post processing for multi-value items
				if key == '__doextrem__':
					params['doextrem'] = True
					params['needfile'] = True
				if key == '__cl__':
					params['docont'] = 'a'
					params['loff'] = 0.48
				elif key == '__cb__':
					params['docont'] = 'b'
					params['loff'] = 0.52
				elif key == '__palettes__':
					params['scale'] = 45824
					params['showpal'] = True
				elif key == '__ipict__':
					params['picture'] = v[0]
					params['cpict'] = v[0]
				elif key == '__scale__':
					params['scale'] = v[0]
					params['needfile'] = True
		elif isinstance(v, (list, tuple)):
			params[key] = v[0]
		else:
			params[key] = v

	#sys.stderr.write('%s\n'%args)
	#sys.stderr.write('%s\n\n'%params)
	fc = Falsecolor(**params)

if __name__ == '__main__':
	try: main()
	except KeyboardInterrupt:
		sys.stderr.write('*cancelled*\n')
		exit(1)
	except (Error) as e:
		#with open('falsecolor.error', 'a') as ef:
		#	ef.write('%s: %s\n' % (SHORTPROGN, str(e)))
		sys.stderr.write('%s: %s\n' % (SHORTPROGN, str(e)))
		exit(-1)

