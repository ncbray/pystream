import util.canonical
import collections

__all__ = ['noMod', 'remapContextual', 'makeContextualAnnotation', 'annotationSet']

noMod = util.canonical.Sentinel('<no mod>')

ContextualAnnotation = collections.namedtuple('ContextualAnnotation', 'merged context')

def annotationSet(data):
	return tuple(sorted(data))

def makeContextualAnnotation(cdata):
	merged = set()
	for data in cdata: merged.update(data)
	return ContextualAnnotation(annotationSet(merged), tuple(cdata))

def remapContextual(cdata, remap, translator=None):
	if cdata is None: return None

	cout  = []

	for i in remap:
		if i >= 0:
			data = cdata[1][i]
			if translator:
				data = annotationSet([translator(item) for item in data])
		else:
			data = ()
		cout.append(data)

	return makeContextualAnnotation(cout)
