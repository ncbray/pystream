from fold import fold
from dce import dce
from dataflow.base import InternalError

from cStringIO import StringIO
from common.simplecodegen import SimpleCodeGen

#
# Leverages type inference to eliminate indirect calls,
# fold and propigate constants, etc.
# In effect, this pass attempts to "de-dynamicize" Python
#


def simplify(extractor, adb, node):
	try:
		node = fold(extractor, adb, node)
		node = dce(extractor, adb, node)
	except InternalError:
		print
		print "#######################################"
		print "Function generated an internal error..."
		print "#######################################"
		sio = StringIO()
		scg = SimpleCodeGen(sio)
		scg.walk(node)
		print sio.getvalue()
		raise


	return node
