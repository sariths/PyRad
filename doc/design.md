
###Design goals
 - usage instructions (-H)
 - progress report (-V)
 - dry-run mode (-N)
 - detailed error diagnostics
 - compatible with Python 2.7 and Python 3.x
 - self contained (all functionality can be combined in one file)
 - truly cross-platform (no external dependencies other than Python and Radiance)
 - direct process management (no intermediate shell calls)
 - immune to whitespace in file names
 - tamper-proof use of temporary files


When adding scripts to this collection, you might want to consider a few guidelines:

  * Create test cases in `ray/test/testcases/<category>/test_<module>.py`,
    that the current csh/pl script passes.
	In the end, make sure that the new script passes as well.

  * Use the general architecture as shown in the existing examples

    - `#!/usr/bin/env python`

    - Module docstring

    - `__all__ = ('main')`

	- Imports from the standard library. When library names have changed,
	  try the Python3 version first, and on ImportError the Python2.7
	  version, with suitable renames. E.g.:

			try:
				from itertools import zip_longest, chain
			except ImportError:
				from itertools import izip_longest as zip_longest, chain

	- Search for the Radiance Python support library (if needed):

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

	  When invoked as a module, the caller is responsible that the correct
	  directories are present in sys.path.
	  When frozen, the support modules will be included and no search is
	  necessary.
	  We use `sys.exit()` instead of just `exit()` because the latter is
	  defined in site.py, which is not normally included in a frozen file.

    - `from pyradlib.pyrad_proc import ProcMixin`

      Process management library (if needed). See below for building/installing.

    - `SHORTPROGN = os.path.splitext(os.path.basename(sys.argv[0]))[0]`

    - If "Error" was not imported from pyrad_proc above:
	
			class Error(Exception): pass

    - `SOME_DATA = '''...'''`

      eg. for calfile templates

    - `class **Name**(ProcMixin):`

      Using the uppercased name of the script.

    - A number of standardized methods from ProcMixin to use. 

      * `def raise_on_error(self, actstr, e):`

      * `def qjoin(self, sl):`

      * `self.call_one(self, cmdl, actstr, _in=None, out=None, universal_newlines=False):`

        Invoke a Radiance executable.
				`cmdl` is the command line with executable name and arguments seperated in a list.
				`actstr` is a short description of the action for verbose operation and error messages
				(eg.: `"filter input image"`). To have it read from stdin, pass an open file object to `_in`,
				to have it write to stdout, pass an open file object to `out`.
				Otherwise it will use the existing stdin/stdout streams.
				If `universal_newlines` is true, the *output* pipe will return
				text instead of bytes data.

      * `self.call_two(self, cmsdl_1, cmdl_2, actstr_1, actstr_2, _in=None, out=None, universal_newlines=False):`

		Invoke two Radiance executable and chain them in a pipe
		(`cmd1 | cmd2`). `_in` and `out` apply to the complete pipe.
		The other arguments are analog to call_one().

      * `self.call_many(self, cmsdsl, actstr, _in=None, out=None, universal_newlines=False):`

		Invoke an arbitrary number of  Radiance executable and chain them in a
		pipe (`cmdsl[0] | cmdsl[1]| ... | cmdsl[N] `).
		`_in` and `out` apply to the complete pipe.
		The other arguments are analog to call_one().

    -	`def main():`

      * docstr for main():
              
              '''This is a command line script and not currently usable as a module.
              Use the -H option for instructions.'''
              
	  * Use `argparse.ArgumentParser()` for command line handling if possible.
	    Some of the existing scripts have slightly unconventional command lines
	    though, which may make this a challenge.

    - start on loading:

            if __name__ == '__main__':
                try: main()
                    except KeyboardInterrupt:
                        sys.stderr.write('*cancelled*\n')
                        sys.exit(1)
                    except Exception as e:
                        sys.stderr.write('%s: %s\n' % (SHORTPROGN, e))
                        sys.exit(-1)



###Building and Installing

Pyradlib is shipped as `ray/src/common/pyradlib`.
It is meant to be installed as a subdirectory to the Radiance file library.
On unix systems this is sufficient for the scripts to find it.

This doesn't work as well on Windows, because scripts are typically not
invoked directly, but only as an argument to the interpreter.
The most practical approach there is to use `pyinstaller -F` to generate
completely self-contained executables. If file size is of concern (eg. for a
binary distribution), then create a spec file to build a multiprogram bundle
with merged common modules, which will include the runtime overhead in only one
of the files.

All that can easily be included in any of the current Radiance build systems.

