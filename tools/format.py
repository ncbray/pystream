# Standardizes whitespace formatting for all the Python source files in a directory

import os.path
import optparse
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
	group.add_option('-n', dest='dryrun', action='store_true', default=False, help="modifications are not written to disk")

	group.add_option('--multiline-ok', dest='multiline_ok', action='store_true', default=False, help="don't abort if a multiline string is found")

	parser.add_option_group(group)

	group = optparse.OptionGroup(parser, "File Filters")
	group.add_option('-f', dest='filefilters', action='append', default=[], help="matches the file name", metavar="FILTER")
	group.add_option('-g', dest='excludefilefilters', action='append', default=[], help="excludes file name", metavar="FILTER")
	parser.add_option_group(group)

	return parser

possibleMultilineString = re.compile('"""|\'\'\'')

def countSpaces(line):
	count = 0
	for c in line:
		if c == ' ':
			count += 1
		else:
			break
	return count

def handleFile(fn):
	f = open(fn)

	spacetabs = False
	spacetabRanges = []
	spacetabStart = -1
	spacetabEnd = -1
	blockEnd = -1

	def logSpacetabs():
		if spacetabStart != -1:
			if spacetabStart == spacetabEnd:
				spacetabRanges.append(str(spacetabStart))
			else:
				spacetabRanges.append("%d-%d" % (spacetabStart, spacetabEnd))

	changed   = False

	lines = []

	eolMod = 0

	title = False

	spaceDist = {}

	multiline = False

	for line in f:
		if possibleMultilineString.search(line):
			multiline = True

		# Note: this implicitly fixes inconsistent newline characters.
		newline = line.rstrip() + '\n'

		lineNo = len(lines)+1

		if line != newline:
			if not title:
				print fn
				title = True
			print "EOL MOD", len(lines)+1, repr(line)
			eolMod += 1
			changed = True
			line = newline

		if line[0] == ' ':
			spacetabs = True
			count = countSpaces(line)
			spaceDist[count] = spaceDist.get(count, 0) + 1
			if blockEnd + 1 != lineNo:
				logSpacetabs()
				spacetabStart = lineNo
			spacetabEnd = lineNo
			blockEnd = lineNo
		elif line[0] != '\t':
			if blockEnd + 1 == lineNo:
				blockEnd = lineNo # Extend blocks past empty lines.


		lines.append(line)

	logSpacetabs()

	# Remove newline at the end of the file.
	eofLines = False
	while lines and lines[-1] == '\n':
		lines.pop()
		changed = True
		eofLines = True

	if eofLines:
		if not title:
			print fn
			title = True
		print "EOF NEWLINES"

	if spacetabs:
		if not title:
			print fn
			title = True
		counts = list(spaceDist.keys())
		counts.sort()

		clean8 = all([c%8==0 for c in counts])
		clean4 = all([c%4==0 for c in counts])

		if clean8:
			size = '8?'
		elif clean4:
			size = '4?'
		else:
			size = 'wierd'

		print "WARNING: spacetabs (%s)" % size, counts
		print "lines", ",".join(spacetabRanges)

	f.close()

	if changed and not options.dryrun:
		if multiline and not options.multiline_ok:
			if not title:
				print fn
				title = True
			print "ABORTING CHANGES - possible multiline string"
			print
			return

		if changed:
			f = open(fn, 'w')
			for line in lines:
				f.write(line)
			f.close()

	if title:
		print

def run(dir):
	for path, dirs, files in os.walk(dir):
		for fn in files:
			base, ext = os.path.splitext(fn)
			if ext == '.py':
				fullname = os.path.join(path, fn)
				handleFile(fullname)


parser = buildParser()
options, args = parser.parse_args()

run(options.directory)
