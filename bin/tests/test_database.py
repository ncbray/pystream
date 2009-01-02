from __future__ import absolute_import

import unittest


import analysis.database.structure as structure
import analysis.database.tupleset as tupleset
import analysis.database.tuplemap as tuplemap
import analysis.database.lattice as lattice


class TestStructureSchema(unittest.TestCase):
	def testCreate(self):
		intSchema = structure.TypeSchema(int)
		s = structure.StructureSchema(('a', intSchema),
				       ('b', intSchema),
				       ('c', intSchema))

		self.assertEqual(s.field('b'), intSchema)
		self.assertRaises(structure.base.SchemaError, s.field, 'z')

	def testBadCreate(self):
		intSchema = structure.TypeSchema(int)
		self.assertRaises(structure.base.SchemaError, structure.StructureSchema, ('a', intSchema), ('b', intSchema), ('a', intSchema))

	def testValidate(self):
		intSchema = structure.TypeSchema(int)
		s = structure.StructureSchema(('a', intSchema), ('b', intSchema), ('c', intSchema))

		self.assert_(s.validateNoRaise((1, 2, 3)))
		self.assert_(not s.validateNoRaise((1, 2, 3.0)))
		self.assert_(not s.validateNoRaise((1, 2)))
		self.assert_(not s.validateNoRaise((1, 2, 3, 4)))


class TestTupleSet(unittest.TestCase):
	def setUp(self):
		intSchema = structure.TypeSchema(int)
		s = structure.StructureSchema(('a', intSchema), ('b', intSchema))
		schema = tupleset.TupleSetSchema(s)
		self.schema = schema


	def testInit(self):
		ts = self.schema.instance()
		ts.add(1, 2)
		ts.add(1, 3)
		ts.add(1, 2)

		self.assertEqual(len(ts), 2)
		for a, b in ts:
			self.assertEqual(a, 1)
			self.assert_(b == 2 or b == 3)

		ts.remove(1, 2)
		self.assertEqual(len(ts), 1)
		ts.remove(1, 3)
		self.assertEqual(len(ts), 0)

		self.assertRaises(structure.base.DatabaseError, ts.remove, 1, 2)





class TestTupleMap(unittest.TestCase):
	def setUp(self):
		intSchema = structure.TypeSchema(int)
		
		s = structure.StructureSchema(('a', intSchema), ('b', intSchema))
		v = lattice.setUnionSchema
		
		schema = tuplemap.TupleMapSchema(s, v)
		self.schema = schema


	def testAdd(self):
		m = self.schema.instance()
		
		m[(1, 2)].add(1)
		m[(1, 2)].add(2)
		m[(1, 3)].add(1)

		self.assertEqual(len(m), 2)

		for key, data in m:
			if key == (1, 2):
				self.assertEqual(data, set((1, 2)))
			elif key == (1, 3):
				self.assertEqual(data, set((1,)))
			else:
				self.fail()


	def testForget(self):
		m = self.schema.instance()
		m[(1, 2)].add(1)
		m[(1, 2)].add(2)
		m[(1, 3)].add(1)
		m[(1, 3)].add(3)

		self.assertEqual(len(m), 2)

		f = m.forget()
		self.assertEqual(f, set((1, 2, 3)))
