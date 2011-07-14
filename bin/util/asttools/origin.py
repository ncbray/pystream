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

from util.monkeypatch.xcollections import namedtuple

def originString(origin):
	if origin is None: return "<unknown origin>"

	if origin.filename:
		s = "File \"%s\"" % origin.filename
	else:
		s = ''


	if origin.lineno is None or origin.lineno < 0:
		needComma = False
	elif origin.col is None or origin.col < 0:
		if s: s += ', '
		s = "%sline %d" % (s, origin.lineno)
		needComma = True
	else:
		if s: s += ', '
		s = "%sline %d:%d" % (s, origin.lineno, origin.col)
		needComma = True

	if origin.name:
		if s:
			if needComma:
				s += ', '
			else:
				s += ' '
		s = "%sin %s" % (s, origin.name)

	return s

Origin = namedtuple('Origin', 'name filename lineno col', dict(originString=originString))
