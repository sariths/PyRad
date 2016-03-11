# PyRad
Replacements in Python for some of the shell/Perl scripts included with the
[Radiance](http://www.radiance-online.org/) lighting simulation package.

Usually the scripts are drop-in replacements for the originals, but with
some additional functionality.

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

###Currently implemented
 * **falsecolor.py** - Make a false color Radiance picture
 * **phisto.py** - Compute foveal histogram for picture set
 * **rlux.py** - Compute illuminance from ray origin and direction
 * **pveil.py** - Add veiling glare to picture

###Contributions welcome
 - more scripts (implementing the same design goals)
 - systematic test cases (only casually tested so far)
 - Wishlist items (with specification if original is undocumented)
