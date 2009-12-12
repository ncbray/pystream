from util.xcollections import namedtuple

def originString(origin):
	if origin is None: return "<unknown origin>"

        if origin.filename:
                s = "File \"%s\"" % origin.filename
        else:
                s = ''

	
	if origin.lineno is None or origin.lineno < 0:
                needComma = False
	elif origin.col is None or origin.col < 0:
                if s: s += ', '
		s = "%sline %d" % (s, origin.lineno)
                needComma = True
	else:
                if s: s += ', '
		s = "%sline %d:%d" % (s, origin.lineno, origin.col)
                needComma = True

        if origin.name:
                if s:
                        if needComma:
                                s += ', '
                        else:
                                s += ' '
                s = "%sin %s" % (s, origin.name)

        return s

Origin = namedtuple('Origin', 'name filename lineno col', dict(originString=originString))
