usePsyco        = True

# Absolute path, as durring development the script
# may be called from different working directories...
outputDirectory = "c:/projects/pystream/summaries"

#limitedTest = ['tests.test_util']

testExclude = [
	'tests.test_full',
	'tests.test_sese',
	'analysis.bdddatalog.tests.test_datalog',
	'analysis.bdddatalog.tests.test_relational',
	]
