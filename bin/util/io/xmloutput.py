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

__all__ = ['XMLOutput']

import re
# Note: converting line breaks to break tags is a bit of a hack.
xmlLUT = {'&':'&amp;', '<':'&lt;', '>':'&gt;', '\n':'<br/>'}
xmlRE = re.compile('[%s]' % ''.join(xmlLUT.iterkeys()))

def convert(match):
	return xmlLUT.get(match.group(0), 'ERROR')

def content(s):
	return xmlRE.sub(convert, str(s))

class xmlscope(object):
	__slots__ = 'out', 'name', 'kargs', 'parent'

	def __init__(self, out, name, kargs, parent=None):
		self.out  = out
		self.name = name
		self.kargs = kargs
		self.parent = parent

	def __enter__(self):
		if self.parent: self.parent.__enter__()
		self.out.begin(self.name, **self.kargs)

	def __exit__(self, type, value, tb):
		self.out.end(self.name)
		if self.parent: self.parent.__exit__(type, value, tb)

	def scope(self, s, **kargs):
		return xmlscope(self.out, s, kargs, self)

class XMLOutput(object):
	def __init__(self, f):
		self.f = f
		self.tagStack = []

	def close(self):
		self.f = None

	def __lshift__(self, s):
		return self.write(s)

	def __iadd__(self, s):
		return self.begin(s)

	def __isub__(self, s):
		return self.end(s)

	def __out(self, s):
		self.f.write(s)

	def write(self, s):
		self.__out(content(s))
		return self

	def tag(self, s, **kargs):
		if kargs:
			args = ' '.join(['%s="%s"' % (k, v) for k, v in kargs.iteritems()])
			self.__out('<%s %s />' % (s, args))
		else:
			self.__out('<%s />' % s)
		return self

	def begin(self, s, **kargs):
		if kargs:
			args = ' '.join(['%s="%s"' % (k, v) for k, v in kargs.iteritems()])
			self.__out('<%s %s>' % (s, args))
		else:
			self.__out('<%s>' % s)
		self.tagStack.append(s)
		return self


	def end(self, s):
		matched = self.tagStack.pop()
		assert s == matched, 'Ending tag "%s" does not match begining tag "%s".' % (s, matched)
		self.__out('</%s>' % s)
		return self

	def scope(self, s, **kargs):
		return xmlscope(self, s, kargs)

	def endl(self):
		self.__out('\n')
		return self
