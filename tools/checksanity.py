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

import os.path

if __name__ == '__main__':
	dn = 'bin'

	for path, dirs, files in os.walk(dn):
		fileset = set(files)
		compiled   = 0
		uncompiled = 0

		for fn in files:
			root, ext = os.path.splitext(fn)

			if ext == '.py':
				pyc = root + '.pyc'
				pyo = root + '.pyo'
				if pyc not in fileset and pyo not in fileset:
					print "Uncompiled:\t%s" % os.path.join(path, fn)
					uncompiled += 1

			elif ext == '.pyc' or ext == '.pyo':
				py = root + '.py'
				if py not in fileset:
					print "No source:\t%s" % os.path.join(path, fn)
				compiled += 1

		if uncompiled and not compiled and not dirs:
			print "Dead directory:\t%s" %  path
