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
