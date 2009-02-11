from util.typedispatch import *
from programIR.python import ast
from programIR.python import program
from util import xform

# HACK
from common import astpprint

import optimization.simplify

def checkCallArgs(node, count):
	assert len(node.args) == count, node
	assert not node.kwds, node
	assert not node.vargs, node
	assert not node.kargs, node

class LLTranslator(object):
	__metaclass__ = typedispatcher

	def __init__(self, extractor):
		self.extractor = extractor
		self.defn      = {}

		self.specialGlobals = set(('allocate', 'load', 'store', 'check', 'loadDict', 'storeDict', 'checkDict'))

	def resolveGlobal(self, name):
		pyobj = __builtins__[name]
		obj = self.extractor.getObject(pyobj)
		return ast.Existing(obj)

	@defaultdispatch
	def default(self, node):
		assert False, repr(node)

	@dispatch(type(None))
	def visitLeaf(self, node):
		return node

	@dispatch(ast.Local)
	def visitLocal(self, node):
		if node in self.defn and isinstance(self.defn[node], ast.Existing):
			return self.defn[node]
		return node

	@dispatch(ast.Existing)
	def visitExisting(self, node):
		self.defn[node] = node
		return node

	@dispatch(ast.GetGlobal)
	def visitGetGlobal(self, node):
		node = xform.allChildren(self, node)

		namedefn = self.defn[node.name]
		assert isinstance(namedefn, ast.Existing)
		name = namedefn.object.pyobj

		if name in self.specialGlobals:
			return name
		else:
			glbl = self.resolveGlobal(name)
			return glbl


	@dispatch(ast.Call)
	def visitCall(self, node):
		node = xform.allChildren(self, node)
		if node.expr in self.defn:
			defn = self.defn[node.expr]
			if defn in self.specialGlobals:
				if defn is 'allocate':
					checkCallArgs(node, 1)
					node = ast.Allocate(node.args[0])
				elif defn is 'load':
					checkCallArgs(node, 2)
					node = ast.Load(node.args[0], 'LowLevel', node.args[1])
				elif defn is 'check':
					checkCallArgs(node, 2)
					node = ast.Check(node.args[0], 'LowLevel', node.args[1])
				elif defn is 'loadDict':
					checkCallArgs(node, 2)
					node = ast.Load(node.args[0], 'Dictionary', node.args[1])
				elif defn is 'checkDict':
					checkCallArgs(node, 2)
					node = ast.Check(node.args[0], 'Dictionary', node.args[1])
				else:
					assert False
		return node

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		expr = self(node.expr)


		if node.lcl in self.defn:
			self.defn[node.lcl] = None
		else:
			self.defn[node.lcl] = expr

		if expr not in self.specialGlobals:
			node.expr = expr
			return node
		else:
			return ()

	@dispatch(ast.ConvertToBool)
	def visitConvertToBool(self, node):
		# TODO eliminate unessisary?
		return xform.allChildren(self, node)

	@dispatch(ast.Suite, list, tuple, ast.Switch, ast.Condition, ast.Return)
	def visitOK(self, node):
		return xform.allChildren(self, node)

	def process(self, node):
		node.ast = self(node.ast)
		optimization.simplify.simplify(self.extractor, None, node)
		#astpprint.pprint(node)
		return node

def translate(extractor, code):
	llt = LLTranslator(extractor)
	return llt.process(code)