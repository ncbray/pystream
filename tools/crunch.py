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

from xmloutput import XMLOutput

def handleFile(o, fullname):
	with o.scope('p'):
		with o.scope('b'):
			o << fullname
	o.endl()

	with o.scope('pre'):
		o << '# Copyright (c) 2010 Nicholas Bray'
		o.endl()
		o.endl()

		for line in open(fullname):
			o << line.rstrip()
			o.endl()

o = open("crunch.html", 'w')
o = XMLOutput(o)

with o.scope('html'):
	with o.scope('body'):
		for path, dirs, files in os.walk('bin'):
			for f in files:
				if f[-3:] == '.py':
					fullname = os.path.join(path, f)
					print fullname

					handleFile(o, fullname)
