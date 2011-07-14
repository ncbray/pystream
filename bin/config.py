# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Use a JIT?
usePsyco = True

debugOnFailiure = False

# Create output directory relative to this config file.
import os.path
base, junk = os.path.split(__file__)
outputDirectory = os.path.normpath(os.path.join(base, '..', 'summaries'))

doDump = False
maskDumpErrors = False
doThreadCleanup = False

dumpStats = False


# Pointer analysis testing
useXTypes = True
useControlSensitivity = True
useCPA = True

if True:
	testOnly = [
		('tests', 'test_full'),
		#('tests', 'test_canonical'),
		#('tests', 'test_graphalgorithims'),
		('tests', 'ipa'),
		('tests', 'test_ssa')
	]

testExclude = [
	# Known to be broken
	('tests', 'decompilertests', 'test_exception'),
	]
