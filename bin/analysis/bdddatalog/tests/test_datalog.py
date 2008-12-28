from __future__ import absolute_import

import unittest

from analysis.bdddatalog import compileAlgorithim
from analysis.bdddatalog import datalogIR
from analysis.bdddatalog import relationalIR


from . import algorithims


class TestDatalogParser(unittest.TestCase):
	def testParser(self):
		ast = datalogIR.parseAlgorithim(algorithims.Algorithim)

		self.assertEqual(1, len(ast.domains))
		self.assertEqual(3, len(ast.relations))
		self.assertEqual(4, len(ast.expressions))

	def testSymbolRedef(self):
		self.assertRaises(datalogIR.datalogast.SymbolRedefinitionError, datalogIR.parser.astFromAlgorithim, algorithims.SymbolRedef)

	def testUnknownDomain(self):
		self.assertRaises(datalogIR.datalogast.UnknownDomainError, datalogIR.parser.astFromAlgorithim, algorithims.UnknownDomain)

	def testBadExpression(self):
		self.assertRaises(datalogIR.datalogast.UnknownTableError, datalogIR.parser.astFromAlgorithim, algorithims.BadExpression)

	def testBadType(self):
		self.assertRaises(datalogIR.datalogast.ExpressionTypeError, datalogIR.parser.astFromAlgorithim, algorithims.BadType)

	def testBadSize(self):
		self.assertRaises(datalogIR.datalogast.ExpressionArgumentError, datalogIR.parser.astFromAlgorithim, algorithims.BadSize)

	def testNameReuse(self):
		ast = datalogIR.parser.astFromAlgorithim(algorithims.NameReuse)

class TestDatalogOptimizer(unittest.TestCase):
	def setUp(self):
		self.ast = datalogIR.parseAlgorithim(algorithims.Algorithim)
	
	def testPDG(self):
		reads, writes = datalogIR.optimizer.makePDG(self.ast)

		t = self.ast.symbols['transition']
		c = self.ast.symbols['closure']
		b = self.ast.symbols['backwards']

		expected = {t:set(),
			   c:set((t, c)),
			   b:set((t, b)),
			   }
		self.assertEqual(expected, writes)


	def testDeadCode(self):
		# HACK?
		ast = datalogIR.parseAlgorithim(algorithims.DeadCode)

		self.assertEqual(len(ast.relations), 7)
		self.assertEqual(len(ast.expressions), 4)
		self.assertEqual(len(ast.domains), 4)



	def testTemporary(self):
		ast = datalogIR.parseAlgorithim(algorithims.Temporary)

		self.assertEqual(len(ast.relations), 6)
		self.assertEqual(len(ast.expressions), 4)
		self.assertEqual(len(ast.domains), 3)


class TestClosureFunctionality(unittest.TestCase):
	def setUp(self):
		self.prgm = compileAlgorithim(algorithims.Algorithim, {'state':8})

	def testCompilation(self):
		self.assertEqual(len(self.prgm.relations['transition'].attributes), 2)

	def testFunctionality(self):
		t = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 5), (6, 7)]

		for c, n in t:
			self.prgm.set('transition', current=c, next=n)

		transition = self.prgm.relations['transition']
		self.assertEqual(transition.enumerateList(), t)

		self.prgm.execute()

		closure = self.prgm.relations['closure']
		self.assert_(closure.restrict(current=0, next=5).isTrue())
		self.assert_(closure.restrict(current=7).isFalse())
		
		backwards = self.prgm.relations['backwards']
		self.assert_(backwards.restrict(current=0).isFalse())
		self.assert_(backwards.restrict(current=7, next=0).isTrue())

		self.assertEqual(closure.restrict(current=0).enumerateList(), [(1,), (2,), (3,), (4,), (5,), (6,), (7,)])
		self.assertEqual(closure.restrict(current=6).enumerateList(), [(5,), (6,), (7,)])
		self.assertEqual(closure.restrict(current=7).enumerateList(), [])


class TestStratification(unittest.TestCase):
	def testIsNotstratified(self):
		self.assertRaises(relationalIR.StratificationError, compileAlgorithim, algorithims.IsNotStratified, {'variable':8, 'heap':8, 'field':8})


if __name__ == '__main__':
	unittest.main()
