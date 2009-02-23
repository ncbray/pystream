from __future__ import absolute_import

from tests.shape.shape_base import *

class TestSimpleCase(TestCompoundConstraintBase):
	def shapeSetUp(self):
		# Splice example from paper
		x, self.xSlot, self.xExpr  = self.makeLocalObjs('x')
		y, self.ySlot, self.yExpr  = self.makeLocalObjs('y')
		z, self.zSlot, self.zExpr  = self.makeLocalObjs('z')
		t, self.tSlot, self.tExpr  = self.makeLocalObjs('t')
		q, self.qSlot, self.qExpr  = self.makeLocalObjs('q')
		ret, self.retSlot, self.retExpr  = self.makeLocalObjs('internal_return')

		self.nSlot  = self.sys.canonical.fieldSlot(None, ('LowLevel', self.extractor.getObject('n')))

		self.xRef   = self.refs(self.xSlot)
		self.yRef   = self.refs(self.ySlot)
		self.retRef = self.refs(self.retSlot)

		self.nRef  = self.refs(self.nSlot)
		self.n2Ref = self.refs(self.nSlot, self.nSlot)
		self.n3Ref = self.refs(self.nSlot, self.nSlot, self.nSlot)

		self.p    = [self.parameterSlot(i) for i in range(2)]
		self.pRef = [self.refs(slot) for slot in self.p]

		# t = x
		# x = t.n
		# q = y.n
		# t.n = q
		# y.n = t
		# y = t.n

		# HACK should really be doing a convertToBool?
		cond = ast.Condition(ast.Suite([]), x)

		body = ast.Suite([
			ast.Assign(x, t),
			ast.Assign(ast.Load(t, 'LowLevel', self.existing('n')), x),
			ast.Assign(ast.Load(y, 'LowLevel', self.existing('n')), q),
			ast.Store(t, 'LowLevel', self.existing('n'), q),
			ast.Delete(q),
			ast.Store(y, 'LowLevel', self.existing('n'), t),
			ast.Assign(ast.Load(t, 'LowLevel', self.existing('n')), y),
			])

		else_ = ast.Suite([])

		loop = ast.While(cond, body, else_)

		self.body = ast.Suite([
			ast.Assign(y, z),
			loop,
			ast.Return(z)
			])


		self.code = ast.Code('test', None, [x, y], ['x', 'y'], None, None, ret, self.body)

		a, self.aSlot, self.aExpr  = self.makeLocalObjs('a')
		b, self.bSlot, self.bExpr  = self.makeLocalObjs('b')
		c, self.cSlot, self.cExpr  = self.makeLocalObjs('c')

		self.aRef  = self.refs(self.aSlot)
		self.bRef  = self.refs(self.bSlot)
		self.cRef  = self.refs(self.cSlot)
		self.bcRef = self.refs(self.bSlot, self.cSlot)

		self.anRef = self.refs(self.aSlot, self.nSlot)

		dc = ast.DirectCall(self.code, None, [a,b], [], None, None)
		self.caller = ast.Suite([
			ast.Assign(dc, c),
			])

		invocation = (self.caller, dc, self.code)


		self.context = None
		self.cs = True

		# Make a dummy invocation
		self.db.addInvocation(self.caller, self.context, dc, self.code, self.context)

		self.funcInput,  self.funcOutput   = self.makeConstraints(self.code)
		self.callerInput, self.callerOutput = self.makeConstraints(self.caller)

		self.setInOut(self.callerInput, self.callerOutput)

	def testLocal1(self):
		self.setInOut(self.funcInput, self.funcOutput)

		argument = (self.pRef[0], None, None)
		results = [
			(self.nRef, None, None),
			]
		self.checkTransfer(argument, results)

	def testLocal2(self):
		self.setInOut(self.funcInput, self.funcOutput)

		argument = (self.pRef[1], None, None)
		results = [
			(self.retRef, None, None),
			]
		self.checkTransfer(argument, results)

	def testLocal3(self):
		self.setInOut(self.funcInput, self.funcOutput)

		argument = (self.nRef, None, None)
		results = [
			(self.nRef, None, None),
			]
		self.checkTransfer(argument, results)

		#self.dump()


	def testLocal4(self):
		self.setInOut(self.funcInput, self.funcOutput)

		argument = (self.n2Ref, None, None)
		results = [
			(self.nRef, None, None),
			(self.n2Ref, None, None),
			(self.n3Ref, None, None),
			]
		self.checkTransfer(argument, results)
		#self.dump()

	def testCall1(self):
		argument = (self.aRef, None, None)
		results = [
			(self.aRef, None, None),
			(self.anRef, None, None),
			]
		self.checkTransfer(argument, results)

	def testCall2(self):
		argument = (self.bRef, None, None)
		results = [
			(self.bcRef, None, None),
			]
		self.checkTransfer(argument, results)

	def testCall3(self):
		argument = (self.nRef, None, None)
		results = [
			(self.nRef, None, None),
			]
		self.checkTransfer(argument, results)




class TestCallLoadCase(TestCompoundConstraintBase):
	def shapeSetUp(self):
		x, self.xSlot, self.xExpr  = self.makeLocalObjs('x')
		y, self.ySlot, self.yExpr  = self.makeLocalObjs('y')
		ret, self.retSlot, self.retExpr  = self.makeLocalObjs('internal_return')
		self.nSlot = self.sys.canonical.fieldSlot(None, ('LowLevel', self.extractor.getObject('n')))

		self.xRef   = self.refs(self.xSlot)
		self.retRef = self.refs(self.retSlot)
		self.nRef   = self.refs(self.nSlot)


		self.retnRef = self.refs(self.retSlot, self.nSlot)
		self.xnExpr  = self.expr(self.xExpr, self.nSlot)


		body = ast.Suite([
			ast.Assign(ast.Load(x, 'LowLevel', self.existing('n')), y),
			ast.Return(y)
			])


		self.code = ast.Code('loadTest', None, [x], ['x'], None, None, ret, body)


		a, self.aSlot, self.aExpr  = self.makeLocalObjs('a')
		b, self.bSlot, self.bExpr  = self.makeLocalObjs('b')
		c, self.cSlot, self.cExpr  = self.makeLocalObjs('c')

		self.aRef  = self.refs(self.aSlot)
		self.bRef  = self.refs(self.bSlot)
		self.cRef  = self.refs(self.cSlot)
		self.cnRef = self.refs(self.cSlot, self.nSlot)

		self.anRef  = self.refs(self.aSlot, self.nSlot)
		self.anExpr = self.expr(self.aExpr, self.nSlot)

		dc = ast.DirectCall(self.code, None, [a], [], None, None)
		self.caller = ast.Suite([
			ast.Assign(dc, c),
			])

		invocation = (self.caller, dc, self.code)


		self.context = None
		self.cs = True

		# Make a dummy invocation
		self.db.addInvocation(self.caller, self.context, dc, self.code, self.context)

		self.funcInput,  self.funcOutput   = self.makeConstraints(self.code)

		self.callerInput, self.callerOutput = self.makeConstraints(self.caller)
		self.setInOut(self.callerInput, self.callerOutput)


	def testLocal1(self):
		self.setInOut(self.funcInput, self.funcOutput)

		argument = (self.nRef, None, None)
		results = [
			# No information about x/y/etc as there's no extended parameters...
			(self.nRef,    None, None),
			(self.retnRef, None, None),
			]
		self.checkTransfer(argument, results)

	def testCall1(self):
		argument = (self.aRef, None, None)
		results = [
			(self.aRef, None, None),
			]
		self.checkTransfer(argument, results)

	def testCall2(self):
		argument = (self.cRef, None, None)
		results = [
			]
		self.checkTransfer(argument, results)

	def testCall3(self):
		argument = (self.nRef, None, None)
		results = [
			(self.nRef,  None, (self.anExpr,)),
			(self.cnRef, (self.anExpr,), None),
			]
		self.checkTransfer(argument, results)



class TestVArgCase(TestCompoundConstraintBase):
	def shapeSetUp(self):
		self.context = None
		self.cs = True

		# Parameters
		self.p    = [self.parameterSlot(i) for i in range(3)]
		self.pRef = [self.refs(slot) for slot in self.p]

		# Locals
		x, self.xSlot, self.xExpr  = self.makeLocalObjs('x')
		y, self.ySlot, self.yExpr  = self.makeLocalObjs('y')
		z, self.zSlot, self.zExpr  = self.makeLocalObjs('z')
		ret, self.retSlot, self.retExpr  = self.makeLocalObjs('internal_return')

		# Fields
		self.lSlot = self.sys.canonical.fieldSlot(None, ('LowLevel', self.extractor.getObject('l')))
		self.rSlot = self.sys.canonical.fieldSlot(None, ('LowLevel', self.extractor.getObject('r')))

		# Expressions
		self.retlExpr  = self.expr(self.retExpr, self.lSlot)
		self.retrExpr  = self.expr(self.retExpr, self.rSlot)

		# Reference Counts
		self.xRef   = self.refs(self.xSlot)
		self.yRef   = self.refs(self.ySlot)
		self.zRef   = self.refs(self.zSlot)
		self.retRef = self.refs(self.retSlot)
		self.lRef   = self.refs(self.lSlot)
		self.rRef   = self.refs(self.rSlot)

		body = ast.Suite([
			ast.Store(x, 'LowLevel', self.existing('l'), y),
			ast.Store(x, 'LowLevel', self.existing('r'), z),
			ast.Return(x)
			])


		self.code = ast.Code('buildTreeTest', None, [x, y, z], ['x', 'y', 'z'], None, None, ret, body)


		a, self.aSlot, self.aExpr  = self.makeLocalObjs('a')
		b, self.bSlot, self.bExpr  = self.makeLocalObjs('b')
		c, self.cSlot, self.cExpr  = self.makeLocalObjs('c')

		self.aRef = self.refs(self.aSlot)
		self.bRef = self.refs(self.bSlot)
		self.cRef = self.refs(self.cSlot)


		dc = ast.DirectCall(self.code, None, [], [], a, None)
		self.caller = ast.Suite([
			ast.Assign(dc, c),
			])


		self.v0Slot = self.sys.canonical.fieldSlot(None, ('Array', self.extractor.getObject(0)))
		self.v1Slot = self.sys.canonical.fieldSlot(None, ('Array', self.extractor.getObject(1)))
		self.v2Slot = self.sys.canonical.fieldSlot(None, ('Array', self.extractor.getObject(2)))

		self.v0Ref = self.refs(self.v0Slot)
		self.v1Ref = self.refs(self.v1Slot)
		self.v2Ref = self.refs(self.v2Slot)

		self.cv0Ref  = self.refs(self.cSlot, self.v0Slot)
		self.lv1Ref  = self.refs(self.lSlot, self.v1Slot)
		self.rv2Ref  = self.refs(self.rSlot, self.v2Slot)

		self.av0Expr = self.expr(self.aExpr, self.v0Slot)
		self.av1Expr = self.expr(self.aExpr, self.v1Slot)
		self.av2Expr = self.expr(self.aExpr, self.v2Slot)


		self.clExpr  = self.expr(self.cExpr, self.lSlot)
		self.crExpr  = self.expr(self.cExpr, self.rSlot)


		# Make a dummy invocation
		self.db.addInvocation(self.caller, self.context, dc, self.code, self.context)

		self.funcInput,   self.funcOutput   = self.makeConstraints(self.code)

		self.callerInput, self.callerOutput = self.makeConstraints(self.caller)
		self.setInOut(self.callerInput, self.callerOutput)


	def testLocal1(self):
		self.setInOut(self.funcInput, self.funcOutput)

		argument = (self.pRef[0], None, None)
		results = [
			(self.retRef, None, None),
			]
		self.checkTransfer(argument, results)

	def testLocal2(self):
		self.setInOut(self.funcInput, self.funcOutput)

		argument = (self.pRef[1], None, None)
		results = [
			(self.lRef, (self.retlExpr,), None),
			]
		self.checkTransfer(argument, results)

	def testLocal3(self):
		self.setInOut(self.funcInput, self.funcOutput)

		argument = (self.pRef[2], None, None)
		results = [
			(self.rRef, (self.retrExpr,), None),
			]
		self.checkTransfer(argument, results)

	def testCall1(self):
		argument = (self.aRef, None, None)
		results = [
			(self.aRef, None, None),
			]
		self.checkTransfer(argument, results)

	def testCall2(self):
		argument = (self.cRef, None, None)
		results = [
			]
		self.checkTransfer(argument, results)

	def testCall3(self):
		argument = (self.v0Ref, None, None)
		results = [
			(self.v0Ref,  None, (self.av0Expr,)),
			(self.cv0Ref, (self.av0Expr,), None),
			]
		self.checkTransfer(argument, results)

	def testCall4(self):
		argument = (self.v1Ref, None, None)
		results = [
			(self.v1Ref,  None, (self.clExpr, self.av1Expr,)),
			(self.lv1Ref, (self.clExpr, self.av1Expr,), None),
			]
		self.checkTransfer(argument, results)

	def testCall5(self):
		argument = (self.v2Ref, None, None)
		results = [
			(self.v2Ref,  None, (self.crExpr, self.av2Expr,)),
			(self.rv2Ref, (self.crExpr, self.av2Expr,), None),
			]
		self.checkTransfer(argument, results)