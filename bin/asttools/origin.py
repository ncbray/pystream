from util.xcollections import namedtuple

def originString(origin):
	if origin is None:
		return "<unknown origin>"
	elif origin.lineno is None or origin.lineno < 0:
		return "File \"%s\" in %s" % (origin.filename, origin.name)
	elif origin.col is None or origin.col < 0:
		return "File \"%s\", line %d, in %s" % (origin.filename, origin.lineno, origin.name)
	else:
		return "File \"%s\", line %d:%d, in %s" % (origin.filename, origin.lineno, origin.col, origin.name)

Origin = namedtuple('Origin', 'name filename lineno col', dict(originString=originString))
