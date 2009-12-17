import sys

def traceBlame(offset, count):
	lines = []
	for i in range(count):
		try:
			caller   = sys._getframe(offset+(count-i-1))
			name	 = caller.f_code.co_name
			lineno   = caller.f_lineno
			filename = caller.f_code.co_filename
			del caller # Destroy a circular reference

			lines.append("%s:%d in %s" % (filename, lineno, name))
		except:
                        pass

	return tuple(lines)
