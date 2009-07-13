import os.path

if __name__ == '__main__':
	dn = 'bin'
	
	for path, dirs, files in os.walk(dn):
		fileset = set(files)
		compiled   = 0
		uncompiled = 0
		
		for fn in files:
			root, ext = os.path.splitext(fn)

			if ext == '.py':
				pyc = root + '.pyc'
				pyo = root + '.pyo'
				if pyc not in fileset and pyo not in fileset:
					print "Uncompiled:\t%s" % os.path.join(path, fn)
					uncompiled += 1
					
			elif ext == '.pyc' or ext == '.pyo':
				py = root + '.py'
				if py not in fileset:
					print "No source:\t%s" % os.path.join(path, fn)
				compiled += 1

		if uncompiled and not compiled and not dirs:
			print "Dead directory:\t%s" %  path
