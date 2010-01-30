from .. import intrinsics

class ShaderDescription(object):
	__slots__ = 'fields', 'outputs'

class VSOutputDescription(object):
	__slots__ = 'position', 'varying'

	def collectUsed(self):
		used = set()
		self.position.collectUsed(used)

		for var in self.varying:
			var.collectUsed(used)

		return used

class FSOutputDescription(object):
	__slots__ = 'colors', 'depth'

	def collectUsed(self):
		used = set()
		if self.depth:
			self.depth.collectUsed(used)

		for color in self.colors:
			color.collectUsed(used)

		return used

class TreeNode(object):
	def __init__(self, lcl):
		self.lcl    = lcl
		self.fields = {}
		self.used   = intrinsics.isIntrinsicType(self.pythonType())

	def pythonType(self):
		refs = self.lcl.annotation.references.merged
		pt = refs[0].xtype.obj.pythonType()
		for ref in refs[1:]:
			assert pt is ref.xtype.obj.pythonType()
		return pt

	def field(self, fieldName, lcl):
		tree = TreeNode(lcl)
		self.fields[fieldName] = tree
		return tree

	def collectUsed(self, used):
		if self.used:
			used.add(self.lcl)
		for child in self.fields.itervalues():
			child.collectUsed(used)

	def extractTuple(self):
		array = {}
		length = None

		for fieldName, child in self.fields.iteritems():
			if fieldName.type == 'LowLevel':
				if fieldName.name.pyobj == 'length':
					length = child.lcl.annotation.references.merged[0].xtype.obj.pyobj

			elif fieldName.type == 'Array':
				array[fieldName.name.pyobj] = child
			else:
				assert False, fieldName

		assert len(array) == length

		return tuple([array[i] for i in range(length)])
