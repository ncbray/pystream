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
import hashlib

def ensureDirectoryExists(dirname):
	if not os.path.exists(dirname): os.makedirs(dirname)

def join(directory, name, format=None):
	if format is not None:
		name = "%s.%s" % (name, format)
	return os.path.join(directory, name)

def relative(path, root):
	return os.path.relpath(path, root)

def fileInput(directory, name, format=None, binary=False):
	fullname = join(directory, name, format)
	f = open(fullname, 'rb' if binary else 'r')
	return f

def readData(directory, name, format=None, binary=False):
	f = fileInput(directory, name, format, binary=binary)
	result = f.read()
	f.close()
	return result


def fileOutput(directory, name, format=None, binary=False):
	ensureDirectoryExists(directory)
	fullname = join(directory, name, format)
	f = open(fullname, 'wb' if binary else 'w')
	return f

def writeData(directory, name, format, data, binary=False):
	f = fileOutput(directory, name, format, binary=binary)
	f.write(data)
	f.close()

def writeBinaryData(directory, name, format, data):
	writeData(directory, name, format, data, binary=True)


def dataHash(s):
	h = hashlib.sha1()
	h.update(s)
	return h.digest()
	#return h.hexdigest()

def fileHash(directory, name, format=None, binary=False):
	return dataHash(readData(directory, name, format, binary))

def writeFileIfChanged(directory, name, format, data, binary=False):
	if os.path.exists(join(directory, name, format)):
		if fileHash(directory, name, format, binary) == dataHash(data):
			return False

	writeData(directory, name, format, data, binary)
	return True
