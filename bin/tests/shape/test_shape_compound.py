from __future__ import absolute_import

from tests.shape.shape_base import *

class TestSimpleCase(TestCompoundConstraintBase):
	def shapeSetUp(self):
		self.context = None
		self.cs = True

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

		dc.rewriteAnnotation(invokes=(((self.code, self.context),), None))

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
		self.context = None
		self.cs = True

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

		dc.rewriteAnnotation(invokes=(((self.code, self.context),), None))

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


		dc.rewriteAnnotation(invokes=(((self.code, self.context),), None))

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



class TestVParamCase(TestCompoundConstraintBase):
	def shapeSetUp(self):
		self.context = None
		self.cs = True

		# Parameters
		self.p    = [self.parameterSlot(i) for i in range(3)]
		self.pRef = [self.refs(slot) for slot in self.p]

		# Locals
		vargs, self.vargsSlot, self.vargsExpr  = self.makeLocalObjs('vargs')
		ret,   self.retSlot,   self.retExpr  = self.makeLocalObjs('internal_return')


		body = ast.Suite([
			ast.Return(vargs)
			])

		self.code = ast.Code('buildTupleTest', None, [], [], vargs, None, ret, body)


		a, self.aSlot, self.aExpr  = self.makeLocalObjs('a')
		b, self.bSlot, self.bExpr  = self.makeLocalObjs('b')
		c, self.cSlot, self.cExpr  = self.makeLocalObjs('c')
		d, self.dSlot, self.dExpr  = self.makeLocalObjs('d')

		dc = ast.DirectCall(self.code, None, [a, b, c], [], None, None)
		self.caller = ast.Suite([
			ast.Assign(dc, d),
			])


		self.v0Slot = self.sys.canonical.fieldSlot(None, ('Array', self.extractor.getObject(0)))
		self.v1Slot = self.sys.canonical.fieldSlot(None, ('Array', self.extractor.getObject(1)))
		self.v2Slot = self.sys.canonical.fieldSlot(None, ('Array', self.extractor.getObject(2)))
		self.v0Ref = self.refs(self.v0Slot)
		self.v1Ref = self.refs(self.v1Slot)
		self.v2Ref = self.refs(self.v2Slot)

		self.retv0Expr = self.expr(self.retExpr, self.v0Slot)
		self.retv1Expr = self.expr(self.retExpr, self.v1Slot)
		self.retv2Expr = self.expr(self.retExpr, self.v2Slot)

		self.aRef   = self.refs(self.aSlot)
		self.av0Ref = self.refs(self.aSlot, self.v0Slot)

		self.bRef   = self.refs(self.bSlot)
		self.bv1Ref = self.refs(self.bSlot, self.v1Slot)

		self.cRef   = self.refs(self.cSlot)
		self.cv2Ref = self.refs(self.cSlot, self.v2Slot)

		self.dv0Expr = self.expr(self.dExpr, self.v0Slot)
		self.dv1Expr = self.expr(self.dExpr, self.v1Slot)
		self.dv2Expr = self.expr(self.dExpr, self.v2Slot)

		dc.rewriteAnnotation(invokes=(((self.code, self.context),), None))

		# Make a dummy invocation
		self.db.addInvocation(self.caller, self.context, dc, self.code, self.context)

		self.funcInput,   self.funcOutput   = self.makeConstraints(self.code)

		self.callerInput, self.callerOutput = self.makeConstraints(self.caller)
		self.setInOut(self.callerInput, self.callerOutput)


	def testLocal1(self):
		self.setInOut(self.funcInput, self.funcOutput)

		argument = (self.pRef[0], None, None)
		results = [
			(self.v0Ref, (self.retv0Expr,), None),
			]
		self.checkTransfer(argument, results)

	def testLocal2(self):
		self.setInOut(self.funcInput, self.funcOutput)

		argument = (self.pRef[1], None, None)
		results = [
			(self.v1Ref, (self.retv1Expr,), None),
			]
		self.checkTransfer(argument, results)

	def testLocal3(self):
		self.setInOut(self.funcInput, self.funcOutput)

		argument = (self.pRef[2], None, None)
		results = [
			(self.v2Ref, (self.retv2Expr,), None),
			]
		self.checkTransfer(argument, results)

	def testCall1(self):
		argument = (self.aRef, None, None)
		results = [
			(self.av0Ref, (self.dv0Expr,), None),
			]
		self.checkTransfer(argument, results)

	def testCall2(self):
		argument = (self.bRef, None, None)
		results = [
			(self.bv1Ref, (self.dv1Expr,), None),
			]
		self.checkTransfer(argument, results)

	def testCall3(self):
		argument = (self.cRef, None, None)
		results = [
			(self.cv2Ref, (self.dv2Expr,), None),
			]
		self.checkTransfer(argument, results)


class TestRecursiveCase(TestCompoundConstraintBase):
	def makeDummy(self):
		# Locals
		l, lSlot, lExpr  = self.makeLocalObjs('l')
		n, nSlot, nExpr  = self.makeLocalObjs('n')
		t,tSlot,tExpr  = self.makeLocalObjs('t')

		ret,   retSlot,   retExpr  = self.makeLocalObjs('internal_return')

		load  = ast.Assign(ast.Load(l, 'LowLevel', self.existing('tail')), t)
		store = ast.Store(l, 'LowLevel', self.existing('tail'), n)

		body = ast.Suite([
			load,
			store,
			ast.Return(l),
			])

		code = ast.Code('reverseTestDummy', None, [l, n], ['l', 'n'], None, None, ret, body)

		self.makeConstraints(code)

		self.dummyLoadPre  = self.statementPre(load)
		self.dummyLoadPost = self.statementPost(load)

		self.dummyStorePre  = self.statementPre(store)
		self.dummyStorePost = self.statementPost(store)

		return code

	def shapeSetUp(self):
		self.context = None
		self.cs = True

		# Parameters
		self.p    = [self.parameterSlot(i) for i in range(2)]
		self.pRef = [self.refs(slot) for slot in self.p]

		#dummy = self.makeDummy()

		# Locals
		l, self.lSlot, self.lExpr  = self.makeLocalObjs('l')
		n, self.nSlot, self.nExpr  = self.makeLocalObjs('n')
		t, self.tSlot, self.tExpr  = self.makeLocalObjs('t')

		ret,   self.retSlot,   self.retExpr  = self.makeLocalObjs('internal_return')

		self.headSlot  = self.sys.canonical.fieldSlot(None, ('LowLevel', self.extractor.getObject('head')))
		self.tailSlot  = self.sys.canonical.fieldSlot(None, ('LowLevel', self.extractor.getObject('tail')))


		self.retRef  = self.refs(self.retSlot)
		self.headRef = self.refs(self.headSlot)
		self.tailRef = self.refs(self.tailSlot)
		self.nullRef = self.refs()


		# Pre-declare
		self.code = ast.Code('reverseTest', None, [l, n], ['l', 'n'], None, None, ret, ast.Suite([]))


		cond = ast.Condition(ast.Suite([]), t)

		#callCode = dummy
		callCode = self.code

		dc = ast.DirectCall(callCode, None, [t, l], [], None, None)

		temp = ast.Local('temp')
		tb = ast.Suite([
			ast.Assign(dc, temp),
			ast.Return(temp)
			])

		fb = ast.Suite([
			ast.Return(l),
			])

		switch = ast.Switch(cond, tb, fb)

		load  = ast.Assign(ast.Load(l, 'LowLevel', self.existing('tail')), t)
		store = ast.Store(l, 'LowLevel', self.existing('tail'), n)

		body = ast.Suite([
			load,
			store,
			switch,
			#tb,
			])

		self.code.ast = body

		#from common import simplecodegen
		#simplecodegen.SimpleCodeGen(None).walk(self.code)


		dc.rewriteAnnotation(invokes=(((callCode, self.context),), None))

		# Make a dummy invocation
		self.db.addInvocation(self.code, self.context, dc, callCode, self.context)

		self.codeInput, self.codeOutput = self.makeConstraints(self.code)
		self.setInOut(self.codeInput, self.codeOutput)

		self.storePre  = self.statementPre(store)
		self.storePost = self.statementPost(store)

		self.loadPre  = self.statementPre(load)
		self.loadPost = self.statementPost(load)

		self.dcPre  = self.statementPre(dc)
		self.dcPost = self.statementPost(dc)


	def testLocal1(self):
		argument = (self.pRef[0], None, None)
		results = [
			(self.retRef,  None, None),
			(self.tailRef, None, None),
			#(self.nullRef, None, None),
			]
		self.checkTransfer(argument, results)

	def testLocal2(self):
		argument = (self.pRef[1], None, None)
		results = [
			(self.tailRef, None, None),

			# TODO this is due to analysis imprecision.
			# To fix this, we need disjointness information.
			# n(.tail)+ != l(.tail)+
			(self.retRef, None, None),

			#(self.nullRef, None, None),
			]
		self.checkTransfer(argument, results)
		#self.dump(self.loadPre)

	def testLocal3(self):
		argument = (self.tailRef, None, None)
		results = [
			(self.retRef, None, None),
			(self.tailRef, None, None),
			#(self.nullRef, None, None),
			]
		self.checkTransfer(argument, results)
		#self.checkTransfer(argument, None)
		#assert self.dcPost is not None
		#self.dump(self.codeOutput)

	def testLocal4(self):
		argument = (self.headRef, None, None)
		results = [
			(self.headRef, None, None),
			]
		self.checkTransfer(argument, results)


class TestAllocateCase(TestCompoundConstraintBase):
	def shapeSetUp(self):
		self.context = None
		self.cs = True

		x, self.xSlot, self.xExpr  = self.makeLocalObjs('x')
		y, self.ySlot, self.yExpr  = self.makeLocalObjs('y')


		aobj = self.extractor.getObject('a')
		self.aSlot  = self.sys.canonical.fieldSlot(None, ('LowLevel', aobj))

		bobj = self.extractor.getObject('a')
		self.bSlot  = self.sys.canonical.fieldSlot(None, ('LowLevel', bobj))

		self.xRef   = self.refs(self.xSlot)
		self.yRef   = self.refs(self.ySlot)

		self.aRef   = self.refs(self.aSlot)
		self.bRef   = self.refs(self.bSlot)


		self.yaexpr = self.expr(self.yExpr, self.aSlot)
		self.ybexpr = self.expr(self.yExpr, self.bSlot)

		alloc = ast.Allocate(x)

		self.code = ast.Suite([
			ast.Assign(alloc, y),
			])

		lc = self.sys.cpacanonical.localName(None, x, self.context)
		xinfo = self.root.root(self.sys, lc, self.root.regionHint)
		btype = self.sys.cpacanonical.pathType(None, 'bogus', id(alloc))

		bogusinfo = xinfo.initializeType(self.sys, btype)

		self.aField = self.sys.cpacanonical.fieldName('LowLevel', aobj)
		self.bField = self.sys.cpacanonical.fieldName('LowLevel', bobj)

		bogusinfo.field(self.sys, self.aField, self.root.regionHint)
		bogusinfo.field(self.sys, self.bField, self.root.regionHint)

		alloc.rewriteAnnotation(allocates=((bogusinfo,),None))

		self.funcInput,  self.funcOutput = self.makeConstraints(self.code)
		self.setInOut(self.funcInput, self.funcOutput)


	def testLocal1(self):
		argument = (self.aRef, None, None)
		results = [
			(self.aRef,    None, (self.yaexpr,)),
			]
		self.checkTransfer(argument, results)


	def testLocal2(self):
		argument = (self.bRef, None, None)
		results = [
			(self.bRef,    None, (self.ybexpr,)),
			]
		self.checkTransfer(argument, results)


	def testLocal3(self):
		argument = (self.xRef, None, None)
		results = [
			(self.xRef,    None, None),
			]
		self.checkTransfer(argument, results)

	def testLocal4(self):
		argument = (self.yRef, None, None)
		results = [
			]
		self.checkTransfer(argument, results)