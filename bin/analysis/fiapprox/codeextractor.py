from __future__ import absolute_import

from util.visitor import StandardVisitor

from common import opnames

# HACK
import programIR.python.ast as code

from stubs.stubcollector import exports

class CodeExtractor(StandardVisitor):
	def __init__(self, ce, fobj, fast, rootContext):
		self.ce = ce
		self.rootContext = rootContext
		self.functionStack = []

		self.pushFunction(fobj, fast)

		self.created = set()

	def addTuple(self, *args):
		self.ce.addTuple(*args)

	def addSymbol(self, *args):
		self.ce.addSymbol(*args)


	def makeBytecode(self, node):
		self.ce.makeBytecode(self.functionAST(), node, advance=True)

	def pushFunction(self, obj, ast):
		self.functionStack.append((obj, ast))

	def popFunction(self):
		self.functionStack.pop()

	def functionOBJ(self):
		return self.functionStack[-1][0]

	def functionAST(self):
		return self.functionStack[-1][1]



	#### Direct Calls ###

	def visitBuildList(self, node):
		self.makeBytecode(node)
		self.addTuple('directCall', node, exports['buildList'])

		args = [self.visit(arg) for arg in node.args]
		self.ce.setArgs(node, args)

		return node

	def visitBuildTuple(self, node):
		self.makeBytecode(node)
		self.addTuple('directCall', node, exports['buildTuple'])

		args = [self.visit(arg) for arg in node.args]
		self.ce.setArgs(node, args)

		return node

	def visitBuildMap(self, node):
		self.makeBytecode(node)
		self.addTuple('directCall', node, exports['buildMap'])
		return node


	def visitConvertToBool(self, node):
		self.makeBytecode(node)
		self.addTuple('directCall', node, exports['convertToBool'])

		self.ce.setArgs(node, [self.visit(node.expr)])

		return node

	def visitNot(self, node):
		self.makeBytecode(node)
		self.addTuple('directCall', node, 'null') # HACK
		self.ce.setArgs(node, [self.visit(node.expr)])
		return node


	def visitImport(self, node):
		self.makeBytecode(node)
		self.addTuple('directCall', node, 'null') # HACK
		return node

	def visitUnpackSequence(self, node):
		self.makeBytecode(node)
		self.addTuple('directCall', node, exports['unpackSequence']) # HACK

		self.ce.setArgs(node, [self.visit(node.expr)])

		for i, target in enumerate(node.targets):
			target = self.visit(target)
			self.addTuple('opResult', target, i, node)


	def visitPrint(self, node):
		self.makeBytecode(node)
		self.addTuple('directCall', node, 'null') # HACK

		# HACK incomplete

##		if node.target:
##			target = self.visit(node.target)
##		else:
##			target = self.ce.extractor.getObject(None)
##
##		if node.expr:
##			expr = self.visit(node.expr)
##		else:
##			expr = self.ce.extractor.getObject(None)
##
##		self.ce.setArgs(node, [target, expr])

		return node


	def visitGetSlice(self, node):
		self.makeBytecode(node)
		self.addTuple('directCall', node, 'null') # HACK

		args = [self.visit(node.expr)]
		if node.start: args.append(self.visit(node.start))
		if node.stop: args.append(self.visit(node.stop))
		if node.step:  args.append(self.visit(node.step))

		self.ce.setArgs(node, args)

		return node


	def visitSetSlice(self, node):
		# HACK

		self.makeBytecode(node)
		self.addTuple('directCall', node, 'null') # HACK

		args = [self.visit(node.expr)]
		if node.start: args.append(self.visit(node.start))
		if node.stop: args.append(self.visit(node.stop))
		if node.step:  args.append(self.visit(node.step))
		args.append(self.visit(node.value))

		self.ce.setArgs(node, args)



	def visitDeleteSlice(self, node):
		self.makeBytecode(node)
		self.addTuple('directCall', node, 'null') # HACK
		
		args = [self.visit(node.expr)]
		if node.start: args.append(self.visit(node.start))
		if node.stop: args.append(self.visit(node.stop))
		if node.step:  args.append(self.visit(node.step))

		self.ce.setArgs(node, args)

		return node


	### ??? ###


	def visitShortCircutAnd(self, node):
		self.makeBytecode(node)
		# HACK
		for term in node.terms:
			self.visit(term)

		return node
		

	def visitShortCircutOr(self, node):
		self.makeBytecode(node)

		# HACK
		for term in node.terms:
			self.visit(term)

		return node


	### ??? ###

	def visitReturn(self, node):
		lcl = self.visit(node.expr)
		self.addTuple('returns', self.functionAST(), 0, lcl)


	def visitRaise(self, node):
		# HACK
		# TODO implement?
		pass

	def visitBreak(self, node):
		pass

	def visitContinue(self, node):
		pass

	def visitYield(self, node):
		self.makeBytecode(node)
		# HACK
		# TODO implement?

		return node

	def visitLocal(self, node):
		if not node in self.created:
			self.ce.makeVariable(self.functionAST(), node)
			self.created.add(node)
		return node

	def visitExisting(self, node):
		return node.object

	def visitGetCellDeref(self, node):
		self.makeBytecode(node)

		# HACK
		# TODO implement

		return node

	def visitSetCellDeref(self, node):
		# HACK
		# TODO implement

		pass

	def visitGetAttr(self, node):
		
		expr = self.visit(node.expr)
		name = self.visit(node.name)

		self.makeBytecode(node)
		self.addTuple('directCall', node, exports['interpreter_getattribute'])
		self.ce.setArgs(node, [expr, name])
		return node


		return node

	def visitSetAttr(self, node):
		expr = self.visit(node.expr)
		name = self.visit(node.name)
		value = self.visit(node.value)

		self.makeBytecode(node)
		self.addTuple('directCall', node, exports['interpreter_setattr'])
		self.ce.setArgs(node, [expr, name, value])

	def visitDeleteAttr(self, node):
		
		expr = self.visit(node.expr)
		name = self.visit(node.name)

		self.makeBytecode(node)
		self.addTuple('directCall', node, 'null')
		self.ce.setArgs(node, [expr, name])


	def visitGetSubscript(self, node):
		
		expr = self.visit(node.expr)
		subscript = self.visit(node.subscript)

		self.makeBytecode(node)
		self.addTuple('directCall', node, 'null')
		self.ce.setArgs(node, [expr, subscript])

		return node

	def visitSetSubscript(self, node):
		expr = self.visit(node.expr)
		subscript = self.visit(node.subscript)
		value = self.visit(node.value)

		self.makeBytecode(node)
		self.addTuple('directCall', node, 'null')
		self.ce.setArgs(node, [expr, subscript, value])
		

	def visitDeleteSubscript(self, node):
		expr = self.visit(node.expr)
		subscript = self.visit(node.subscript)


		self.makeBytecode(node)
		self.addTuple('directCall', node, 'null')
		self.ce.setArgs(node, [expr, subscript])



	def visitGetGlobal(self, node):
		self.makeBytecode(node)
		name = self.visit(node.name)

		self.addTuple('directCall', node, exports['interpreterLoadGlobal'])
		self.ce.setArgs(node, [self.functionOBJ(), name])
		
		return node

	def visitSetGlobal(self, node):
		self.makeBytecode(node)
		name = self.visit(node.name)
		value = self.visit(node.value)

		self.addTuple('directCall', node, exports['interpreterStoreGlobal'])
		self.ce.setArgs(node, [self.functionOBJ(), name, value])

	def visitGetIter(self, node):
		self.makeBytecode(node)
		self.addTuple('directCall', node, exports['interpreter_iter'])
		self.ce.setArgs(node, [self.visit(node.expr)])
		return node


	def visitBinaryOp(self, node):
		
		l = self.visit(node.left)
		r = self.visit(node.right)

		# TODO convert to a direct call.
		#self.addTuple('binaryOp', node, node.op, l, r)


		# HACK skip in/is operations.
		if node.op in opnames.mustHaveSpace:
			self.makeBytecode(node)
			return node

		
		if node.op in opnames.inplaceOps:
			opname = opnames.inplace[node.op[:-1]]
		else:
			opname = opnames.forward[node.op]
			

		self.makeBytecode(node)
		self.addTuple('directCall', node, exports['interpreter%s' % opname])
		self.ce.setArgs(node, [l, r])

		return node



	def visitUnaryPrefixOp(self, node):
		
		expr = self.visit(node.expr)

		opname = opnames.unaryPrefixLUT[node.op]

		self.makeBytecode(node)
		self.addTuple('directCall', node, exports['interpreter%s' % opname])		
		self.ce.setArgs(node, [expr])

		return node


	def visitCall(self, node):
		# HACK
##		assert not node.kwds
##		assert not node.vargs
##		assert not node.kargs
		
		self.makeBytecode(node)

		expr = self.visit(node.expr)
		#self.addTuple('operation', node, 'Call', expr)
		self.addTuple('call', node, expr)

		self.ce.setArgs(node, [self.visit(arg) for arg in node.args])
		
		return node

	def visitAssign(self, node):
		expr = self.visit(node.expr)
		lcl = self.visit(node.lcl)

		if isinstance(node.expr, code.Local):
			# lcl = lcl
			# 'merge' is converted into an assignment.
			self.addTuple('merge', node.lcl, expr)
		elif isinstance(node.expr, code.Existing):
			# lcl = constant
			# Every constant has a "phantom local" that holds it.
			# Phantom locals are equivilent to globals, in C.
			self.addTuple('varPoint0', lcl, (self.rootContext, expr))
		else:
			# lcl = operation
			assert expr, type(node.expr)
			self.addTuple('opResult', lcl, 0, expr)


	def visitDiscard(self, node):
		self.visit(node.expr)

	def visitDelete(self, node):
		# Not useful for flow-insensitive analysis
		pass

	def visitSuite(self, node):
		for block in node.blocks:
			self.visit(block)

	def visitCondition(self, node):
		self.visit(node.preamble)
		self.visit(node.conditional)

	def visitSwitch(self, node):
		self.visit(node.condition)
		self.visit(node.t)
		self.visit(node.f)

	def visitExceptionHandler(self, node):
		self.visit(node.preamble)
		self.visit(node.type)

		# HACK, should pipe in exception value?
		if node.value:
			self.visit(node.value)
			
		self.visit(node.body)

	def visitTryExceptFinally(self, node):
		self.visit(node.body)
		if node.else_: self.visit(node.else_)

		for handler in node.handlers:
			self.visit(handler)

		if node.defaultHandler:
			self.visit(node.defaultHandler)

		if node.finally_:
			self.visit(node.finally_)


	def visitWhile(self, node):
		self.visit(node.condition)
		self.visit(node.body)
		if node.else_: self.visit(node.else_)

	def visitFor(self, node):
		iterator = self.visit(node.iterator)


		self.makeBytecode(node)
		self.addTuple('directCall', node, exports['interpreter_next'])
		self.ce.setArgs(node, [iterator])

		self.addTuple('opResult', self.visit(node.index), 0, node)
		
		self.visit(node.body)
		if node.else_: self.visit(node.else_)

	def visitCode(self, node):
		func = self.functionAST()

		for i, param in enumerate(node.parameters):
			assert isinstance(param, code.Local)
			param = self.visit(param)
			self.addTuple('formalParam', func, i, param)		

		# HACK
##		assert not node.vargs
##		assert not node.kargs

		self.visit(node.ast)

	def visitFunction(self, node):
		self.visit(node.code)


	def visitMakeFunction(self, node):
		self.makeBytecode(node)

		self.addSymbol('function', node.code)

		# HACK
		# TODO defaults
		# TODO cells

		#assert False, "Untested: what object/ast pair should be pushed?"
		# HACK refers the the globals of the outer function?
		self.pushFunction(self.functionOBJ(), node.code)
		self.visit(node.code)
		self.popFunction()

		return node
