import sys

from language.python import ast
from language.python.simplecodegen import SimpleCodeGen

from util.asttools.astpprint import pprint
from util.asttools import symbols
Symbol = symbols.Symbol

from ... import intrinsics

import cStringIO

from util.io import filesystem

from . import existingtransform

def existingSymbol(name):
	return ast.Existing(symbols.Extract(symbols.Symbol(name)))

def existingConstant(value):
	return ast.Existing(symbols.Extract(value))

uniformBindTemplate = ast.Discard(
	ast.Call(
		ast.GetAttr(
			symbols.Symbol('self'),
			existingSymbol('methodName')
		),
		[existingSymbol('name'), symbols.Symbol('value')],
		[], None, None
	)
)

def bindUniform(compiler, self, name, t, value):
	bind = symbols.SymbolRewriter(compiler.extractor, uniformBindTemplate)
	methodName = "bind_uniform_" + t.__name__
	return bind.rewrite(self=self, methodName=methodName, name=name, value=value)

typeCheckTemplate = ast.Call(
	ast.GetGlobal(existingConstant('isinstance')),
	[symbols.Symbol('root'), existingSymbol('type')],
	[], None, None
)

typeBindTemplate = ast.Suite([
])

# self -> the serializing class
# root -> the current uniform local
def serializeUniformNode(compiler, translator, self, holdingSlot, refs, root):
	check = symbols.SymbolRewriter(compiler.extractor, typeCheckTemplate)

	types = sorted(set([ref.xtype.obj.pythonType() for ref in refs]))

	# The tree transform should guarantee there's only one object per type
	typeLUT = {}
	for ref in refs:
		t = ref.xtype.obj.pythonType()
		assert t not in typeLUT
		typeLUT[t] = ref

	assert len(types) > 0

	if len(types) == 1:
		t = types[0]
		return handleUniformType(compiler, translator, self, holdingSlot, typeLUT[t], root, t)
	else:
		switches = []
		for t in types:
			cond  = check.rewrite(root=root, type=t)

			body     = handleUniformType(compiler, translator, self, holdingSlot, typeLUT[t], root, t)

			switches.append((cond, ast.Suite(body)))

		current = ast.Suite([ast.Assert(ast.Existing(compiler.extractor.getObject(False)), None)])

		for cond, suite in reversed(switches):
			current = ast.Switch(ast.Condition(ast.Suite([]), cond), suite, ast.Suite([current]))

		return [current]

uniformGetTemplate = ast.Assign(
	ast.Call(
		ast.GetAttr(
			ast.GetAttr(
				existingSymbol('cls'),
				existingSymbol('attr')
				),
			existingConstant('__get__')
		),
		[Symbol('root')], [], None, None
	),
	[Symbol('target')]
)

def classAttrFromField(compiler, field):
	assert field.type == 'Attribute', field

	name = field.name.pyobj
	descriptor = compiler.slots.reverse[name]
	cls  = descriptor.__objclass__
	attr = descriptor.__name__

	# HACK may have been renamed...
	assert cls.__dict__[attr] is descriptor, "Can't find original descriptor!"

	return cls, attr

def handleUniformType(compiler, translator, self, holdingSlot, ref, root, t):
	statements = []

	# Find the group name
	holdingSlot = translator.compatible[holdingSlot]

	structInfo = translator.ioRefInfo.get(holdingSlot)

	if structInfo:
		if structInfo.multipleTypes():
			sub = structInfo.lut.subpools['type']
			name = sub.name
			uid  = translator.typeIDs[t]
			uidO = compiler.extractor.getObject(uid)

			statements.append(bindUniform(compiler, self, name, int, ast.Existing(uidO)))

		if intrinsics.isIntrinsicType(t):
			if t in intrinsics.samplerTypes:
				sg = translator.samplerGroup(ref)
				assert sg.unique
				name = sg.name
			else:
				sub = structInfo.lut.subpools[t]
				name = sub.name
			statements.append(bindUniform(compiler, self, name, t, root))

		# TODO fields?

	get = symbols.SymbolRewriter(compiler.extractor, uniformGetTemplate)

	# TODO mutually exclusive?

	for field in ref.slots.itervalues():
		if not intrinsics.isIntrinsicSlot(field):
			if field.slotName.type != 'Attribute': continue

			cls, attr = classAttrFromField(compiler, field.slotName)

			assert issubclass(t, cls), (ref, field)

			target  = ast.Local('bogus')

			# Load the field
			assign = get.rewrite(cls=cls, attr=attr, root=root, target=target)
			statements.append(assign)

			# Recurse
			statements.extend(serializeUniformNode(compiler, translator, self, field, field, target))

	return statements

uniformCodeTemplate = ast.Code(
	'bindUniforms',
	ast.CodeParameters(
		None,
		symbols.Symbol('args'),
		['self', 'shader'], [], None, None, []),
	symbols.Symbol('body')
)

def bindUniforms(compiler, translator, uniformSlot):
	code = symbols.SymbolRewriter(compiler.extractor, uniformCodeTemplate)

	self   = ast.Local('self')
	shader = ast.Local('shader')

	if uniformSlot.annotation.references:
		uniformRefs = uniformSlot.annotation.references.merged
		body = ast.Suite(serializeUniformNode(compiler, translator, self, uniformSlot, uniformRefs, shader))
	else:
		# No uniforms are used.
		body = ast.Suite([])

	return code.rewrite(args=[self, shader], body=body)


streamCodeTemplate = ast.Code(
	'bindStreams',
	ast.CodeParameters(
		None,
		symbols.Symbol('args'),
		symbols.Symbol('argnames'),
		[], None, None, []),
	symbols.Symbol('body')
)

streamBindTemplate = ast.Discard(
	ast.Call(
		ast.GetAttr(symbols.Symbol('self'), existingSymbol('attr')),
		[existingSymbol('shaderName'), symbols.Symbol('name')],
		[], None, None
	)
)

def bindStreams(compiler, translator, context):
	code = symbols.SymbolRewriter(compiler.extractor, streamCodeTemplate)
	bind = symbols.SymbolRewriter(compiler.extractor, streamBindTemplate)

	originalParams = context.originalParams
	currentParams = context.code.codeparameters

	self   = ast.Local('self')
	streams   = []

	statements = []

	for original in originalParams.params[2:]:
		root = ast.Local(original.name)
		streams.append(root)

		ioname = context.shaderdesc.fields[original]
		if ioname in translator.liveInputs:

			refs = original.annotation.references.merged
			assert len(refs) == 1
			obj = refs[0]
			assert intrinsics.isIntrinsicObject(obj)
			t = obj.xtype.obj.pythonType()
			attr = "bind_stream_" + t.__name__

			structInfo = translator.ioRefInfo.get(ioname)

			shaderName = structInfo.lut.subpools[t].name

			statements.append(bind.rewrite(self=self, attr=attr, shaderName=shaderName, name=root))

#	for original, current in zip(originalParams.params, currentParams.params)[2:]:
#		root = ast.Local(original.name)
#		streams.append(root)
#
#		if current.isDoNotCare(): continue
#
#		refs = current.annotation.references.merged
#		assert len(refs) == 1
#		obj = refs[0]
#		assert intrinsics.isIntrinsicObject(obj)
#		t = obj.xtype.obj.pythonType()
#		attr = "bind_stream_" + t.__name__
#
#		structInfo = translator.serializationInfo(current)
#		assert structInfo is not None
#
#		shaderName = structInfo.intrinsics[t].decl.name
#
#		statements.append(bind.rewrite(self=self, attr=attr, shaderName=shaderName, name=root))

	body = ast.Suite(statements)

	args = [self]
	args.extend(streams)
	names = [arg.name for arg in args]

	return code.rewrite(args=args, argnames=names, body=body)

classTemplate = ast.ClassDef(
	symbols.Symbol('className'),
	[ast.GetAttr(
		ast.GetGlobal(existingConstant('pystreamruntime')),
		existingConstant('BaseCompiledShader')
	)],
	ast.Suite([
		ast.Assign(existingSymbol('original'), [ast.Local('original')]),
		ast.Assign(existingSymbol('vsCode'), [ast.Local('vs')]),
		ast.Assign(existingSymbol('fsCode'), [ast.Local('fs')]),
		ast.FunctionDef('bindUniforms', symbols.Symbol('bindUniforms'), []),
		ast.FunctionDef('bindStreams',  symbols.Symbol('bindStreams'), [])
	]),
	[]
)


callback = ast.Local('callback')
# Not a FunctionDef, as the symbol rewriter would not be able to reach through the (shared) code
registerTemplate = ast.Code(
	'register',
	ast.CodeParameters(
		None,
		[callback],
		['callback'], [], None, None, []),
	ast.Suite([
			ast.Discard(
					ast.Call(
							callback,
							[ast.GetGlobal(existingSymbol('className')),],
							[], None, None)
			)
	])
)



def generateBindingClass(compiler, prgm, shaderprgm, translator):
	className = "Compiled%s" % shaderprgm.name

	# TODO original as the actual class object?
	original = shaderprgm.name

	uniformSlot = shaderprgm.vscontext.originalParams.params[0]
	if not uniformSlot.annotation.references:
		# May be unused in vs.
		uniformSlot = shaderprgm.fscontext.originalParams.params[0]

	uniformCode = bindUniforms(compiler, translator, uniformSlot)
	streamCode  = bindStreams(compiler, translator, shaderprgm.vscontext)

	vsCode = shaderprgm.vscontext.shaderCode
	fsCode = shaderprgm.fscontext.shaderCode

	code = symbols.SymbolRewriter(compiler.extractor, classTemplate)
	cdef = code.rewrite(className=className, original=original, vsCode=vsCode, fsCode=fsCode, bindUniforms=uniformCode, bindStreams=streamCode)
	cdef = existingtransform.evaluateAST(compiler, cdef)

	register = symbols.SymbolRewriter(compiler.extractor, registerTemplate)
	rdef = register.rewrite(className=className)

	buffer = cStringIO.StringIO()
	SimpleCodeGen(buffer).process(cdef)
	SimpleCodeGen(buffer).process(rdef)

	s = buffer.getvalue()

	# HACK for imports
	s = "import pystreamruntime\nimport tests.full.physics\n\n" + s

	print
	print s
	print

	filesystem.writeData('summaries/shaders', shaderprgm.name, 'py', s)

	return cdef
