import unittest
from analysis.ipa.ipanalysis import IPAnalysis
from analysis.ipa.constraints import qualifiers
from analysis.storegraph.canonicalobjects import CanonicalObjects
from language.python import program

from application.context import CompilerContext

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

class MockSignature(object):
	def __init__(self):
		self.code = None

class TestIPABase(unittest.TestCase):
	def setUp(self):
		self.compiler  = CompilerContext(None)
		self.extractor = MockExtractor()
		self.compiler.extractor = self.extractor
		self.canonical = CanonicalObjects()
		existingPolicy = None
		externalPolicy = None

		self.analysis = IPAnalysis(self.compiler, self.canonical, existingPolicy, externalPolicy)

	def local(self, context, name, *values):
		lcl = context.local(name)
		if values: lcl.updateValues(frozenset(values))
		return lcl

	def assertIsInstance(self, obj, cls):
		self.assert_(isinstance(obj, cls), "expected %r, got %r" % (cls, type(obj)))

	def const(self, pyobj, qualifier=qualifiers.HZ):
		obj = self.extractor.getObject(pyobj)
		xtype = self.canonical.existingType(obj)
		return self.analysis.objectName(xtype, qualifier)

	def makeContext(self):
		return self.analysis.getContext(MockSignature())
