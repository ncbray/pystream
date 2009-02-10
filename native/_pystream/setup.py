from distutils.core import setup, Extension

setup(name='_pystream',
	version='1.0',
	author='Nick Bray',
	ext_modules=[
		Extension('_pystream', ['_pystream.cpp'])
		]
	)

# TODO automatically copy into the library directory?
# NOTES
#python setup.py install --home=~ \
#                        --install-purelib=python/lib \
#                        --install-platlib=python/lib.$PLAT \
#                        --install-scripts=python/scripts
#                        --install-data=python/data
# This generates a .egg-info file?
