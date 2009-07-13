from asttools.transform import *
from language.python import ast
from language.python import program

# HACK for debugging
from asttools import astpprint

import optimization.simplify

def checkCallArgs(node, count):
	assert len(node.args) == count, node
	assert not node.kwds, node
	assert not node.vargs, node
	assert not node.kargs, node

class LLTranslator(TypeDispatcher):
	def __init__(self, compiler, func):
		self.compiler = compiler
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
		elif name in self.compiler.extractor.nameLUT:
			pyobj = self.compiler.extractor.nameLUT[name]
		else:
			pyobj = __builtins__[name]

		obj = self.compiler.extractor.getObject(pyobj)
		e = ast.Existing(obj)
		self.defn[e] = e
		return e

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

	def translateName(self, name):
		if name is 'internal_self':
			assert self.code.codeparameters.selfparam
			return self.code.codeparameters.selfparam
		elif name in self.specialGlobals:
			return name
		else:
			return self.resolveGlobal(name)


	@dispatch(ast.GetGlobal)
	def visitGetGlobal(self, node):
		node = allChildren(self, node)
		namedefn = self.defn[node.name]
		assert isinstance(namedefn, ast.Existing)
		name = namedefn.object.pyobj
		return self.translateName(name)

	@dispatch(ast.GetCellDeref)
	def visitGetGellDeref(self, node):
		name = node.cell.name
		return self.translateName(name)


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
				code = self.compiler.extractor.getCall(defn.object)
				if code:
					node = ast.DirectCall(code, node.expr, node.args, node.kwds, node.vargs, node.kargs)

		node.annotation = original.annotation
		return node

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		expr = self(node.expr)
		assert not isinstance(expr, ast.Store), "Must discard stores."

		# A little strange, but it works because there will only be one target in the cases we care about.
		for lcl in node.lcls:
			self.defn[lcl] = expr

		if expr not in self.specialGlobals:
			if node.expr == expr:
				return node
			else:
				return ast.Assign(expr, node.lcls)
		else:
			return ()


	@dispatch(ast.Discard)
	def visitDiscard(self, node):
		expr = self(node.expr)
		if isinstance(expr, ast.Store): return expr

		if expr not in self.specialGlobals:
			if node.expr == expr:
				return node
			else:
				return ast.Discard(expr)
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

	@dispatch(ast.BinaryOp, ast.GetAttr, ast.GetSubscript, ast.BuildTuple)
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

	@dispatch(ast.Return)
	def visitReturn(self, node):
		if len(node.exprs) == 1:
			defn = self.defn.get(node.exprs[0])
			if isinstance(defn, ast.BuildTuple):
				# HACK this transformation can be unsound if any of the arguments to the BuildTuple have been redefined.
				# HACK this may create unwanted multi-returns.
				# HACK no guarentee the number of return args is consistant.
				newexprs = [self(arg) for arg in defn.args]
				self.setNumReturns(len(newexprs))
				return ast.Return(newexprs)

		self.setNumReturns(len(node.exprs))
		return allChildren(self, node)

	def setNumReturns(self, num):
		if self.numReturns is None:
			self.numReturns = num

			p = self.code.codeparameters
			if num != len(p.returnparams):
				returnparams = [ast.Local('internal_return_%d' % i) for i in range(num)]
				self.code.codeparameters = ast.CodeParameters(p.selfparam, p.params, p.paramnames, p.vparam, p.kparam, returnparams)

		else:
			assert num == self.numReturns

	@dispatch(ast.Suite, list, tuple, ast.Condition)
	def visitOK(self, node):
		return allChildren(self, node)

	def process(self, node):
		self.numReturns = None

		self.code = node
		node.ast = self(node.ast)
		self.code = None

		optimization.simplify.evaluateCode(self.compiler, node)

		#astpprint.pprint(node)
		return node

def translate(compiler, func, code):
	llt = LLTranslator(compiler, func)
	return llt.process(code)