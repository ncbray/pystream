import unittest

from analysis.ipa.ipanalysis import IPAnalysis
from analysis.ipa.constraints import flow, qualifiers

from language.python import program

from analysis.storegraph.canonicalobjects import CanonicalObjects

class MockObjectName(object):
	__slots__ = '_obj', 'qualifier'
	def __init__(self, obj, qualifier):
		self._obj = obj
		self.qualifier = qualifier

	def cpaType(self):
		return self._obj

	def obj(self):
		return self._obj

	def pyObj(self):
		return self._obj.pyobj

	def isObjectName(self):
		return True

	def __repr__(self):
		return "MockObjectName(%r, %s)" % (self._obj, self.qualifier)

class MockExtractor(object):
	def __init__(self):
		self.cache = {}

	def getObject(self, pyobj):
		key = (type(pyobj), pyobj)
		result = self.cache.get(key)
		if result is None:
			result = program.Object(pyobj)
			self.cache[key] = result
		return result

class TestFlowConstraints(unittest.TestCase):
	def setUp(self):
		self.extractor = MockExtractor()
		self.canonical = CanonicalObjects()
		existingPolicy = None
		externalPolicy = None

		self.analysis = IPAnalysis(self.extractor, self.canonical, existingPolicy, externalPolicy)
		self.context  = self.analysis.getContext(None)

	def local(self, name, *values):
		lcl = self.context.local(name)
		if values: lcl.updateValues(frozenset(values))
		return lcl

	def assertIsInstance(self, obj, cls):
		self.assert_(isinstance(obj, cls), "expected %r, got %r" % (cls, type(obj)))

	def const(self, pyobj):
		obj = self.extractor.getObject(pyobj)
		return MockObjectName(obj, qualifiers.HZ)

	def testStore(self):
		o = self.const('obj')
		n = self.const('name')
		v = self.const('value')

		src       = self.local(0, v)
		dst       = self.local(1, o)
		fieldtype = 'Attribute'
		fieldname = self.local(2, n)

		self.context.constraint(flow.StoreConstraint(src, dst, fieldtype, fieldname))

		# Check that a constraint was created
		self.assertEqual(len(self.context.constraints), 2)
		concrete = self.context.constraints[1]
		self.assertIsInstance(concrete, flow.CopyConstraint)

		field = concrete.dst

		# Check that the target is the right field
		self.assertEqual(field, self.context.field(o, fieldtype, n.obj()))

		# Check that the value propagated
		self.assertEqual(field.values, frozenset([v]))


	def testLoad(self):
		o = self.const('obj')
		n = self.const('name')
		v = self.const('value')

		src       = self.local(0, o)
		fieldtype = 'Attribute'
		fieldname = self.local(1, n)
		dst       = self.local(2)

		field = self.context.field(o, fieldtype, n.obj())
		field.updateSingleValue(v)

		self.context.constraint(flow.LoadConstraint(src, fieldtype, fieldname, dst))

		# Check that a constraint was created
		self.assertEqual(len(self.context.constraints), 2)
		concrete = self.context.constraints[1]
		self.assertIsInstance(concrete, flow.CopyConstraint)

		# Check that the source is the right field
		self.assertEqual(concrete.src, field)

		# Check that the value propagated
		self.assertEqual(dst.values, field.values)


	def checkTemplate(self, value, null):
		o = self.const('obj')
		n = self.const('name')
		v = self.const('value')

		src       = self.local(0, o)
		fieldtype = 'Attribute'
		fieldname = self.local(1, n)
		dst       = self.local(2)

		field = self.context.field(o, fieldtype, n.obj())
		self.assertEqual(field.null, True)

		if not null: field.clearNull()
		if value: field.updateSingleValue(v)

		self.context.constraint(flow.CheckConstraint(src, fieldtype, fieldname, dst))

		# Check that a constraint was created
		self.assertEqual(len(self.context.constraints), 2)
		concrete = self.context.constraints[1]
		self.assertIsInstance(concrete, flow.ConcreteCheckConstraint)

		# Check that the source is the right field
		self.assertEqual(concrete.src, field)

		expected = []
		if null: expected.append(self.context.allocatePyObj(False))
		if value: expected.append(self.context.allocatePyObj(True))

		# Check that the value propagated
		self.assertEqual(dst.values, frozenset(expected))


	def testCheckBoth(self):
		self.checkTemplate(True, True)

	def testCheckValue(self):
		self.checkTemplate(True, False)

	def testCheckNull(self):
		self.checkTemplate(False, True)

	def testCheckNeither(self):
		self.checkTemplate(False, False)
