from util.visitor import StandardVisitor
from language.python.ast import isPythonAST
from language.python.program import AbstractObject, Object


valueTypes = (str, int, float, long, type(None))

class ASTVisitor(StandardVisitor):
	def default(self, node):
		if isinstance(node, valueTypes):
			pass
		elif isinstance(node, (tuple, list)):
			for child in node:
				self.visit(child)
		else:
			for child in node.children():
				self.visit(child)	

# Constant folding can generate constants that are only visible from the code.
# Search the code for constants.
# This visitor is generic enough it can handle both high- and low-level ASTs
class ConstantFinder(ASTVisitor):
	def __init__(self):
		self.constants = set()

	def visitExisting(self, node):
		assert isinstance(node.object, AbstractObject)
		self.constants.add(node.object)

def findCodeReferencedObjects(functions, entryPoints):
	cf = ConstantFinder()

	for func in functions:
		cf.walk(func)

	codeReferenced = cf.constants

	for func, args in entryPoints:
		codeReferenced.add(func)
		codeReferenced.update(args)


	return codeReferenced
