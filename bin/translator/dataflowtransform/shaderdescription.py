from .. import intrinsics
from language.glsl import ast as glsl

class IOInfo(object):
	__slots__ = 'uniforms', 'inputs', 'outputs', 'builtin', 'same'

	def __init__(self):
		self.uniforms = set()
		self.inputs   = set()
		self.outputs  = set()

		self.builtin  = {}

		self.same     = {}

class ProgramDescription(object):
	__slots__ = 'prgm', 'vscontext', 'fscontext', 'mapping', 'vs2fs', 'ioinfo'

	def __init__(self, prgm, vscontext, fscontext):
		self.prgm = prgm
		self.vscontext = vscontext
		self.fscontext = fscontext

		self.vs2fs = {}

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

			assert tree.lcl not in self.vs2fs
			self.vs2fs[tree.lcl] = field

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

	def linkVarying(self):
		# Generate fs input => vs output mappings
		# This is a reverse mapping, as that makes subsequent operations easier

		vsoutputs = self.vscontext.shaderdesc.outputs.varying
		fsparams = self.fscontext.originalParams.params[2:]

		assert len(vsoutputs) == len(fsparams)

		mapping = {}

		for output, param in zip(vsoutputs, fsparams):
			self.handleOutputToLocal(output, param, mapping)

		self.mapping = mapping




	def markTraverse(self, refs, marks):
		for ref in refs:
			for field in ref:
				self.markField(field, marks)

	def markEquivilents(self, field, marks):
		lcls = []
		for fields in (self.vscontext.shaderdesc.fields, self.fscontext.shaderdesc.fields):
			if field in fields:
				lcl = fields[field]
				marks.add(lcl)
				lcls.append(lcl)

		if len(lcls) > 1:
			self.ioinfo.same[lcls[0]] = lcls[1]

	def markField(self, field, marks):
		if field not in self.ioinfo.uniforms and not intrinsics.isIntrinsicSlot(field):
			marks.add(field)
			self.markEquivilents(field, marks)

			self.markTraverse(field, marks)

	def markParam(self, param, marks):
		if param.isDoNotCare(): return
		marks.add(param)
		self.markTraverse(param.annotation.references.merged, marks)


	def markParams(self, context):
		params = context.originalParams
		self.markParam(params.params[0], self.ioinfo.uniforms)

		for param in params.params[1:]:
			self.markParam(param, self.ioinfo.inputs)

	def makeIOInfo(self):
		self.ioinfo = IOInfo()

		self.markParams(self.vscontext)
		self.markParams(self.fscontext)

		self.vscontext.shaderdesc.outputs.updateInfo(self.ioinfo)
		self.fscontext.shaderdesc.outputs.updateInfo(self.ioinfo)


		fsfields = self.fscontext.shaderdesc.fields
		for src, dst in self.vs2fs.iteritems():
			dst = fsfields.get(dst, dst)
			self.ioinfo.same[src] = dst

		return self.ioinfo

class ShaderDescription(object):
	__slots__ = 'fields', 'outputs'

class OutputBase(object):
	__slots__ = ()

	def updateInfo(self, info):
		info.outputs.update(self.collectUsed())
		self.getBuiltin(info)


class VSOutputDescription(OutputBase):
	__slots__ = 'position', 'varying'

	def collectUsed(self):
		used = set()
		self.position.collectUsed(used)

		for var in self.varying:
			var.collectUsed(used)

		return used

	def getBuiltin(self, info):
		vec4T = intrinsics.intrinsicTypeNodes[intrinsics.vec.vec4]
		info.builtin[self.position.lcl] = glsl.OutputDecl(None, False, False, True, vec4T, 'gl_Position')

class FSOutputDescription(OutputBase):
	__slots__ = 'colors', 'depth'

	def collectUsed(self):
		used = set()
		if self.depth:
			self.depth.collectUsed(used)

		for color in self.colors:
			color.collectUsed(used)

		return used

	def getBuiltin(self, info):
		if self.depth:
			floatT = intrinsics.intrinsicTypeNodes[float]
			info.builtin[self.position.lcl] = glsl.OutputDecl(None, False, False, True, floatT, 'gl_Depth')


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
