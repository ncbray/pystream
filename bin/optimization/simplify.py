from . import fold
from . import dce
from dataflow.base import InternalError

from cStringIO import StringIO
from language.python.simplecodegen import SimpleCodeGen

from language.python import ast

#
# Leverages type inference to eliminate indirect calls,
# fold and propigate constants, etc.
# In effect, this pass attempts to "de-dynamicize" Python
#


def evaluateCode(compiler, node):
	assert node.isCode(), type(node)

	try:
		fold.evaluateCode(compiler, node)

		# Can't process arbitrary abstract code nodes.
		if node.isStandardCode():
			dce.evaluateCode(compiler, node)

	except InternalError:
		print
		print "#######################################"
		print "Function generated an internal error..."
		print "#######################################"
		sio = StringIO()
		scg = SimpleCodeGen(sio)
		scg.process(node)
		print sio.getvalue()
		raise


def evaluate(compiler):
	with compiler.console.scope('simplify'):
		for code in compiler.liveCode:
			if not code.annotation.descriptive:
				evaluateCode(compiler, code)
