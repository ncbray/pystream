from . base import AbstractCode

from language.python.ast import *
import language.base.annotation as annotation
import util.calling

### BEGIN support code ###

class VSContext(object):
	__slots__ = 'position', 'point_size'

# Depth is inout?
class FSContext(object):
	__slots__ = 'coord', 'front_facing', 'colors', 'depth'

### END support code ###

# HACK
from language.python.annotations import CodeAnnotation
emptyShaderProgramAnnotation = CodeAnnotation(None, False, False, None, None, None, None, None, None, None, None)

def createShaderProgram(extractor):
	name = "shader_program"

	selfparam = None
	parameters = (Local('vs'), Local('fs'), Local('shader'))
	parameternames = ('vs', 'fs', 'shader')
	streams = Local('streams')
	returnparams = [Local('return_shader_program')]

	codeparameters = CodeParameters(selfparam, parameters, parameternames, streams, None, returnparams)

	vscontext = Local('vs_context')
	fscontext = Local('fs_context')

	vsout = Local('vs_return')
	fsout = Local('fs_return')

	vsCall     = Assign(Call(parameters[0], (parameters[2], vscontext), [], streams, None), [vsout])
	fsCall     = Assign(Call(parameters[1], (parameters[2], fscontext), [], vsout, None), [fsout])

	junk = []

	# Setup the VSContext
	junk.append(Assign(Allocate(Existing(extractor.getObject(VSContext))), [vscontext]))

	# Setup the FSContext
	junk.append(Assign(Allocate(Existing(extractor.getObject(FSContext))), [fscontext]))

	junk.append(Return([Existing(extractor.getObject(None))]))
	#junk.append(Discard(GetAttr(fsout, Existing(extractor.getObject('colors')))))

	sp = ShaderProgram(name, codeparameters, vsCall, fsCall, junk)
	return sp

class ShaderProgram(AbstractCode):
	__fields__ = """name:str codeparameters:CodeParameters vsCall:Statement fsCall:Statement junk:Statement*"""

	__shared__ = True

	__emptyAnnotation__ = emptyShaderProgramAnnotation

	def codeName(self):
		return self.name

	def setCodeName(self, name):
		self.name = name

	def codeParameters(self):
		return self.codeparameters.codeParameters()

	def extractConstraints(self, ce):
		ce(self.vsCall)
		ce(self.fsCall)
		ce(self.junk)

	def vertexShaderCode(self):
		# HACK assumes the call is a DirectCall
		return self.vsCall.expr.code

	def fragmentShaderCode(self):
		# HACK assumes the call is a DirectCall
		return self.fsCall.expr.code


	# Used to find the slots that need to be read
	def crawlObj(self, obj, slots):
		if not obj.xtype.isExisting() and not obj.xtype.isExternal():
			for slotName, slot in obj.slots.iteritems():
				if slot not in slots:
					slots.add(slot)
					for ref in slot:
						self.crawlObj(ref, slots)

	def crawlLocal(self, lcl, cindex, slots):
		refs = lcl.annotation.references[1][cindex]
		for ref in refs:
			self.crawlObj(ref, slots)

	# These are reads that will not be found by the analysis.
	def abstractReads(self):
		fsout = self.fsCall.lcls[0]

		reads = []
		for cindex, context in enumerate(self.annotation.contexts):
			slots = set()

			self.crawlLocal(fsout, cindex, slots)

			# HACK
			for stmt in self.junk:
				if isinstance(stmt, Assign):
					assert len(stmt.lcls) == 1
					self.crawlLocal(stmt.lcls[0], cindex, slots)


			reads.append(annotations.annotationSet(slots))

		return annotations.makeContextualAnnotation(reads)