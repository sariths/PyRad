#!/usr/bin/env python
''' glaze.py - Complex glazing model (goes with glaze1.cal and glaze2.cal) 

Drop-in replacement for the original csh script by Greg Ward.
2016 - Georg Mischler

Funding for the original development generously provided by Visarc, Inc.
(http://www.visarc.com)

The general assumption is that one surface per pane is uncoated, and
reflectances and transmittances are computed from this fact.
'''
from __future__ import division, print_function, unicode_literals
__all__ = ('main')
__revision__ ='$Revision: 1.0 $'
import os
import sys
import argparse

try: # Py3
	import tkinter
	from tkinter import ttk
	from tkinter import filedialog
	from tkinter import messagebox
except ImportError: # Py2.7
	import Tkinter as tkinter
	import ttk
	import tkFileDialog as filedialog
	import tkMessageBox as messagebox

class Error(Exception): pass
SHORTPROGN = os.path.splitext(os.path.basename(sys.argv[0]))[0]

FRIT_FMT = '''
void BRTDfunc glaze1_unnamed
10
  sr_frit_r sr_frit_g sr_frit_b
  st_frit_r st_frit_g st_frit_b
  0 0 0
  glaze1.cal
0
11
  {} {} {}
  {} {} {}
  {} {} {}
  {} {}
'''

LOWE_FMT = '''
void BRTDfunc glaze1_unnamed
10
  sr_clear_r sr_clear_g sr_clear_b
  st_clear_r st_clear_g st_clear_b
  0 0 0
  glaze1.cal
0
19
  0 0 0
  0 0 0
  0 0 0
  {}
  {} {} {}
  {} {} {}
  {} {} {}
'''

FPF_FMT = '''
void BRTDfunc glaze2_unnamed
10
  if(Rdot,cr({s4g}*rclr,{s3g}*{s4g}*tclr,fr({s2r_rgb[0]})),cr(fr({s1r_rgb[0]}),ft({s12t_rgb[0]}),{s3g}*rclr))
  if(Rdot,cr({s4g}*rclr,{s3g}*{s4g}*tclr,fr({s2r_rgb[1]})),cr(fr({s1r_rgb[1]}),ft({s12t_rgb[1]}),{s3g}*rclr))
  if(Rdot,cr({s4g}*rclr,{s3g}*{s4g}*tclr,fr({s2r_rgb[2]})),cr(fr({s1r_rgb[2]}),ft({s12t_rgb[2]}),{s3g}*rclr))
  {s3g}*{s4g}*ft({s12t_rgb[0]})*tclr
  {s3g}*{s4g}*ft({s12t_rgb[1]})*tclr
  {s3g}*{s4g}*ft({s12t_rgb[2]})*tclr
  0 0 0
  glaze2.cal
0
9
  {} {} {}
  {} {} {}
  {} {} {}
'''

BPF_FMT = '''
void BRTDfunc glaze2_unnamed
10
  if(Rdot,cr(fr({s4r_rgb[0]}),ft({s34t_rgb[0]}),{s2g}*rclr),cr({s1g}*rclr,{s1g}*{s2g}*tclr,fr({s3r_rgb[0]})))
  if(Rdot,cr(fr({s4r_rgb[1]}),ft({s34t_rgb[1]}),{s2g}*rclr),cr({s1g}*rclr,{s1g}*{s2g}*tclr,fr({s3r_rgb[1]})))
  if(Rdot,cr(fr({s4r_rgb[2]}),ft({s34t_rgb[2]}),{s2g}*rclr),cr({s1g}*rclr,{s1g}*{s2g}*tclr,fr({s3r_rgb[2]})))
  {s1g}*{s2g}*ft({s34t_rgb[0]})*tclr"
  {s1g}*{s2g}*ft({s34t_rgb[1]})*tclr"
  {s1g}*{s2g}*ft({s34t_rgb[2]})*tclr"
  0 0 0
  glaze2.cal
0
9
  {} {} {}
  {} {} {}
  {} {} {}
'''

LOWE2_FMT = '''
void BRTDfunc glaze2_unnamed
10
  if(Rdot,cr(fr({s4r_rgb[0]}),ft({s34t_rgb[0]}),fr({s2r_rgb[0]})),cr(fr({s1r_rgb[0]}),ft({s12t_rgb[0]}),fr({s3r_rgb[0]})))
  if(Rdot,cr(fr({s4r_rgb[1]}),ft({s34t_rgb[1]}),fr({s2r_rgb[1]})),cr(fr({s1r_rgb[1]}),ft({s12t_rgb[1]}),fr({s3r_rgb[1]})))
  if(Rdot,cr(fr({s4r_rgb[2]}),ft({s34t_rgb[2]}),fr({s2r_rgb[2]})),cr(fr({s1r_rgb[2]}),ft({s12t_rgb[2]}),fr({s3r_rgb[2]})))
  ft({s34t_rgb[0]})*ft({s12t_rgb[0]})
  ft({s34t_rgb[1]})*ft({s12t_rgb[1]})
  ft({s34t_rgb[2]})*ft({s12t_rgb[2]})
  0 0 0
  glaze2.cal
0
9
  0 0 0
  0 0 0
  0 0 0
'''

class Glazing(object):
	'''The data for one specific glass coating, as stored in the database.
	Will compute the result in concert with one or several others.'''
	def __init__(self, name,
			rg_r,rg_g,rg_b, rc_r,rc_g,rc_b, tn_r,tn_g,tn_b, partial):
		self.name = name
		self.rg_r = rg_r; self.rg_g = rg_g; self.rg_b = rg_b
		self.rc_r = rc_r; self.rc_g = rc_g; self.rc_b = rc_b
		self.tn_r = tn_r; self.tn_g = tn_g; self.tn_b = tn_b
		self.partial = partial


	def _hemiref(self, r, g, b, sc, cr, cg, cb):
		rv = 0.265 * (sc * r + (1-sc) * cr) 
		gv = 0.670 * (sc * g + (1-sc) * cg)
		bv = 0.065 * (sc * b + (1-sc) * cb)
		return rv + gv + bv

	def make_1_mat(self, cvg, other, o_cvg):
		'''Compute single glazing ("other" is the inner surface)'''
		res = [ '# Number of panes in system: 1',
				'# Exterior surface s1 type: %s' % self.name]
		sc = 1
		if self.partial:
			res.append('# s1 coating coverage: %g' % cvg)
			sc = cvg
		res.append('# Interior surface s2 type: %s' % other.name)
		if other.partial:
			res.append('# s2 coating coverage: %g' % o_cvg)
			sc = o_cvg
		if self is _clear:
			oi = other
			e_nhr = self._hemiref(oi.rg_r, oi.rg_g, oi.rg_b, sc,
					_clear.rg_r, _clear.rg_b, _clear.rg_b)
			i_nhr = self._hemiref(oi.rc_r, oi.rc_g, oi.rc_b, sc,
					_clear.rc_r, _clear.rc_b, _clear.rc_b)
		else:
			oi = self
			e_nhr = self._hemiref(oi.rc_r, oi.rc_g, oi.rc_b, sc,
					_clear.rc_r, _clear.rc_b, _clear.rc_b)
			i_nhr = self._hemiref(oi.rg_r, oi.rg_g, oi.rg_b, sc,
					_clear.rg_r, _clear.rg_b, _clear.rg_b)
		n_htmt =  self._hemiref(oi.tn_r, oi.tn_g, oi.tn_b, sc,
				_clear.tn_r, _clear.tn_b, _clear.tn_b)
		res.append('# Exterior normal hemispherical reflectance: %g' % e_nhr)
		res.append('# Interior normal hemispherical reflectance: %g' % i_nhr)
		res.append('# Normal hemispherical transmittance: %g' % n_htmt)
		if self.partial or other.partial: # frit glazing
			if other is _clear:
				fargs = ( cvg*(self.rg_r-_clear.rg_r),
						cvg*(self.rg_b-_clear.rg_b),
						cvg*(self.rg_g-_clear.rg_g),
						cvg*self.rc_r, cvg*self.rc_g, cvg*self.rc_b,
						cvg*self.tn_r, cvg*self.tn_g, cvg*self.tn_b,
						1, cvg )
			else:
				fargs = ( o_cvg*(other.rg_r-_clear.rg_r),
						o_cvg*(other.rg_b-_clear.rg_b),
						o_cvg*(other.rg_g-_clear.rg_g),
						o_cvg*other.rc_r, o_cvg*other.rc_g, o_cvg*other.rc_b,
						o_cvg*other.tn_r, o_cvg*other.tn_g, o_cvg*other.tn_b,
						-1, o_cvg )
			res.append(FRIT_FMT.format(*fargs))
		else: # low-e glazing
			if other is _clear:
				fargs = [1]
				oi = self
			else:
				fargs = [-1]
				oi = other
			fargs.extend([oi.rg_r, oi.rg_g, oi.rg_b,
						oi.rc_r, oi.rc_g, oi.rc_b,
						oi.tn_r, oi.tn_g, oi.tn_b,])
			res.append(LOWE_FMT.format(*fargs))
		return res

	def _w2cs(self, r,g,b):
		return 0.265 * r + 0.670 * g + 0.065 * b

	def make_2_mat(self, s1c, o2, s2c, o3, s3c, o4, s4c):
		'''Compute double glazing'''
		res = ['# Number of panes in system: 2']
		if o2 is _clear:
			s2r_rgb  = self.rg_r, self.rg_g, self.rg_b
			s1r_rgb  = self.rc_r, self.rc_g, self.rc_b
			s12t_rgb = self.tn_r, self.tn_g, self.tn_b
		else:
			s2r_rgb  = o2.rc_r, o2.rc_g, o2.rc_b
			s1r_rgb  = o2.rg_r, o2.rg_g, o2.rg_b
			s12t_rgb = o2.tn_r, o2.tn_g, o2.tn_b
		if o4 is _clear:
			s4r_rgb  = o3.rg_r, o3.rg_g, o3.rg_b
			s3r_rgb  = o3.rc_r, o3.rc_g, o3.rc_b
			s34t_rgb = o3.tn_r, o3.tn_g, o3.tn_b
		else:
			s4r_rgb  = o4.rc_r, o4.rc_g, o4.rc_b
			s3r_rgb  = o4.rg_r, o4.rg_g, o4.rg_b
			s34t_rgb = o4.tn_r, o4.tn_g, o4.tn_b
		s12c = 1
		res.append('# Exterior surface s1 type: %s' % self.name)
		if self.partial:
			res.append('# s1 coating coverage: %g' % s1c)
			s12c = s1c
		res.append('# Inner surface s2 type: %s' % o2.name)
		if o2.partial:
			res.append('# s2 coating coverage: %g' % s2c)
			s12c = s2c
		s34c = 1
		res.append('# Inner surface s3 type: %s' % o3.name)
		if o3.partial:
			res.append('# s3 coating coverage: %g' % s3c)
			s34c = s3c
		res.append('# Interior surface s4 type: %s' % o4.name)
		if o4.partial:
			res.append('# s1 coating coverage: %g' % s4c)
			s34c = s4c
		# Approximate reflectance and transmittance for comment using gray value
		rglass = self._w2cs(_clear.rg_r, _clear.rg_g, _clear.rg_b)
		tglass = self._w2cs(_clear.tn_r, _clear.tn_g, _clear.tn_b)
		s1r_gry = s12c * self._w2cs(*s1r_rgb) + (1 - s12c) * rglass
		s2r_gry = s12c * self._w2cs(*s2r_rgb) + (1 - s12c) * rglass
		s12t_gry = s12c * self._w2cs(*s12t_rgb) + (1 - s12c) * tglass
		s3r_gry = s34c * self._w2cs(*s3r_rgb) + (1 - s34c) * rglass
		s4r_gry = s34c * self._w2cs(*s4r_rgb) + (1 - s34c) * rglass
		s34t_gry = s34c * self._w2cs(*s34t_rgb) + (1 - s34c) * tglass
		res.append('# Exterior normal hemispherical reflectance: %g'
				% (s1r_gry + s12t_gry**2 * s3r_gry))
		res.append('# Interior normal hemispherical reflectance: %g'
				% (s4r_gry + s34t_gry**2 * s2r_gry))
		res.append('# Normal hemispherical transmittance: %g'
				% (s12t_gry * s34t_gry))
		if o3.partial or o4.partial: # front pane has frit
			if o3.partial:
				sc = s3c
				s3g = 1 - s3c
			else:
				s3c = 0
				s3g = 1
			if o4.partial:
				sc = s4c
				s4g = 1 - s4c
			else:
				s4c = 0
				s4g = 1
			fargs = [sc*s4r_rgb[0]-s3c*_clear.rg_r,
					sc*s4r_rgb[1]-s3c*_clear.rg_g,
					sc*s4r_rgb[2]-s3c*_clear.rg_b,
					s12t_rgb[0]**2*(sc*s3r_rgb[0]-s4c*_clear.rg_r),
					s12t_rgb[1]**2*(sc*s3r_rgb[1]-s4c*_clear.rg_g),
					s12t_rgb[2]**2*(sc*s3r_rgb[2]-s4c*_clear.rg_b),
					sc*s12t_rgb[0]*s34t_rgb[0],
					sc*s12t_rgb[1]*s34t_rgb[1],
					sc*s12t_rgb[2]*s34t_rgb[2], ]
			res.append(FPF_FMT.format(*fargs, s4g=s4g, s3g=s3g,
					s1r_rgb=s1r_rgb, s2r_rgb=s2r_rgb, s12t_rgb=s12t_rgb))
			return res
		elif self.partial or o2.partial: # back pane has frit
			if self.partial:
				sc = s1c
				s1g = 1 - s1c
			else:
				s1c = 0
				s1g = 1
			if o2.partial:
				sc = s2c
				s2g = 1 - s2c
			else:
				s2c = 0
				s2g = 1
			fargs = [ s34t_rgb[0]**2*(sc*s2r_rgb[0]-s1c*_clear.rg_r),
					s34t_rgb[1]**2*(sc*s2r_rgb[1]-s1c*_clear.rg_g),
					s34t_rgb[2]**2*(sc*s2r_rgb[2]-s1c*_clear.rg_b),
					sc*s1r_rgb[0]-s2c*_clear.rg_r,
					sc*s1r_rgb[1]-s2c*_clear.rg_g,
					sc*s1r_rgb[2]-s2c*_clear.rg_b,
					sc*s34t_rgb[0]*s12t_rgb[0],
					sc*s34t_rgb[1]*s12t_rgb[1],
					sc*s34t_rgb[2]*s12t_rgb[2], ]
			res.append(BPF_FMT.format(*fargs, s1g=s1g, s2g=s2g,
					s3r_rgb=s3r_rgb, s4r_rgb=s4r_rgb, s34t_rgb=s34t_rgb))
			return res
		else: # Low-E and regular glazing only
			res.append(LOWE2_FMT.format(s1r_rgb=s1r_rgb, s2r_rgb=s2r_rgb, s12t_rgb=s12t_rgb,
					s3r_rgb=s3r_rgb, s4r_rgb=s4r_rgb, s34t_rgb=s34t_rgb))
			return res


# Default demo database.
# The first one is a special name, referenced pretty much everywhere.
_clear = Glazing('clear glass', 0.074,0.077,0.079, 0.074,0.077,0.079,
	0.862,0.890,0.886, False)
__lowe = Glazing('VE1-2M low-E coating', 0.065,0.058,0.067, 0.042,0.049,0.043,
	0.756,0.808,0.744, False)
__pvb = Glazing('PVB laminated', 0.11,0.11,0.11, 0.11,0.11,0.11,
	0.63,0.63,0.63, False)
__v175 = Glazing('V-175 white frit', 0.33,0.33,0.33, 0.59,0.59,0.59,
	0.21,0.21,0.21, True)
__v933 = Glazing('V-933 warm gray frit', 0.15,0.15,0.15, 0.21,0.21,0.21,
	0.09,0.09,0.09, True)
__default = [_clear, __lowe, __pvb, __v175, __v933]


class GlazeText(tkinter.Text, object):
	'''Scrolled text widgte for showing the result.'''
	def __init__(self, parent, *args, **kwargs):
		self._frame = ttk.Frame(parent)
		sup = super(GlazeText, self)
		sup.__init__(self._frame, *args, **kwargs)
		sup.grid(column=1, row=1, sticky='wens', padx=0)
		self._frame.grid_columnconfigure(1, weight=1)
		self._frame.grid_rowconfigure(1, weight=1)
		self.__vertbar = ttk.Scrollbar(self._frame, orient='vertical',
				command=self.yview,)
		self.__vertbar['takefocus'] = 0
		self.__vertbar.grid(column=2, row=1, sticky='wens')
		self.configure(yscrollcommand=self.__vertbar.set)
		self.__horbar = ttk.Scrollbar(self._frame, orient='horizontal',
				command=self.xview,)
		self.__horbar['takefocus'] = 0
		self.__horbar.grid(column=1, row=2, sticky='wens')
		self.configure(xscrollcommand=self.__horbar.set)
		self.grid = self._frame.grid # function call to pass on
		self['state'] = 'disabled' # read only

	def fill(self, text):
		try: 
			self['state'] = 'normal'
			self.delete('1.0', tkinter.END)
			self.insert('1.0', '\n'.join(text))
		finally:
			self['state'] = 'disabled' # read only


class Glaze(ttk.Frame, object):
	'''The interactive application'''
	def __init__(self, args):
		if args.datafile:
			datafile = args.datafile[0]
			if os.path.isfile(datafile):
				self.load_data(datafile)
			else:
				raise Error('No such file: "%s"' % datafile)
			self.datafile = os.path.abspath(datafile)
		else:
			self.data = __default
			self.datafile = '<default data>'
			self.dnames = [d.name for d in self.data]
		self.initialdir = '.'

		self.root = tkinter.Tk()
		super(Glaze, self).__init__(self.root, width='200px', height='200px')
		self.master.title('Glaze.py - Complex glazing model for Radiance')
		self.grid(column=1, row=1, sticky='wens')
		self.root.grid_columnconfigure(1, weight=1)
		self.root.grid_rowconfigure(1, weight=1)
		self.output = GlazeText(self, wrap=tkinter.NONE)
		self.output.grid(column=2, row=0, rowspan=1, sticky='wens')
		self.grid_columnconfigure(2, weight=1)
		self.grid_rowconfigure(0, weight=1)
		self.dialog = ttk.Frame(self)
		self.dialog.grid(column=2, row=1, sticky='wens', padx='5px', pady='5px')
		self.root.bind('<Key-Escape>', lambda ev=None, f=self.done: f())
		self.build_dialog(self.dialog)
		self.root.mainloop()

	def load_data(self, fn):
		headpat = ['Surface','Tr','Tg','Tb','Rcr','Rcg','Rcb','Rgr','Rgg','Rgb','Part']
		with open(fn, 'r') as f:
			lines = f.readlines()
		if not lines:
			raise Error('Empty file: "%s"' % fn)
		head = lines[0].strip().split('\t')
		if head != headpat:
			raise Error('Header mismatch in file: "%s"' % fn)
		del lines[0]
		data = []
		i = 2
		clear = None
		for line in lines:
			sl = line.strip().split('\t')
			if not len(sl) == 11:
				raise Error('Incorrect number of elements on line %d in file "%s"'
						% (i, fn))
			name = sl[0]
			try: items = [float(s) for s in sl[1:]]
			except ValueError:
				raise Error('Incorrect value on line %d in file "%s"' % (i, fn))
			tr,tg,tb, rcr,rcg,rcb, rgr,rgg,rgb, partial = items
			g = Glazing(name, rgr,rgg,rgb, rcr,rcg,rcb, tr,tg,tb, bool(partial))
			if ((not clear) # pick out the first clear glazing, if any
					and ((abs(g.rc_r-g.rg_r)+abs(g.rc_g-g.rg_g)+abs(g.rc_b-g.rg_b))
						<= 0.005)):
				clear = g
			else:
				data.append(g)
			i += 1
		if clear:
			self.data = [clear] + data
			# everybody refers to it by that name
			global _clear
			_clear = clear
		else:
			self.data = [_clear] + data
		self.dnames = [d.name for d in self.data]

	def build_dialog(self, this):
		self.s12_sel = tkinter.IntVar()
		self.s12_sel.set(1)
		self.s34_sel = tkinter.IntVar()
		self.s34_sel.set(1)
		lf = ttk.LabelFrame(this, text='Loaded Data File')
		lf.grid(column=0, row=10, columnspan=30, sticky='nsew')
		self.filelabel = ttk.Label(lf, text=self.datafile)
		self.filelabel.grid(column=0, row=0, sticky='nsew')
		this.grid_rowconfigure(11, minsize='10px')

		lf = ttk.Frame(this)
		lf.grid(column=0, row=20, columnspan=10, rowspan=30, sticky='nsew')
		this.grid_columnconfigure(1, weight=1)
		self.npvar = tkinter.IntVar()
		one = ttk.Radiobutton(lf, value=1, text='Single Pane',
				variable=self.npvar, command=self.show_vis)
		one.grid(column=2, row=1, sticky='w')
		two = ttk.Radiobutton(lf, value=2, text='Double Pane',
				variable=self.npvar, command=self.show_vis)
		two.grid(column=2, row=2, sticky='w')
		lf.grid_columnconfigure(1, weight=1)
		lf.grid_columnconfigure(3, weight=1)
		lf.grid_rowconfigure(3, weight=1)
		self.bbox = ttk.Frame(lf)
		self.bbox.grid(column=1, row=4, columnspan=3, sticky='ws')
		self.build_bbox(self.bbox)

		self.canvas = tkinter.Canvas(this, width=250, height=150,
				xscrollincrement='1', yscrollincrement='1')
		self.canvas.grid(column=10, row=20, columnspan=10, rowspan=30,
				padx='4px')
		self.canvas.xview_scroll(-int(self.canvas['width'])//2, 'units')

		self.p1 = ttk.LabelFrame(this, text='Outer Pane',
				borderwidth=0, relief='flat', padding='2px')
		self.p1.grid(column=20, row=20, columnspan=10, rowspan=13,
				sticky='nsew')
		type1_label = ttk.Label(self.p1, text='Type:')
		type1_label.grid(column=1, row=1, sticky='e')
		self.p1_type = ttk.Combobox(self.p1, values=self.dnames)
		self.p1_type.current(0)
		self.p1_type.state(('readonly',))
		self.p1_type.bind('<<ComboboxSelected>>', self.show_vis)
		self.p1_type.grid(column=2, row=1, sticky='w')
		cvg1_label = ttk.Label(self.p1, text='Coverage:')
		cvg1_label.grid(column=1, row=2, sticky='e')
		self.p1_cvgv = tkinter.DoubleVar()
		self.p1_cvgv.set('1')
		self.p1_cvg = ttk.Entry(self.p1, textvariable=self.p1_cvgv,
				justify='right', width=15,)
		self.p1_cvg.bind('<KeyRelease>', self.show)
		self.p1_cvg.grid(column=2, row=2, sticky='w')

		self.p2 = ttk.LabelFrame(this, text='Inner Pane',
				borderwidth=0, relief='flat', padding='2px')
		self.p2.grid(column=20, row=35, columnspan=10, rowspan=13,
				sticky='nsew')
		type2_label = ttk.Label(self.p2, text='Type:')
		type2_label.grid(column=1, row=1, sticky='e')
		self.p2_type = ttk.Combobox(self.p2, values=self.dnames,
				postcommand=self.show)
		self.p2_type.current(0)
		self.p2_type.state(('readonly',))
		self.p2_type.bind('<<ComboboxSelected>>', self.show_vis)
		self.p2_type.grid(column=2, row=1, sticky='w')
		cvg2_label = ttk.Label(self.p2, text='Coverage:')
		cvg2_label.grid(column=1, row=2, sticky='e')
		self.p2_cvgv = tkinter.DoubleVar()
		self.p2_cvgv.set('1')
		self.p2_cvg = ttk.Entry(self.p2, textvariable=self.p2_cvgv,
				justify='right', width=15, )
		self.p2_cvg.bind('<KeyRelease>', self.show)
		self.p2_cvg.grid(column=2, row=2, sticky='w')

		self.npvar.set(1)
		self.show_vis()

	def build_bbox(self, this):
		self.save_button = ttk.Button(this, text='Save Material...',
				command=self.save)
		self.save_button.grid(column=1, row=1,
				sticky='ew', pady='2px')
		self.load_button = ttk.Button(this, text='Load Data...',
				command=self.load)
		self.load_button.grid(column=1, row=2,
				sticky='ew', pady='2px')
		self.done_button = ttk.Button(this, text='Done', command=self.done)
		self.done_button.grid(column=1, row=3,
				sticky='ew', pady='2px')

	def update_ui(self):
		self.p1_type['values'] = self.dnames
		self.p1_type.current(0)
		self.p2_type['values'] = self.dnames
		self.p2_type.current(0)
		self.filelabel['text']= self.datafile
		self.show_vis()

	def draw(self):
		w = int(self.canvas['width'])
		h = int(self.canvas['height'])
		xp = 0
		ydist = 10
		low = h-ydist
		self.canvas.delete('all')
		pl = [xp+2-w/2, h, xp+w/2, h, xp+w/2, 2, xp+2-w/2, 2]
		self.canvas.create_polygon(pl, outline='darkgrey', fill='')
		if self.npvar.get() == 1:
			self.draw_pane(xp, low, ydist, ydist+25, self.s12_sel, 's1', 's2')
		else:
			self.draw_pane(xp-40, low, ydist, ydist+25, self.s12_sel, 's1', 's2')
			self.draw_pane(xp+40, low, ydist, low-25, self.s34_sel, 's3', 's4')
		self.canvas.create_line((w/2-40, h/2, w/2-10, h/2), arrow=tkinter.LAST)
		self.canvas.create_text((w/2-40, h/2-20), text='inside', anchor='w')

	def draw_pane(self, xp, low, ydist, rbh, var, s1t, s2t):
		pl = [xp+10, ydist, xp+10, low, xp-10, low, xp-10, ydist]
		self.canvas.create_polygon(pl, outline='', fill='lightblue')
		s1rb = ttk.Radiobutton(self.dialog, value=1, variable=var, text=s1t,
				command=self.show)
		s2rb = ttk.Radiobutton(self.dialog, value=2, variable=var, text=s2t,
				command=self.show)
		self.canvas.create_window((xp-12, rbh), window=s1rb, anchor='e')
		self.canvas.create_window((xp+12, rbh), window=s2rb, anchor='w')
		if var.get() == 1:
			cols = ['red', 'darkgrey']
		else:
			cols = ['darkgrey', 'red']
		self.canvas.create_line((xp-10, low, xp-10, ydist), fill=cols[0],
				width=2)
		self.canvas.create_line((xp+10, low, xp+10, ydist), fill=cols[1],
				width=2)

	def show(self, ev=None):
		cvg_err = ['###   Input Error', '###', '###   Coverage must be between 0.0 and 1.0']
		head = ['# Glazing produced by Radiance glaze.py script',
				'# %s' % __revision__,
				'# Material surface normal points to interior']
		self.draw()
		panes = self.npvar.get()

		p1_type = self.data[self.p1_type.current()]
		if p1_type.partial:
			try: p1_cvg = float(self.p1_cvg.get())
			except ValueError:
				self.output.fill(cvg_err)
				return
			if 0 > p1_cvg or 1 < p1_cvg:
				self.output.fill(cvg_err)
				return
		else:
			p1_cvg = 1
		if self.s12_sel.get() == 1:
			s1_type = p1_type
			s1_cvg = p1_cvg
			s2_type = _clear
			s2_cvg = 1
		else:
			s1_type = _clear
			s1_cvg = 1
			s2_type = p1_type
			s2_cvg = p1_cvg

		if panes == 1:
			mat = s1_type.make_1_mat(s1_cvg, s2_type, s1_cvg)
			self.output.fill(head + mat)
			return

		p2_type = self.data[self.p2_type.current()]
		if p2_type.partial:
			try: p2_cvg = float(self.p2_cvg.get())
			except ValueError:
				self.output.fill(cvg_err)
				return
			if 0 > p2_cvg or 1 < p2_cvg:
				self.output.fill(cvg_err)
				return
		else:
			p2_cvg = 1
		if self.s34_sel.get() == 1:
			s3_type = p2_type
			s3_cvg = p2_cvg
			s4_type = _clear
			s4_cvg = 1
		else:
			s3_type = _clear
			s3_cvg = 1
			s4_type = p2_type
			s4_cvg = p2_cvg
		mat = s1_type.make_2_mat(s1_cvg, s2_type, s2_cvg,
				s3_type, s3_cvg, s4_type, s4_cvg)
		self.output.fill(head + mat)


	def show_vis(self, ev=None):
		p1p = p2p = False
		if self.npvar.get() == 1:
			self.p2_type.state(('disabled',))
			self.p2_cvg.state(('disabled',))
		else:
			p2_type = self.data[self.p2_type.current()]
			p2p = p2_type.partial
			self.p2_type.state(('!disabled',))
			if p2p:
				self.p2_cvg.state(('!disabled',))
		p1_type = self.data[self.p1_type.current()]
		p1p = p1_type.partial
		if p1p:
			self.p1_cvg.state(('!disabled',))
		else:
			self.p1_cvg.state(('disabled',))
		if p1p and p2p:
			self.output.fill(['###   Input Error', '###',
				'###   Only one pane may be fritted'])
			return
		self.show()

	def save(self, event=None):
		txt = self.output.get('1.0', tkinter.END)
		if 'Error' in txt: return
		fn = filedialog.asksaveasfilename(title='Save Material',
				initialdir=self.initialdir,
				filetypes=[('Radiance scene files', '*.rad'),
					('All files', '*.*')])
		if fn:
			self.initialdir,f = os.path.split(fn)
			with open(fn, 'w') as f:
				f.write(txt)

	def load(self, event=None):
		fn = filedialog.askopenfilename(title='Load Glazing Data',
				initialdir=self.initialdir,
				filetypes=[('Data files', '*.dat'),
					('All files', '*.*')])
		if fn:
			try: self.load_data(fn)
			except Error as e:
				messagebox.showerror('Error while Loading Data',
						'Failed to load data file\n\n' + str(e))
			else:
				self.initialdir,f = os.path.split(fn)
				self.datafile = fn
				self.update_ui()

	def done(self, event=None):
		self.root.destroy()


def main():
	''' This is an executable script and not currently usable as a module.
	Use the -H option for instructions.'''
	parser = argparse.ArgumentParser(add_help=False,
		description='Generate material definition for complex glazing model',)
	parser.add_argument('-H', action='help',
		help='Help: print this text to stderr and exit')
	parser.add_argument('-f', action='store', nargs=1, dest='datafile',
			metavar='datafile', help='read other glazing data')
	args = parser.parse_args() 
	Glaze(args)

if __name__ == '__main__':
	try: main()
	except KeyboardInterrupt:
		sys.stderr.write('*cancelled*\n')
		sys.exit(1)
	except Error as e:
		sys.stderr.write('%s: %s\n' % (SHORTPROGN, e))
		sys.exit(-1)

