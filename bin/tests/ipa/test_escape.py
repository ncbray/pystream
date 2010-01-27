from . base import TestIPABase

from analysis.ipa import escape
from analysis.ipa.escape import objectescape
from analysis.ipa.constraints import qualifiers

class TestObjectEscape(TestIPABase):
	def setUp(self):
		TestIPABase.setUp(self)
		self.context  = self.makeContext()

	def assertFlags(self, objectName, expected):
		obj = self.context.region.object(objectName)
		self.assertEqual(obj.flags, expected, 'expected %r.flags to be %s not %s' % (obj, objectescape.repr(expected), objectescape.repr(obj.flags)))

	def testReturn(self):
		t1  = self.local(self.context, 'temp1')
		r  = self.local(self.context, 'return')
		self.context.returns.append(r)

		o1 = self.const('o1', qualifiers.HZ)
		t1.updateSingleValue(o1)

		self.context.assign(t1, r)

		objectescape.process(self.context)

		self.assertFlags(o1, objectescape.escapeReturn)

	def testReturnStore(self):
		t1  = self.local(self.context, 'temp1')
		t2  = self.local(self.context, 'temp2')
		n   = self.local(self.context, 'name')

		r  = self.local(self.context, 'return')
		self.context.returns.append(r)

		no = self.const('nameObj', qualifiers.HZ)
		n.updateSingleValue(no)

		o1 = self.const('o1', qualifiers.HZ)
		t1.updateSingleValue(o1)

		o2 = self.const('o2', qualifiers.HZ)
		t2.updateSingleValue(o2)

		self.context.store(t2, t1, 'Array', n)
		self.context.assign(t1, r)

		objectescape.process(self.context)

		self.assertFlags(o1, objectescape.escapeReturn)
		self.assertFlags(o2, objectescape.escapeReturn)

	def testParamStore(self):
		p0  = self.local(self.context, 'param0')
		self.context.params.append(p0)
		t1  = self.local(self.context, 'temp1')
		n   = self.local(self.context, 'name')

		no = self.const('nameObj', qualifiers.HZ)
		n.updateSingleValue(no)

		o1 = self.const('o1', qualifiers.HZ)
		t1.updateSingleValue(o1)

		o2 = self.const('o2', qualifiers.DN)
		p0.updateSingleValue(o2)

		self.context.store(t1, p0, 'Attribute', n)

		objectescape.process(self.context)

		self.assertFlags(o1, objectescape.escapeParam)
		self.assertFlags(o2, objectescape.escapeParam)

	def testParamStoreReturn(self):
		p0  = self.local(self.context, 'param0')
		self.context.params.append(p0)
		t1  = self.local(self.context, 'temp1')
		n   = self.local(self.context, 'name')
		r  = self.local(self.context, 'return')
		self.context.returns.append(r)

		no = self.const('nameObj', qualifiers.HZ)
		n.updateSingleValue(no)

		o1 = self.const('o1', qualifiers.HZ)
		t1.updateSingleValue(o1)

		o2 = self.const('o2', qualifiers.DN)
		p0.updateSingleValue(o2)

		self.context.store(t1, p0, 'Attribute', n)
		self.context.assign(t1, r)

		objectescape.process(self.context)

		self.assertFlags(o1, objectescape.escapeParam|objectescape.escapeReturn)
		self.assertFlags(o2, objectescape.escapeParam)
