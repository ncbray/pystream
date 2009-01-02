usePsyco        = True

# Absolute path, as durring development the script
# may be called from different working directories...
outputDirectory = "c:/projects/pystream/summaries"

if True:
	limitedTest = [
		'tests.test_database',
		'tests.test_full',
		]

testExclude = [
	#'tests.test_full',
	'tests.test_shape',
	'tests.test_sese',
	'analysis.bdddatalog.tests.test_datalog',
	'analysis.bdddatalog.tests.test_relational',
	]
