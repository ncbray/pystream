import os
import os.path

import sys

import re


directoryName = "."

insensitive = False

grepString = r'(partialEntry)|(partialExit)'
fileString = '\.py$'

state = 0

# Read the command line arguents
for arg in sys.argv[1:]:
	if arg[0] == '-' and len(arg) >= 2:
		if arg=='-i':
			insensitive = True
		elif arg[:2] == '-f':
			fileString = arg[2:]
		elif arg[:2] == '-d':
			directoryName = arg[2:]
			assert os.path.exists(directoryName), "Directory %r does not exist." % directoryName

		else:
			assert False, "Unknown command: %s" % arg
	else:
		if state == 0:
			grepString = arg
			state = 1
		elif state == 1:
			replaceString = arg
			state = 2
		else:
			assert False, "Too many arguments."

assert state == 2, "Too few arguments."

	
graveyardFilter = re.compile(r'graveyard')

# Build the regular expressions.
fileFilter = re.compile(fileString)

flags = 0
if insensitive: flags |= re.I


grepFilter = re.compile(grepString, flags)

print


# HACK can't deal with multi-line strings?
def makeCommentRE():
	simple       = r'[^\'"#]+'
	doubleQuoted = r'(?:"(?:[^"\\]|\\.|\\$)*(?:"|$))'
	singleQuoted = r"(?:'(?:[^'\\]|\\.|\\$)*(?:'|$))"
	notComment   = r"(?:%s|%s|%s)+" % (simple, singleQuoted, doubleQuoted)

	comment      = r"(?:#\s*(.+)?)"

	return re.compile(r"^(%s)?%s?$" % (notComment, comment))

commentRE = makeCommentRE()


def splitLine(line):
	match = commentRE.match(line)
	assert match != None, line
	return [('' if group==None else group.strip()) for group in match.groups()]



class StandardGrep(object):
	def __init__(self):
		self.files = 0
		self.lines = 0
		self.occurances = 0

		self.lastFile = None

	def displayMatch(self, fn, lineno, line):
		if fn != self.lastFile:
			if self.lastFile != None:
				print
			print fn
			self.lastFile = fn
		print "%d\t%s" % (lineno, line.strip())
		
		
	def handleLine(self, fn, lineno, line):
		if grepFilter.search(line):
			self.callback(fn, lineno, line)
			self.occurances += 1

		code, comment =  splitLine(line)
		if code: self.lines += 1

	def handleFile(self, fn):
		fh = open(fn)
		data = fh.read()
		fh.close()

		#result = re.sub(grepString, replaceString, data)
		result = grepFilter.sub(replaceString, data)
		if result != data:
			print "Rewrite", fn
			fh = open(fn, 'w')
			fh.write(result)
			fh.close()

		self.files += 1



	def walk(self, dn, callback):
		self.callback = callback
		
		for path, dirs, files in os.walk(dn):
			for f in files:
				fn = os.path.join(path, f)
				if fileFilter.search(fn) and not graveyardFilter.search(fn):
					self.handleFile(fn)

		if self.lastFile != None:
			print

		print "%7.d occurances." % self.occurances
		print "%7.d lines." % self.lines
		print "%7.d files." % self.files


# Search the files.
sg = StandardGrep()
sg.walk(directoryName, sg.displayMatch)
