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


import util.calling
from util.tvl import *
class TestCallingUtility(unittest.TestCase):
	def testExact(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], None, None, None)
		info = util.calling.callStackToParamsInfo(callee,  False, 2, False, 0, False)


		self.assertEqual(info.willSucceed, TVLTrue)

		self.assertTransfer(info.argParam, 0, 2, 0, 2, 2)
		self.assertEqual(info.argVParam.active, False)

		self.assertEqual(info.uncertainParam, False)
		self.assertEqual(info.uncertainVParam, False)

	def assertHardFail(self, info):
		self.assertEqual(info.willSucceed, TVLFalse)

		self.assertEqual(info.argParam.active,    False)
		self.assertEqual(info.argVParam.active,    False)

		self.assertEqual(info.uncertainParam, False)
		self.assertEqual(info.uncertainVParam, False)

	def assertHardSucceed(self, info):
		self.assertEqual(info.willSucceed, TVLTrue)

	def assertTransfer(self, transfer, sourceBegin, sourceEnd, destinationBegin, destinationEnd, count):
		self.assertEqual(transfer.active, True)
		self.assertEqual(transfer.sourceBegin, sourceBegin)
		self.assertEqual(transfer.sourceEnd, sourceEnd)
		self.assertEqual(transfer.destinationBegin, destinationBegin)
		self.assertEqual(transfer.destinationEnd, destinationEnd)
		self.assertEqual(transfer.count, count)


	def testTooManyArgs(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], None, None, None)
		info = util.calling.callStackToParamsInfo(callee,  False, 3, False, 0, False)
		self.assertHardFail(info)

	def testTooFewArgs(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], None, None, None)
		info = util.calling.callStackToParamsInfo(callee,  False, 1, False, 0, False)
		self.assertHardFail(info)


	### Vargs ###

	def testExactSpill(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], 2, None, None)
		info = util.calling.callStackToParamsInfo(callee,  False, 4, False, 0, False)

		self.assertHardSucceed(info)

		self.assertTransfer(info.argParam, 0, 2, 0, 2, 2)
		self.assertTransfer(info.argVParam, 2, 4, 0, 2, 2)


		self.assertEqual(info.uncertainParam, False)
		self.assertEqual(info.uncertainVParam, False)


	def testUncertainPullVargs(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], 2, None, None)
		info = util.calling.callStackToParamsInfo(callee,  False, 1, True, 0, False)

		self.assertEqual(info.willSucceed, TVLMaybe)

		self.assertTransfer(info.argParam, 0, 1, 0, 1, 1)
		self.assertEqual(info.argVParam.active, False)


		self.assertEqual(info.uncertainParam, True)
		self.assertEqual(info.uncertainParamStart, 1)

		self.assertEqual(info.uncertainVParam, True)

	def testUncertainPull(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], None, None, None)
		info = util.calling.callStackToParamsInfo(callee, False, 1, True, 0, False)

		self.assertEqual(info.willSucceed, TVLMaybe)

		self.assertTransfer(info.argParam, 0, 1, 0, 1, 1)
		self.assertEqual(info.argVParam.active, False)

		self.assertEqual(info.uncertainParam, True)
		self.assertEqual(info.uncertainParamStart, 1)

		self.assertEqual(info.uncertainVParam, False)

	### Known keywords ###

	def testSemiKeyword(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], None, None, None)
		info = util.calling.callStackToParamsInfo(callee,  False, 1, False, ('b',), False)

		self.assertHardSucceed(info)

		self.assertTransfer(info.argParam, 0, 1, 0, 1, 1)
		self.assertEqual(info.argVParam.active, False)

		self.assertEqual(info.uncertainParam, False)
		self.assertEqual(info.uncertainVParam, False)

		self.assert_(1 in info.certainKeywords)


	def testAllKeyword(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], None, None, None)
		info = util.calling.callStackToParamsInfo(callee,  False, 0, False, ('a', 'b',), False)

		self.assertHardSucceed(info)

		self.assertEqual(info.argParam.active, False)
		self.assertEqual(info.argVParam.active, False)
		self.assertEqual(info.uncertainParam, False)
		self.assertEqual(info.uncertainVParam, False)

		self.assert_(0 in info.certainKeywords)
		self.assert_(1 in info.certainKeywords)

	def testRedundantKeyword(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], None, None, None)
		info = util.calling.callStackToParamsInfo(callee,  False, 1, False, ('a',), False)
		self.assertHardFail(info)

	def testBogusKeyword(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [], None, None, None)
		info = util.calling.callStackToParamsInfo(callee,  False, 2, False, ('c',), False)
		self.assertHardFail(info)

	### Deaults ###

	def testIncompleteDefaults(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [2], None, None, None)
		info = util.calling.callStackToParamsInfo(callee,  False, 0, False, (), False)
		self.assertHardFail(info)

	def testUsedDefaults(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [2], None, None, None)
		info = util.calling.callStackToParamsInfo(callee,  False, 1, False, (), False)

		self.assertEqual(info.willSucceed, TVLTrue)
		self.assertTransfer(info.argParam, 0, 1, 0, 1, 1)
		self.assertEqual(info.argVParam.active, False)
		self.assertEqual(info.uncertainParam, False)
		self.assertEqual(info.uncertainVParam, False)

		self.assert_(1 in info.defaults)

	def testUnusedDefaults(self):
		callee = util.calling.CalleeParams(None, [0, 1], ['a', 'b'], [2], None, None, None)
		info = util.calling.callStackToParamsInfo(callee,  False, 2, False, (), False)

		self.assertEqual(info.willSucceed, TVLTrue)
		self.assertTransfer(info.argParam, 0, 2, 0, 2, 2)
		self.assertEqual(info.argVParam.active, False)
		self.assertEqual(info.uncertainParam, False)
		self.assertEqual(info.uncertainVParam, False)

		self.assert_(not info.defaults, info.defaults)


##from cStringIO import StringIO
##from common.simplecodegen import SimpleCodeGen
##from optimization.simplify import simplify
##from language.python import ast

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
