from translator import intrinsics
from language.glsl import ast as glsl

# HACK for debugging
from language.glsl import codegen

# Slot implementation describes the structure for implementing the slot
# type      .t
# reference .r (merge w/ int?)
# float(n)  .f
# int(n)    .i
# bool(n)   .b (merge w/ int?)
# sampler   .s
# If there is only one attribute, inline it.

class SlotStruct(object):
	def __init__(self, objs):

		self.poolinfo = objs

		self.singleType = objs.singleType()

		self.type  = False
		self.ref   = False
		self.count = {float:0, int:0, bool:0}

		if objs.objects:
			self.ref = True

		intrinsicType = None

		for group in (objs.intrinsics, objs.constants):
			for obj in group:
				t = obj.xtype.obj.pythonType()
				if intrinsicType is None:
					intrinsicType = t
				elif intrinsicType is not t:
					self.type = True

				ct, cn = intrinsics.typeComponents[t]
				self.count[ct] = max(self.count.get(ct, 0), cn)

		self.type = self.type or intrinsicType and self.ref

		self._signature = (self.type, self.ref, self.count[float], self.count[int], self.count[bool])

		self.generateAST()

	def generateAST(self):
		if not self.type:
			# This slot is a single field, and can be inlined.
			if self.ref:
				t = int
			else:
				t = self.singleType
			self.ast = intrinsics.intrinsicTypeNodes[t]
			self.inlined = True
		else:
			# This slot is a union of fields, and will be implemented using a struct.
			fields = []

			if self.type:
				fields.append(glsl.VariableDecl(intrinsics.intrinsicTypeNodes[int], 't', None))
			if self.ref:
				fields.append(glsl.VariableDecl(intrinsics.intrinsicTypeNodes[int], 'r', None))
			if self.count[float]:
				fields.append(glsl.VariableDecl(intrinsics.componentTypeNodes[(float, self.count[float])], 'f', None))
			if self.count[int]:
				fields.append(glsl.VariableDecl(intrinsics.componentTypeNodes[(int, self.count[int])], 'i', None))
			if self.count[bool]:
				fields.append(glsl.VariableDecl(intrinsics.componentTypeNodes[(bool, self.count[bool])], 'f', None))

			self.ast = glsl.StructureType('unknownStruct', fields)
			self.inlined = False

	def signature(self):
		return self._signature

	def assign(self, src, dst, filter=None):
		assert filter is None



	def dump(self):
		print "="*60

		self.poolinfo.dump()

		print "t", self.type
		print "r", self.ref
		for t, c in self.count.iteritems():
			print t.__name__, c
		print

		print codegen.evaluateCode(None, self.ast)
		print
