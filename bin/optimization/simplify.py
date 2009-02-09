from fold import foldConstants
from dce import dce
from dataflow.base import InternalError

from cStringIO import StringIO
from common.simplecodegen import SimpleCodeGen

from programIR.python import ast

#
# Leverages type inference to eliminate indirect calls,
# fold and propigate constants, etc.
# In effect, this pass attempts to "de-dynamicize" Python
#


def simplify(extractor, adb, node):
	assert isinstance(node, ast.Code), type(node)
	try:
		node = foldConstants(extractor, adb, node)
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
