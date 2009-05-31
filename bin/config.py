# Use a JIT?
usePsyco = True

# Create output directory relative to this config file.
import os.path
base, junk = os.path.split(__file__)
outputDirectory = os.path.normpath(os.path.join(base, '..', 'summaries'))


if False:
	testOnly = [
		('tests', 'test_full'),
		#('tests', 'shape', 'test_shape'),
		#('tests', 'shape', 'test_shape_compound'),
		('tests', 'test_canonical'),
	]

testExclude = [
	# Known to be broken
	('tests', 'decompiler', 'test_exception'),

	# Not completely implemented
	('tests', 'test_lattice'),
	('tests', 'test_sese'),
	]
