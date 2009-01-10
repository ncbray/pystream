usePsyco        = True

# Absolute path, as durring development the script
# may be called from different working directories...
outputDirectory = "c:/projects/pystream/summaries"

if True:
	limitedTest = [
		'tests.shape.test_shape',
		'tests.shape.test_shape_compound',
		'tests.shape.test_shape_paths',
		'tests.test_database',
		#'tests.test_full',
		#'tests.test_lattice',
		]
else:
	testExclude = [
		# Time consuming
		#'tests.test_full',
		'tests.shape.test_shape',

		# Old, slightly buggy.
		'tests.test_sese',
		'tests.test_lattice',
		'analysis.bdddatalog.tests.test_datalog',
		'analysis.bdddatalog.tests.test_relational',
		]
