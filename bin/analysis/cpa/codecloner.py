from util.typedispatch import *
from language.python import ast

def createCodeMap(liveCode):
	codeMap = {}
	for code in liveCode:
		# This is a shallow copy.  A deep copy will be done later.
		cloned = code.clone()
		codeMap[code] = cloned
	return codeMap

# Note that this cloner does NOT modify annotations, which means any
# invocation annotations will still point to the uncloned code.
# This is OK, however, as this cloning transform is designed to happen
# right before the annotations are rewritten.
class FunctionCloner(TypeDispatcher):
	def __init__(self, liveCode):
		self.codeMap = createCodeMap(liveCode)

	@dispatch(ast.Local)
	def visitLocal(self, node):
		if not node in self.localMap:
			lcl = node.clone()
			self.localMap[node] = lcl
		else:
			lcl = self.localMap[node]
		return lcl

	@dispatch(ast.Code)
	def visitCode(self, node):
		# We may encounter dead direct calls that specify an uncloned target.
		# Return None in this case.
		return self.codeMap.get(node)

	@dispatch(ast.leafTypes)
	def visitLeaf(self, node):
		return node

	@defaultdispatch
	def default(self, node):
		assert not node.__shared__, type(node)
		result = node.rewriteCloned(self)
		self.opMap[node] = result # TODO this included a lot of non-op junk.
		return result

	def process(self, code):
		self.localMap = {}
		self.opMap   = {}

		newcode = self.codeMap[code]
		newcode.replaceChildren(self)

	def op(self, op):
		return self.opMap[op]

	def lcl(self, lcl):
		return self.localMap[lcl]

	def code(self, code):
		return self.codeMap[code]

# Same interface, no cloning performed.
class NullCloner(object):
	def __init__(self, liveCode):
		pass

	def process(self, code):
		pass

	def op(self, op):
		return op

	def lcl(self, lcl):
		return lcl

	def code(self, code):
		return code
