''' pyrad_proc.py - Process and pipeline management for Python Radiance scripts

To create a single-file *.py, at the top of the script write:
  - from pyradlib.proc_mixin import ProcMixin
  - OR replace the above line with the contents of this script

2016 - Georg Mischler
'''

import sys
import subprocess

class ProcMixin():
	'''Process and pipeline management for Python Radiance scripts
	'''

	def __configure_subprocess(self):
		'''Prevent subprocess module failure in frozen scripts on Windows.
		Private method.
		'''
		# On Windows, sys.stdxxx may not be available when:
		# - built as *.exe with "pyinstaller --noconsole"
		# - invoked via CreateProcess() and stream not redirected
		try:
			sys.__stdin__.fileno()
			self._stdin = sys.stdin
		except: self._stdin = subprocess.PIPE
		try:
			sys.__stdout__.fileno()
			self._stdout = sys.stdout
		except: self._stdout = subprocess.PIPE
		try:
			sys.__stderr__.fileno()
			self._stderr = sys.stderr
		# keep subprocesses from opening their own console.
		except: self._stderr = subprocess.PIPE
		if hasattr(subprocess, 'STARTUPINFO'):
			si = subprocess.STARTUPINFO()
			si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
			self._pipeargs = {'startupinfo':si}
		else: self._pipeargs = {}
		# private attribute to indicate established configuration
		self.__proc_mixin_setup = True

	def qjoin(self, sl):
		'''Join a list with quotes around each element containing whitespace.
		We only use this to display command lines on sys.stderr, the actual
		Popen() calls are made with the original list.
		'''
		def _q(s):
			if ' ' in s or '\t' in s or ';' in s:
				return "'" + s + "'"
			return s
		return  ' '.join([_q(s) for s in sl])

	def call_one(self, cmdl, actstr, _in=None, out=None):
		'''Create a single subprocess, possibly with an incoming and outgoing
		pipe at each end.
		- actstr
		  A text string of the form "do something".
		  Used in verbose mode as "### do someting\\n### [command line]"
		  Used in error messages as "Scriptname: Unable to do something".
		- _in / out
		  What to do with the input and output pipes of the process:
		  * a filename as string
		    Open file and use for reading/writing.
		  * a File object
		    Use for reading/writing
		  * subprocess.PIPE
		    Pipe will be available in returned object for reading/writing.
		  * None (default)
		    System stdin/stdout will be used if available
		If _in is a subprocess.PIPE, you should call p.wait() on the returned
		Popen instance after you finish writing to it.
		'''
		try: self.__proc_mixin_setup
		except AttributeError: self.__configure_subprocess()
		if _in == subprocess.PIPE: stdin = _in
		elif isinstance(_in, str): stdin = open(_in, 'rb')
		elif isinstance(_in, file): stdin = _in
		else: stdin = self._stdin
		if out == subprocess.PIPE: stdout = out
		elif isinstance(out, str): stdout = open(out, 'wb')
		elif isinstance(out, file): stdout = out
		else: stdout = self._stdout
		displ = cmdl[:]
		if isinstance(_in, str): displ[:0] = [_in, '>']
		if isinstance(out, str): displ.extend(['>', out])
		if self.verbose:
			sys.stderr.write('### %s \n' % actstr)
			sys.stderr.write(self.qjoin(displ) + '\n')
		if not self.donothing:
			try: p = subprocess.Popen(cmdl, stdin=stdin, stdout=stdout,
					stderr=self._stderr, **self._pipeargs)
			except Exception as e:
				self.raise_on_error(actstr, str(e))
			if stdin != subprocess.PIPE:
				# caller needs to wait after writing (else deadlock)
				res = p.wait()
				if res != 0:
					self.raise_on_error(actstr,
							'Nonzero exit (%d) from command [%s].'
							% (res, self.qjoin(displ)))
			return p

	def call_two(self, cmdl_1, cmdl_2, actstr_1, actstr_2, _in=None, out=None):
		'''Create two processes, chained via a pipe, possibly with an incoming
		and outgoing pipe at each end.
		Returns a tuple of two Popen instances.
		Arguments are equivalent to call_one(), with _in and out applying
		to the ends of the chain.
		If _in is subprocess.PIPE, should call p.wait() on both returned popen
		instances after you finish writing to the first.
		'''
		try: self.__proc_mixin_setup
		except AttributeError: self.__configure_subprocess()
		if _in == subprocess.PIPE: stdin = _in
		elif isinstance(_in, str): stdin = open(_in, 'rb')
		elif isinstance(_in, file): stdin = _in
		else: stdin = self._stdin
		sys.stderr.write('-- stdin: %s\n' % str(stdin))
		if out == subprocess.PIPE: stdout = out
		elif isinstance(out, str): stdout = open(out, 'wb')
		elif isinstance(out, file): stdout = out
		else: stdout = self._stdout
		if self.verbose:
			sys.stderr.write('### %s \n' % actstr_1)
			sys.stderr.write('### %s \n' % actstr_2)
			sys.stderr.write(self.qjoin(cmdl_1) + ' | ')
		if not self.donothing:
			try: p1 = subprocess.Popen(cmdl_1, stdin=stdin,
					stdout=subprocess.PIPE, stderr=self._stderr,
					**self._pipeargs)
			except Exception as e:
				self.raise_on_error(actstr_1, str(e))
		if self.verbose:
			if isinstance(out, str):
				sys.stderr.write(self.qjoin(cmdl_2) + ' > "%s"\n' % out)
			elif isinstance(out, file):
				sys.stderr.write(self.qjoin(cmdl_2) + ' > "%s"\n' % out.name)
			else:
				sys.stderr.write(self.qjoin(cmdl_2) + '\n')
		if not self.donothing:
			try:
				p2 = subprocess.Popen(cmdl_2, stdin=p1.stdout, stdout=stdout,
						stderr=self._stderr, **self._pipeargs)
				p1.stdout.close()
			except Exception as e:
				self.raise_on_error(actstr_2, str(e))
			if stdin != subprocess.PIPE:
				# caller needs to wait after writing (else deadlock)
				res = p1.wait()
				if res != 0:
					self.raise_on_error(actstr_1,
							'Nonzero exit (%d) from command [%s].'
							% (res, self.qjoin(cmdl_1)))
				res = p2.wait()
				if res != 0:
					self.raise_on_error(actstr_2,
							'Nonzero exit (%d) from command [%s].'
							% (res, self.qjoin(cmdl_2)))
			return p1, p2


### end of proc_mixin.py
