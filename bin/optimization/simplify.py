from fold import foldConstants
from dce import dce
from dataflow.base import InternalError

from cStringIO import StringIO
from language.python.simplecodegen import SimpleCodeGen

from language.python import ast

#
# Leverages type inference to eliminate indirect calls,
# fold and propigate constants, etc.
# In effect, this pass attempts to "de-dynamicize" Python
#


def simplify(extractor, db, node):
	assert node.isAbstractCode(), type(node)

	try:
		foldConstants(extractor, db, node)

		# Can't process arbitrary abstract code nodes.
		if node.isStandardCode():
			dce(extractor, node)
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

