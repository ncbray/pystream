# Use a JIT?
usePsyco = False

# Create output directory relative to this config file.
import os.path
base, junk = os.path.split(__file__)
outputDirectory = os.path.normpath(os.path.join(base, '..', 'summaries'))

# Select which tests to run.
if True:
	limitedTest = [
		'tests.shape.test_shape',
		'tests.shape.test_shape_examples',
		'tests.shape.test_shape_compound',
		'tests.shape.test_shape_pathinfo',
		'tests.test_database',
		'tests.test_full',
		'tests.cpa.test_cpa',
		]
else:
	testExclude = [
		# Time consuming
		#'tests.test_full',

		# Old, slightly buggy.
		'tests.test_sese',
		'tests.test_lattice',
		'analysis.bdddatalog.tests.test_datalog',
		'analysis.bdddatalog.tests.test_relational',
		]
