
import os
import os.path

import optparse

import sys

import re


def check_directory(option, opt_str, value, parser):
	if not os.path.exists(value):
		raise optparse.OptionValueError("directory %r does not exist" % value)
	setattr(parser.values, option.dest, value)


def buildParser():
	usage = "usage: %prog [options] textfilters"
	parser = optparse.OptionParser(usage)

	group = optparse.OptionGroup(parser, "Global Configuration")
	group.add_option('-d', dest='directory',   action='callback',  type='string',  callback=check_directory,  default='.', help="the root directory")
	group.add_option('-i', dest='insensitive', action='store_true', default=False, help="filters are case insensitive")
	group.add_option('--no-comments', dest='nocomments', action='store_true', default=False, help="text filters ignore comments")
	parser.add_option_group(group)

	group = optparse.OptionGroup(parser, "File Filters")
	group.add_option('-f', dest='filefilters', action='append',     default=['\.py$'], help="matches the file name", metavar="FILTER")
	parser.add_option_group(group)

	group = optparse.OptionGroup(parser, "Text Filters")
	group.add_option('--id', dest='identifiers', action='append', default=[], metavar="FILTER" , help="specialized text filter to find an identifier")
	group.add_option('-x', dest='excludes', action='append', default=[], help="excludes matching text", metavar="FILTER")
	group.add_option('--import', dest='imports', action='store_true', default=False, help="restricts search to imports")
	parser.add_option_group(group)

	return parser


def fileMatches(filename):
	for f in fileFilters:
		if not f.search(filename):
			return False
	return True

def textMatches(text):
	for f in textFilters:
		if not f.search(text):
			return False

	for f in excludeFilters:
		if f.search(text):
			return False
		
	return True


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
		code, comment =  splitLine(line)

		if options.nocomments:
			line = code

		if textMatches(line):
			self.callback(fn, lineno, line)
			self.occurances += 1

		if code: self.lines += 1

	def handleFile(self, fn):
		fh = open(fn)
		lineno = 1
		for line in fh:
			self.handleLine(fn, lineno, line)
			lineno += 1
		fh.close()
		self.files += 1


	def walk(self, dn, callback):
		self.callback = callback
		
		for path, dirs, files in os.walk(dn):
			for f in files:
				fn = os.path.join(path, f)
				if fileMatches(fn):
					self.handleFile(fn)

		if self.lastFile != None:
			print

		print "%7.d occurances." % self.occurances
		print "%7.d lines." % self.lines
		print "%7.d files." % self.files



if __name__ == '__main__':
	try:
		import psyco
		psyco.full()
	except ImportError:
		pass


	parser = buildParser()
	options, args = parser.parse_args()

	if options.imports:
		args.insert(0, "^\s*(import|from)\s")

	# Create specialized text filters
	# Identifiers are a little strange, as we need to take into account
	# that they may be at the start or the end of a line.
	for i in options.identifiers:
		args.append('(?<![\w\d_])(%s)(?![\w\d_])' % i)


	if len(args) < 1:
		parser.error("at least one text filter must be spesified")


	parser.destroy()


	flags = 0
	if options.insensitive: flags |= re.I

	# Build the regular expressions.

	print

	fileFilters = []
	for ff in options.filefilters:
		print "file: %s" % ff
		fileFilters.append(re.compile(ff, flags))

	textFilters = []
	for tf in args:
		print "text: %s" % tf
		textFilters.append(re.compile(tf, flags))

	excludeFilters = []
	for ef in options.excludes:
		print "excl: %s" % ef
		excludeFilters.append(re.compile(ef, flags))

	print

	directoryName = options.directory

	# Search the files.
	sg = StandardGrep()
	sg.walk(directoryName, sg.displayMatch)
