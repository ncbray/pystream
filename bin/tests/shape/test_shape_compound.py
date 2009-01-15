from __future__ import absolute_import

from tests.shape.shape_base import *

class TestSimpleCase(TestCompoundConstraintBase):
	def setUp(self):
		self.db = MockDB()
		self.sys  = analysis.shape.RegionBasedShapeAnalysis(self.db)
		
		# Splice example from paper
		x, self.xSlot, self.xExpr  = self.makeLocalObjs('x')
		y, self.ySlot, self.yExpr  = self.makeLocalObjs('y')
		z, self.zSlot, self.zExpr  = self.makeLocalObjs('z')
		t, self.tSlot, self.tExpr  = self.makeLocalObjs('t')
		q, self.qSlot, self.qExpr  = self.makeLocalObjs('q')
		ret, self.retSlot, self.retExpr  = self.makeLocalObjs('internal_return')

		self.xRef = self.scalarIncrement(None, self.xSlot)
		self.yRef = self.scalarIncrement(None, self.ySlot)
		self.retRef = self.scalarIncrement(None, self.retSlot)
		self.nSlot = self.sys.canonical.fieldSlot(None, ('LowLevel', 'n'))

		self.nRef = self.scalarIncrement(None, self.nSlot)
		self.n2Ref = self.scalarIncrement(self.nRef, self.nSlot)
		self.n3Ref = self.scalarIncrement(self.n2Ref, self.nSlot)


		# t = x
		# x = t.n
		# q = y.n
		# t.n = q
		# y.n = t
		# y = t.n

		# tn(y.n|)

		# tn(|t.n)
		# tny(t.n|)

		# HACK should really be doing a convertToBool?
		cond = ast.Condition(ast.Suite([]), x)
		
		body = ast.Suite([
			ast.Assign(x, t),
			ast.Assign(ast.Load(t, 'LowLevel', ast.Existing('n')), x),
			ast.Assign(ast.Load(y, 'LowLevel', ast.Existing('n')), q),
			ast.Store(t, 'LowLevel', ast.Existing('n'), q),
			ast.Delete(q),
			ast.Store(y, 'LowLevel', ast.Existing('n'), t),
			ast.Assign(ast.Load(t, 'LowLevel', ast.Existing('n')), y),
			])
		
		else_ = ast.Suite([])

		loop = ast.While(cond, body, else_)

		self.body = ast.Suite([
			ast.Assign(y, z),
			loop,
			ast.Return(z)
			])


		self.code = ast.Code(None, [x, y], ['x', 'y'], None, None, ret, self.body)
		self.func = ast.Function('test', self.code)


		a, self.aSlot, self.aExpr  = self.makeLocalObjs('a')
		b, self.bSlot, self.bExpr  = self.makeLocalObjs('b')
		c, self.cSlot, self.cExpr  = self.makeLocalObjs('c')

		self.aRef = self.scalarIncrement(None, self.aSlot)
		self.bRef = self.scalarIncrement(None, self.bSlot)
		self.cRef = self.scalarIncrement(None, self.cSlot)
		self.bcRef = self.scalarIncrement(self.bRef, self.cSlot)

		self.anRef = self.scalarIncrement(self.aRef, self.nSlot)

		dc = ast.DirectCall(self.func, None, [a,b], [], None, None)
		self.caller = ast.Suite([
			ast.Assign(dc, c),
			])

		invocation = (self.caller, dc, self.func)


		self.context = None
		self.cs = True

		# Make a dummy invocation
		self.db.addInvocation(self.caller, self.context, dc, self.func, self.context)

		self.funcInput,  self.funcOutput   = self.makeConstraints(self.func)
		self.callerInput, self.callerOutput = self.makeConstraints(self.caller)

		self.setInOut(self.callerInput, self.callerOutput)

	def testLocal1(self):
		self.setInOut(self.funcInput, self.funcOutput)

		argument = (self.xRef, None, None)
		results = [
			(self.nRef, None, None),
			]
		self.checkTransfer(argument, results)

	def testLocal2(self):
		self.setInOut(self.funcInput, self.funcOutput)

		argument = (self.yRef, None, None)
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
	def setUp(self):
		self.db = MockDB()
		self.sys  = analysis.shape.RegionBasedShapeAnalysis(self.db)
		
		x, self.xSlot, self.xExpr  = self.makeLocalObjs('x')
		y, self.ySlot, self.yExpr  = self.makeLocalObjs('y')
		ret, self.retSlot, self.retExpr  = self.makeLocalObjs('internal_return')

		self.xRef = self.scalarIncrement(None, self.xSlot)
		self.retRef = self.scalarIncrement(None, self.retSlot)
		self.nSlot = self.sys.canonical.fieldSlot(None, ('LowLevel', 'n'))
		self.nRef = self.scalarIncrement(None, self.nSlot)


		self.retnRef = self.scalarIncrement(self.retRef, self.nSlot)
		self.xnExpr = self.sys.canonical.fieldExpr(self.xExpr, self.nSlot)

		
		body = ast.Suite([
			ast.Assign(ast.Load(x, 'LowLevel', ast.Existing('n')), y),
			ast.Return(y)
			])
		

		self.code = ast.Code(None, [x], ['x'], None, None, ret, body)
		self.func = ast.Function('loadTest', self.code)


		a, self.aSlot, self.aExpr  = self.makeLocalObjs('a')
		b, self.bSlot, self.bExpr  = self.makeLocalObjs('b')
		c, self.cSlot, self.cExpr  = self.makeLocalObjs('c')

		self.aRef = self.scalarIncrement(None, self.aSlot)
		self.bRef = self.scalarIncrement(None, self.bSlot)
		self.cRef = self.scalarIncrement(None, self.cSlot)
		self.cnRef = self.scalarIncrement(self.cRef, self.nSlot)

		self.anRef = self.scalarIncrement(self.aRef, self.nSlot)
		self.anExpr = self.sys.canonical.fieldExpr(self.aExpr, self.nSlot)

		dc = ast.DirectCall(self.func, None, [a], [], None, None)
		self.caller = ast.Suite([
			ast.Assign(dc, c),
			])

		invocation = (self.caller, dc, self.func)


		self.context = None
		self.cs = True

		# Make a dummy invocation
		self.db.addInvocation(self.caller, self.context, dc, self.func, self.context)

		self.funcInput,  self.funcOutput   = self.makeConstraints(self.func)
		self.callerInput, self.callerOutput = self.makeConstraints(self.caller)

		self.setInOut(self.callerInput, self.callerOutput)


	def testLocal1(self):
		self.setInOut(self.funcInput, self.funcOutput)
		
		argument = (self.nRef, None, None)
		results = [
			#(self.nRef, None, (self.xnExpr,)),
			#(self.retnRef, (self.xnExpr,), None),

			# No information about x/y/etc as there's no extended parameters...
			(self.nRef, None, None),
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
			(self.nRef, None, (self.anExpr,)),
			(self.cnRef, (self.anExpr,), None),
			]
		self.checkTransfer(argument, results)
