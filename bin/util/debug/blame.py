import sys
import dis

def lineForInstruction(code, instruction):
	line = 1

	for i, l in dis.findlinestarts(code):
		if i > instruction: break
		line = l

	return line


def traceBlame(offset, count):
	lines = []

	for i in range(count):
		try:
			caller   = sys._getframe(offset+(count-i-1))
			name	 = caller.f_code.co_name

			# inaccurate when psyco is used?
			if hasattr(caller, 'f_lasti'):
				lineno   = lineForInstruction(caller.f_code, caller.f_lasti)
			else:
				lineno   = caller.f_lineno

			filename = caller.f_code.co_filename
			del caller # Destroy a circular reference

			lines.append("%s:%d in %s" % (filename, lineno, name))
		except:
			pass

	return tuple(lines)
