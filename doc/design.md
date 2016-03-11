
###Design goals
 - usage instructions (-H)
 - progress report (-V)
 - dry-run mode (-N)
 - detailed error diagnostics
 - compatible with Python 2.7 and Python 3.x
 - self contained (all functionality in one file)
 - truly cross-platform (no external dependencies other than Python and Radiance)
 - direct process management (no intermediate shell calls)
 - immune to whitespace in file names
 - tamper-proof use of temporary files


When adding scripts to this collection, you might want to consider a few guidelines:

  * Use the general architecture as shown in the existing examples

    - boilerplate header

    - `__all__ = ('main')`

      for now. Allowing use as a module might be useful in some cases

    - `SHORTPROGN = ...`

    - `class Error(Exception): pass`

    - `SOME_DATA = '''...`

      eg. for calfile templates

    - `class Name():`

      Using the uppercased name of the script.

    - A number of standardized methods to use. We currently keep the files self-contained. But we may decide in the future to farm out certain common elements into one or several files, eg. containing a common base class with utility routines. Using identical method definitions now where possible will make this a lot easier.

      * `def raise_on_error(self, actstr, e):`

      * `def qjoin(self, sl):`

      * `self.call_one(self, cmdl, actstr, _in=None, out=None):`

        Invoke a Radiance executable.
				`cmdl` is the command line with executable name and arguments seperated in a list.
				`actstr` is a short description of the action for verbose operation and error messages
				(eg.: `"filter input image"`). To have it read from stdin, pass an open file object to `_in`,
				to have it write to stdout, pass an open file object to `out`.
				Otherwise it will use the existing stdin/stdout streams.

      * `self.call_two(self, cmsdl_1, cmdl_2, actstr_1, actstr_2, _in=None, out=None):`

				Invoke two Radiance executable and chain them in a pipe (`cmd1 | cmd2`).
				`_in` and `out` apply to the complete pipe. The other arguments are analog to call_one().
    -	`def main():`

      * docstr for main():
              
              '''This is a command line script and not currently usable as a module.
              Use the -H option for instructions.'''
              
      * Use `argparse.ArgumentParser()` for command line handling if possible. Some of the existing scripts have slightly unconventional command lines though, which may make this a challenge.

    - start on loading:

            if __name__ == '__main__':
                try: main()
                    except KeyboardInterrupt:
                        sys.stderr.write('*cancelled*\n')
                    except Exception as e:
                        sys.stderr.write('%s: %s\n' % (SHORTPROGN, e))




