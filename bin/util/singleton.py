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

__all__ = ('singleton', 'instance')

class singletonMetaclass(type):
	def __new__(self, name, bases, d):
		if '__repr__' not in d:
			def __repr__(self):
				return name
			d['__repr__'] = __repr__
		cls = type.__new__(self, name+'Type', bases, d)
		return cls()

class singleton(object):
	__metaclass__ = singletonMetaclass
	__slots__ = ()

singleton = type(singleton)


# A decorator for turning a class into a psedo-singleton
# Handy for stateless TypeDispatcher classes
def instance(cls):
	cls.__name__ += 'Type'
	return cls()
