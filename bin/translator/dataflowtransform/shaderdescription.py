from .. import intrinsics

class ProgramDescription(object):
	__slots__ = 'prgm', 'vscontext', 'fscontext'

	def __init__(self, prgm, vscontext, fscontext):
		self.prgm = prgm
		self.vscontext = vscontext
		self.fscontext = fscontext


	def handleOutputToLocal(self, tree, lcl, mapping):
		if tree.used:
			assert lcl not in mapping
			mapping[lcl] = tree.lcl

		refs = lcl.annotation.references.merged
		self.traverse(tree, refs, mapping)

	def handleOutputToField(self, tree, field, mapping):
		if tree.used:
			assert field not in mapping
			mapping[field] = tree.lcl

		refs = field
		self.traverse(tree, refs, mapping)


	def traverse(self, tree, refs, mapping):
		for fieldName, child in tree.fields.iteritems():
			for obj in refs:
				if fieldName in obj.slots:
					self.handleOutputToField(child, obj.slots[fieldName], mapping)

	def link(self):
		#self.linkUniform()
		self.linkVarying()

#	def linkUniform(self):
#		# Generate uniform <=> uniform mappings
#		vskeys = set(self.vscontext.objectInfo.iterkeys())
#		fskeys = set(self.fscontext.objectInfo.iterkeys())
#		common = vskeys.intersection(fskeys)
#
#		vs2fs = {}
#		fs2vs = {}
#
#		for key in common:
#			vsxtype = self.vscontext.objectInfo[key].result
#			fsxtype = self.fscontext.objectInfo[key].result
#			print key
#			print vsxtype
#			print fsxtype
#			print
#
#			vs2fs[vsxtype] = fsxtype
#			fs2vs[fsxtype] = vsxtype

	def linkVarying(self):
		# Generate fs input => vs output mappings
		# This is a reverse mapping, as that makes subsequent operations easier

		vsoutputs = self.vscontext.shaderdesc.outputs.varying
		fsparams = self.fscontext.originalParams.params[2:]

		assert len(vsoutputs) == len(fsparams)

		mapping = {}

		for output, param in zip(vsoutputs, fsparams):
			self.handleOutputToLocal(output, param, mapping)



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
