usePsyco        = False

# Absolute path, as durring development the script
# may be called from different working directories...
outputDirectory = "c:/projects/pystream/summaries"

if False:
	limitedTest = [
		#'tests.shape.test_shape',
		#'tests.shape.test_shape_examples',
		#'tests.shape.test_shape_compound',
		#'tests.shape.test_shape_pathinfo',
		#'tests.test_database',
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
