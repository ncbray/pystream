import os.path
import hashlib

def ensureDirectoryExists(dirname):
	if not os.path.exists(dirname): os.makedirs(dirname)

def join(directory, name, format):
	return os.path.join(directory, "%s.%s" % (name, format))

def fileInput(directory, name, format, binary=False):
	fullname = join(directory, name, format)
	f = open(fullname, 'rb' if binary else 'r')
	return f

def readData(directory, name, format, binary=False):
	f = fileInput(directory, name, format, binary=binary)
	result = f.read()
	f.close()
	return result


def fileOutput(directory, name, format, binary=False):
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

def fileHash(directory, name, format, binary=False):
	return dataHash(readData(directory, name, format, binary))

def writeFileIfChanged(directory, name, format, data, binary=False):
	if os.path.exists(join(directory, name, format)):
		if fileHash(directory, name, format, binary) == dataHash(data):
			return False

	writeData(directory, name, format, data, binary)
	return True
