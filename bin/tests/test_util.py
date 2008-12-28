from __future__ import absolute_import

import unittest

from util.typedispatch import *


class TestTypeDisbatch(unittest.TestCase):
	def testTD(self):
		def visitNumber(self, node):
			return 'number'

		def visitDefault(self, node):
			return 'default'


		class FooBar(object):
			__metaclass__ = typedispatcher

			num = dispatch(int, long)(visitNumber)
			default = defaultdispatch(visitDefault)


		self.assertEqual(FooBar.__dict__['num'],       visitNumber)
		self.assertEqual(FooBar.__dict__['default'],   visitDefault)


		foo = FooBar()
		
		self.assertEqual(foo(1),     'number')
		self.assertEqual(foo(2**70), 'number')
		self.assertEqual(foo(1.0),   'default')




from util import replaceGlobals

from decompiler.programextractor import Extractor


import analysis.cpa

class TestCPA(unittest.TestCase):
	def assertIn(self, first, second, msg=None):
		"""Fail if the one object is not in the other, using the "in" operator.
		"""
		if first not in second:
			raise self.failureException, (msg or '%r not in %r' % (first, second))


	def assertLocalRefTypes(self, finfo, lcl, types):
		self.assertIn(lcl, finfo.localInfos)
		linfo  = finfo.localInfos[lcl].merged
		refs   = linfo.references

		# There's one reference returned, and it's an integer.
		self.assertEqual(len(refs), len(types))
		for ref in refs:
			self.assertIn(ref.obj.type, types)


	def processFunc(self, func):

		func = replaceGlobals(func, {})

		funcobj = self.extractor.getObject(func)

		self.extractor.ensureLoaded(funcobj)
		funcast = self.extractor.getCall(funcobj)
	
		return func, funcast, funcobj


	def testAdd(self):
		self.extractor = Extractor(verbose=False)
		
		def func(a, b):
			return 2*a+b

		func, funcast, funcobj = self.processFunc(func)

		for paramname in funcast.code.parameternames:
			self.assertEqual(type(paramname), str)
		
		a = self.extractor.getObject(3)
		b = self.extractor.getObject(5)

		result = analysis.cpa.evaluate(self.extractor, [(funcast, funcobj, (a, b))])

		finfo  = result.db.functionInfo(funcast)
		types = set((self.extractor.getObject(int),))

		for param in funcast.code.parameters:
			self.assertLocalRefTypes(finfo, param, types)
			
		self.assertLocalRefTypes(finfo, funcast.code.returnparam, types)



import util.calling
class TestCallingUtility(unittest.TestCase):
	def testExact(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], None, None)
		info = util.calling.callStackToParamsInfo(callee, 2, False, 0, False)


		self.assertEqual(info.willAlwaysSucceed, True)
		self.assertEqual(info.willAlwaysFail,    False)

		self.assertTransfer(info.argParam, 0, 2, 0, 2, 2)
		self.assertEqual(info.argVParam.active, False)

		self.assertEqual(info.uncertainParam, False)
		self.assertEqual(info.vparamUncertain, False)

	def assertHardFail(self, info):
		self.assertEqual(info.willAlwaysSucceed, False)
		self.assertEqual(info.willAlwaysFail,    True)


		self.assertEqual(info.argParam.active,    False)
		self.assertEqual(info.argVParam.active,    False)

		self.assertEqual(info.uncertainParam, False)
		self.assertEqual(info.vparamUncertain, False)

	def assertHardSucceed(self, info):
		self.assertEqual(info.willAlwaysSucceed, True)
		self.assertEqual(info.willAlwaysFail,    False)


	def assertTransfer(self, transfer, sourceBegin, sourceEnd, destinationBegin, destinationEnd, count):
		self.assertEqual(transfer.active, True)
		self.assertEqual(transfer.sourceBegin, sourceBegin)
		self.assertEqual(transfer.sourceEnd, sourceEnd)
		self.assertEqual(transfer.destinationBegin, destinationBegin)
		self.assertEqual(transfer.destinationEnd, destinationEnd)
		self.assertEqual(transfer.count, count)
		

	def testTooManyArgs(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], None, None)
		info = util.calling.callStackToParamsInfo(callee, 3, False, 0, False)
		self.assertHardFail(info)

	def testTooFewArgs(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], None, None)
		info = util.calling.callStackToParamsInfo(callee, 1, False, 0, False)
		self.assertHardFail(info)


	### Vargs ###

	def testExactSpill(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], 2, None)
		info = util.calling.callStackToParamsInfo(callee, 4, False, 0, False)

		self.assertHardSucceed(info)

		self.assertTransfer(info.argParam, 0, 2, 0, 2, 2)
		self.assertTransfer(info.argVParam, 2, 4, 0, 2, 2)


		self.assertEqual(info.uncertainParam, False)
		self.assertEqual(info.vparamUncertain, False)


	def testUncertainPullVargs(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], 2, None)
		info = util.calling.callStackToParamsInfo(callee, 1, True, 0, False)

		self.assertEqual(info.willAlwaysSucceed, False)
		self.assertEqual(info.willAlwaysFail,    False)

		self.assertTransfer(info.argParam, 0, 1, 0, 1, 1)
		self.assertEqual(info.argVParam.active, False)


		self.assertEqual(info.uncertainParam, True)
		self.assertEqual(info.uncertainParamStart, 1)
		
		self.assertEqual(info.vparamUncertain, True)

	def testUncertainPull(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], None, None)
		info = util.calling.callStackToParamsInfo(callee, 1, True, 0, False)

		self.assertEqual(info.willAlwaysSucceed, False)
		self.assertEqual(info.willAlwaysFail,    False)

		self.assertTransfer(info.argParam, 0, 1, 0, 1, 1)
		self.assertEqual(info.argVParam.active, False)
		
		self.assertEqual(info.uncertainParam, True)
		self.assertEqual(info.uncertainParamStart, 1)
		
		self.assertEqual(info.vparamUncertain, False)

	### Known keywords ###

	def testSemiKeyword(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], None, None)
		info = util.calling.callStackToParamsInfo(callee, 1, False, ('b',), False)

		self.assertHardSucceed(info)

		self.assertTransfer(info.argParam, 0, 1, 0, 1, 1)
		self.assertEqual(info.argVParam.active, False)
		
		self.assertEqual(info.uncertainParam, False)
		self.assertEqual(info.vparamUncertain, False)

		self.assert_(1 in info.certainKeywords)


	def testAllKeyword(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], None, None)
		info = util.calling.callStackToParamsInfo(callee, 0, False, ('a', 'b',), False)

		self.assertHardSucceed(info)

		self.assertEqual(info.argParam.active, False)
		self.assertEqual(info.argVParam.active, False)
		self.assertEqual(info.uncertainParam, False)
		self.assertEqual(info.vparamUncertain, False)

		self.assert_(0 in info.certainKeywords)
		self.assert_(1 in info.certainKeywords)

	def testRedundantKeyword(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], None, None)
		info = util.calling.callStackToParamsInfo(callee, 1, False, ('a',), False)
		self.assertHardFail(info)

	def testBogusKeyword(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], None, None)
		info = util.calling.callStackToParamsInfo(callee, 2, False, ('c',), False)
		self.assertHardFail(info)

	### Deaults ###

	def testIncompleteDefaults(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [2], None, None)
		info = util.calling.callStackToParamsInfo(callee, 0, False, (), False)
		self.assertHardFail(info)

	def testUsedDefaults(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [2], None, None)
		info = util.calling.callStackToParamsInfo(callee, 1, False, (), False)

		self.assertTransfer(info.argParam, 0, 1, 0, 1, 1)
		self.assertEqual(info.argVParam.active, False)
		self.assertEqual(info.uncertainParam, False)
		self.assertEqual(info.vparamUncertain, False)

		self.assert_(1 in info.defaults)

	def testUnusedDefaults(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [2], None, None)
		info = util.calling.callStackToParamsInfo(callee, 2, False, (), False)

		self.assertTransfer(info.argParam, 0, 2, 0, 2, 2)
		self.assertEqual(info.argVParam.active, False)
		self.assertEqual(info.uncertainParam, False)
		self.assertEqual(info.vparamUncertain, False)

		self.assert_(not info.defaults)

		
##from cStringIO import StringIO
##from common.simplecodegen import SimpleCodeGen
##from optimization.simplify import simplify
##from programIR.python import ast

##class TestConstantFolding(unittest.TestCase):
##	def processFunc(self, func):
##
##		func = replaceGlobals(func, {})
##		
##		f = extractor.decompileFunction(func, ssa=False)
##		extractor.process()
##	
##		f = simplify(extractor, None, f)
##
####		sio = StringIO()
####		scg = SimpleCodeGen(sio)
####		scg.walk(f)
####		print sio.getvalue()
##
##		return f
##
##	def testSwitch1(self):
##		def func(s):
##			a = 11
##			if s:
##				b = 4
##				c = a+b
##				d = c
##			else:
##				b = 2
##				c = a+b
##				d = c+2
##			return a+d
##
##		f = self.processFunc(func)
##
##		finalStatement = f.code.ast.blocks[-1]
##		self.assertEqual(type(finalStatement), ast.Return)
##		self.assertEqual(type(finalStatement.expr), ast.Existing)
##		self.assertEqual(finalStatement.expr.object.pyobj, 26)
##
##	def testSwitch2(self):
##		def func(s, t):
##			a = 0
##			if s:
##				if t:
##					a = 1
##				else:
##					a = 3
##					return a
##			else:
##				if t:
##					a = 1
##				else:
##					a = 2
##					return a
##			return a
##
##		f = self.processFunc(func)
##
##		finalStatement = f.code.ast.blocks[-1]
##		self.assertEqual(type(finalStatement), ast.Return)
##		self.assertEqual(type(finalStatement.expr), ast.Existing)
##		self.assertEqual(finalStatement.expr.object.pyobj, 1)
##
##
##	def testFor1(self):
##		def func(s):
##			a = 5
##			b = 4
##			c = 0
##			d = 1
##			for i in range(s):
##				d = c+1
##				c = c+a
##				b = a-1
##				a = b+1
##
##			return a+b+d
##
##		f = self.processFunc(func)
##
##		finalStatement = f.code.ast.blocks[-1]
##		self.assertEqual(type(finalStatement), ast.Return)
##		self.assertEqual(type(finalStatement.expr), ast.Local)
##
##
##	def testFor2(self):
##		def func(s):
##			i = 0
##			r = 0
##			for i in range(s):
##				r = i # Should not fold to r = 0
##				i = 0
##			return r
##
##		f = self.processFunc(func)
##
##		finalStatement = f.code.ast.blocks[-1]
##		self.assertEqual(type(finalStatement), ast.Return)
##		self.assertEqual(type(finalStatement.expr), ast.Local)
##
##
##	def testWhile1(self):
##		def func(s):
##			a = 5
##			b = 4
##			c = 0
##			d = 1
##			i = 0
##			while i<s:
##				d = c+1
##				c = c+a
##				b = a-1
##				a = b+1
##				s += 1
##			return a+b+d
##
##		f = self.processFunc(func)
##
##		finalStatement = f.code.ast.blocks[-1]
##		self.assertEqual(type(finalStatement), ast.Return)
##		self.assertEqual(type(finalStatement.expr), ast.Local)
##
##
##	def testTryExceptFinally1(self):
##		def func(s):
##			i = 0
##			try:
##				i = 1
##				bool(i)
##			except:
##				pass
##			return i
##
##		f = self.processFunc(func)
##
##		finalStatement = f.code.ast.blocks[-1]
##		self.assertEqual(type(finalStatement), ast.Return)
##		self.assertEqual(type(finalStatement.expr), ast.Existing)
##		self.assertEqual(finalStatement.expr.object.pyobj, 1)
##
##
##	def testTryExceptFinally2(self):
##		def func(s):
##			i = 0
##			try:
##				bool(i)
##				i = 1
##			except:
##				pass
##			return i
##
##		f = self.processFunc(func)
##
##		finalStatement = f.code.ast.blocks[-1]
##		self.assertEqual(type(finalStatement), ast.Return)
##		self.assertEqual(type(finalStatement.expr), ast.Local)
##
##
##	def testTryExceptFinally3(self):
##		def func(s):
##			a = s
##			try:
##				a = 1
##				bool(a)
##			except:
##				a += 1
##			else:
##				a *= 2
##				
##			return a
##
##		f = self.processFunc(func)
##
##		finalStatement = f.code.ast.blocks[-1]
##		self.assertEqual(type(finalStatement), ast.Return)
##		self.assertEqual(type(finalStatement.expr), ast.Existing)
##		self.assertEqual(finalStatement.expr.object.pyobj, 2)
##
##
##	def testTryExceptFinally4(self):
##		def func(s):
##			a = 0
##			try:
##				a = 1
##				a = 2
##				a = int(s)
##				a = 4
##			except:
##				res = a
##			else:
##				res = a/2
##			
##			return res
##
##		f = self.processFunc(func)
##
##		finalStatement = f.code.ast.blocks[-1]
##		self.assertEqual(type(finalStatement), ast.Return)
##		self.assertEqual(type(finalStatement.expr), ast.Existing)
##		self.assertEqual(finalStatement.expr.object.pyobj, 2)
##
##	def testTryExceptFinally5(self):
##		def func(s):
##			a = 0
##			try:
##				a = 1
##				a = 2
##				a = int(s)
##				a = 5
##				a = int(s)
##				a = 4
##			except:
##				res = a
##			else:
##				res = a/2
##			
##			return res
##
##		f = self.processFunc(func)
##
##		finalStatement = f.code.ast.blocks[-1]
##		self.assertEqual(type(finalStatement), ast.Return)
##		self.assertEqual(type(finalStatement.expr), ast.Local)
