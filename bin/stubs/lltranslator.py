from util.typedispatch import *
from programIR.python import ast
from programIR.python import program

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

	def __init__(self, extractor, func):
		self.extractor = extractor
		self.func = func

		self.defn      = {}

		self.specialGlobals = set(('allocate',
			'load',      'store',      'check',
			'loadAttr',  'storeAttr',  'checkAttr',
			'loadDict',  'storeDict',  'checkDict',
			'loadArray', 'storeArray', 'checkArray'))

	def resolveGlobal(self, name):
		glbls = self.func.func_globals

		if name in glbls:
			pyobj = glbls[name]
		else:
			pyobj = __builtins__[name]

		obj = self.extractor.getObject(pyobj)
		e = ast.Existing(obj)
		self.defn[e] = e
		return e

	@defaultdispatch
	def default(self, node):
		assert False, repr(node)

	@dispatch(type(None), str)
	def visitLeaf(self, node):
		return node

	@dispatch(ast.Local)
	def visitLocal(self, node):
		defn = self.defn.get(node)
		if isinstance(defn, ast.Existing):
			return defn
		return node

	@dispatch(ast.Existing)
	def visitExisting(self, node):
		self.defn[node] = node
		return node

	@dispatch(ast.GetGlobal)
	def visitGetGlobal(self, node):
		node = allChildren(self, node)

		namedefn = self.defn[node.name]
		assert isinstance(namedefn, ast.Existing)
		name = namedefn.object.pyobj

		if name in self.specialGlobals:
			return name
		else:
			return self.resolveGlobal(name)


	@dispatch(ast.Call)
	def visitCall(self, node):
		node = allChildren(self, node)
		original = node

		if node.expr in self.defn:
			defn = self.defn[node.expr]
			if defn in self.specialGlobals:
				if defn is 'allocate':
					checkCallArgs(node, 1)
					node = ast.Allocate(node.args[0])
				elif defn is 'load':
					checkCallArgs(node, 2)
					node = ast.Load(node.args[0], 'LowLevel', node.args[1])
				elif defn is 'store':
					checkCallArgs(node, 3)
					node = ast.Store(node.args[0], 'LowLevel', node.args[1], node.args[2])
				elif defn is 'check':
					checkCallArgs(node, 2)
					node = ast.Check(node.args[0], 'LowLevel', node.args[1])
				elif defn is 'loadAttr':
					checkCallArgs(node, 2)
					node = ast.Load(node.args[0], 'Attribute', node.args[1])
				elif defn is 'storeAttr':
					checkCallArgs(node, 3)
					node = ast.Store(node.args[0], 'Attribute', node.args[1], node.args[2])
				elif defn is 'checkAttr':
					checkCallArgs(node, 2)
					node = ast.Check(node.args[0], 'Attribute', node.args[1])
				elif defn is 'loadDict':
					checkCallArgs(node, 2)
					node = ast.Load(node.args[0], 'Dictionary', node.args[1])
				elif defn is 'storeDict':
					checkCallArgs(node, 3)
					node = ast.Store(node.args[0], 'Dictionary', node.args[1], node.args[2])
				elif defn is 'checkDict':
					checkCallArgs(node, 2)
					node = ast.Check(node.args[0], 'Dictionary', node.args[1])
				elif defn is 'loadArray':
					checkCallArgs(node, 2)
					node = ast.Load(node.args[0], 'Array', node.args[1])
				elif defn is 'storeArray':
					checkCallArgs(node, 3)
					node = ast.Store(node.args[0], 'Array', node.args[1], node.args[2])
				elif defn is 'checkArray':
					checkCallArgs(node, 2)
					node = ast.Check(node.args[0], 'Array', node.args[1])
				else:
					assert False, defn
			elif isinstance(defn, ast.Existing):
				# Try to make it a direct call.
				# Not always possible, depends on the order of declaration.
				code = self.extractor.getCall(defn.object)
				if code:
					node = ast.DirectCall(code, node.expr, node.args, node.kwds, node.vargs, node.kargs)

		node.annotation = original.annotation
		return node

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		expr = self(node.expr)
		assert not isinstance(expr, ast.Store), "Must discard stores."

		self.defn[node.lcl] = expr

		if expr not in self.specialGlobals:
			node.expr = expr
			return node
		else:
			return ()


	@dispatch(ast.Discard)
	def visitDiscard(self, node):
		expr = self(node.expr)
		if isinstance(expr, ast.Store): return expr

		if expr not in self.specialGlobals:
			node.expr = expr
			return node
		else:
			return ()

	@dispatch(ast.ConvertToBool)
	def visitConvertToBool(self, node):
		defn = self.defn.get(node.expr)
		if isinstance(defn, (ast.Check, ast.ConvertToBool, ast.Not)):
			# It will be a boolean, so don't bother converting...
			return node.expr
		else:
			return allChildren(self, node)

	@dispatch(ast.BinaryOp, ast.GetAttr)
	def visitExpr(self, node):
		return allChildren(self, node)

	@dispatch(ast.Switch)
	def visitSwitch(self, node):
		cond = self(node.condition)
		self.defn.clear()

		t = self(node.t)
		self.defn.clear()

		f = self(node.f)
		self.defn.clear()


		result = ast.Switch(cond, t, f)
		result.annotation = node.annotation
		return result

	@dispatch(ast.Suite, list, tuple, ast.Condition, ast.Return)
	def visitOK(self, node):
		return allChildren(self, node)

	def process(self, node):
		node.ast = self(node.ast)
		optimization.simplify.simplify(self.extractor, None, node)
		#astpprint.pprint(node)
		return node

def translate(extractor, func, code):
	llt = LLTranslator(extractor, func)
	return llt.process(code)