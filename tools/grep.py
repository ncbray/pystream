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


import os
import os.path

import optparse

import sys

import re


def check_directory(option, opt_str, value, parser):
	if not os.path.exists(value):
		raise optparse.OptionValueError("directory %r does not exist" % value)
	setattr(parser.values, option.dest, value)

def replacesIDCallback(option, opt, value, parser):
	match, replace = value
	match = makeIDMatcher(match)

	parser.values.replaces.append((match, replace))

def matchIDCallback(option, opt, value, parser):
	parser.largs.append(makeIDMatcher(value))

def buildParser():
	usage = "usage: %prog [options] textfilters"
	parser = optparse.OptionParser(usage)

	group = optparse.OptionGroup(parser, "Global Configuration")
	group.add_option('-d', dest='directory',   action='callback',  type='string',  callback=check_directory,  default='.', help="the root directory")
	group.add_option('-i', dest='insensitive', action='store_true', default=False, help="filters are case insensitive")
	group.add_option('-n', dest='dryrun', action='store_true', default=False, help="modifications are not written to disk")

	group.add_option('--no-comments', dest='nocomments', action='store_true', default=False, help="text filters ignore comments")
	parser.add_option_group(group)

	group = optparse.OptionGroup(parser, "File Filters")
	group.add_option('-t', dest='filetypes', action='append', default=[], help="matches the file type", metavar="TYPE")
	group.add_option('-f', dest='filefilters', action='append', default=[], help="matches the file name", metavar="FILTER")
	group.add_option('-g', dest='excludefilefilters', action='append', default=[], help="excludes file name", metavar="FILTER")
	parser.add_option_group(group)

	group = optparse.OptionGroup(parser, "Text Filters")
	group.add_option('--id', dest='identifiers', action='callback', callback=matchIDCallback, type="str", metavar="FILTER", help="specialized text filter to find an identifier")

	group.add_option('-x', dest='excludes', action='append', default=[], help="excludes matching text", metavar="FILTER")
	group.add_option('--import', dest='imports', action='store_true', default=False, help="restricts search to imports")

	group.add_option('-r', dest='replaces', action='append', default=[], help="replaces matching text", nargs=2, metavar="MATCH SUB")
	group.add_option('--idr', dest='replaces', action='callback', callback=replacesIDCallback, help="replaces matching identifier", type='str', nargs=2, metavar="MATCH SUB")

	parser.add_option_group(group)

	return parser


def fileMatches(filename):
	for f in fileFilters:
		if not f.search(filename):
			return False

	for f in excludeFileFilters:
		if f.search(filename):
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

def textReplace(text):
	for r, s in replaceFilters:
		text = r.sub(s, text)
	return text

def replaceActive():
	return bool(replaceFilters)

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
	def __init__(self, matchText):
		self.matchText = matchText
		self.files = 0
		self.lines = 0
		self.occurances = 0
		self.fileOccurances = 0

		self.linesChanged = 0
		self.filesChanged = 0

		self.lastFile = None

	def displayMatch(self, fn, lineno, line):
		if fn != self.lastFile:
			if self.lastFile != None:
				print
			print fn
			self.lastFile = fn
		print "%d\t%s" % (lineno, line.strip())

		self.occurances += 1

	def displayReplace(self, line, newline):
		print "  ->\t%s" % (newline.strip(),)


	def handleLine(self, fn, lineno, line):
		code, comment =  splitLine(line)
		if code: self.lines += 1

		if options.nocomments:
			matchline = code
		else:
			matchline = line

		matched = textMatches(matchline)

		self.matched |= matched

		if replaceActive():
			if matched:
				newline = textReplace(line)
				if newline != line:
					self.callback(fn, lineno, line)
					self.displayReplace(line, newline)

					self.changed = True
					line = newline
					self.linesChanged += 1

			if not options.dryrun:
				self.lineBuffer.append(line)

		else:
			if matched:
				self.callback(fn, lineno, line)


	def handleFile(self, fn):
		if self.matchText:
			fh = open(fn)
			lineno = 1

			self.lineBuffer = []
			self.changed    = False
			self.matched    = False

			for line in fh:
				self.handleLine(fn, lineno, line)
				lineno += 1
			fh.close()

			if self.matched:
				self.fileOccurances += 1

			if replaceActive() and self.changed and not options.dryrun:
				text = "".join(self.lineBuffer)
				fh = open(fn, 'w')
				fh.write(text)
				fh.close()
				self.filesChanged += 1
		else:
			print fn

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

		if self.matchText:
			print "%7.1d occurances in %d file%s." % (self.occurances, self.fileOccurances, 's' if self.fileOccurances != 1 else '')
			print "%7.1d lines." % self.lines
		print "%7.1d files." % self.files

		if replaceActive():
			print "%7.1d lines rewritten." % self.linesChanged
			print "%7.1d files changed." % self.filesChanged

def makeIDMatcher(s):
	# The lookaheads/lookbehinds ensures that the expr starts and ends either
	# with a non-id character, or adjacent to one.
	# This allows exprs that can match non-id characters to behave in a reasonable way
	# Note there are subtle semantic differences between positive and negative
	# lookaheads/lookbehinds.  Primarily, negative versions can match end of strings.
	return '(?:(?<!\w)|(?=\W))(?:%s)(?:(?!\w)|(?<=\W))' % (s,)

if __name__ == '__main__':
	try:
		pass
		#import psyco
		#psyco.full()
	except ImportError:
		pass


	parser = buildParser()
	options, args = parser.parse_args()

	if options.imports:
		args.insert(0, "^\s*(import|from)\s")

	matchText = True
	if len(args) < 1 and len(options.replaces) < 1:
		matchText = False

	parser.destroy()


	flags = 0
	if options.insensitive: flags |= re.I

	# Build the regular expressions.

	print

	fileFilters = []

	# Match the filetype
	if not options.filetypes:
		# default filetype
		options.filetypes.append('py')

	if len(options.filetypes) > 1:
		tf = '\.(%s)$' % '|'.join(options.filetypes)
	else:
		tf = '\.%s$' % options.filetypes[0]

	print "+file: %s" % tf
	fileFilters.append(re.compile(tf, flags))


	# Match the full file name
	for ff in options.filefilters:
		print "+file: %s" % ff
		fileFilters.append(re.compile(ff, flags))

	# Antimatch the full file name
	excludeFileFilters = []
	for ff in options.excludefilefilters:
		print "-file: %s" % ff
		excludeFileFilters.append(re.compile(ff, flags))

	# Match the text
	textFilters = []
	for tf in args:
		print "+text: %s" % tf
		textFilters.append(re.compile(tf, flags))

	# Antimatch the text
	excludeFilters = []
	for ef in options.excludes:
		print "-text: %s" % ef
		excludeFilters.append(re.compile(ef, flags))

	# Replace the text
	replaceFilters = []
	for rf in options.replaces:
		print "!repl: %s -> %s" % rf
		replaceFilters.append((re.compile(rf[0], flags), rf[1]))

	print

	directoryName = options.directory

	# Search the files.
	sg = StandardGrep(matchText)
	sg.walk(directoryName, sg.displayMatch)
