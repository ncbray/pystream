from __future__ import absolute_import

from . import parser
from . import optimizer

def parseAlgorithim(algorithim):
	ast = parser.astFromAlgorithim(algorithim)
	ast = optimizer.simplifyAST(ast)
	return ast
