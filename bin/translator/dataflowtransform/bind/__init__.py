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

# TODO mask?
def serializeUniformNode(compiler, self, tree, root):
	check = symbols.SymbolRewriter(compiler.extractor, typeCheckTemplate)

	types = sorted(set([k.xtype.obj.pythonType() for k in tree.objMasks.iterkeys()]))
	assert len(types) > 0

	if len(types) == 1:
		return handleUniformType(compiler, self, tree, root, types[0])
	else:
		switches = []
		for t in types:
			cond  = check.rewrite(root=root, type=t)

			# Bind an integer that indicated the type of the object?
			value    = ast.Existing(compiler.extractor.getObject(len(types)))
			bindType = bindUniform(compiler, self, 'bogus', int, value)
			body     = handleUniformType(compiler, self, tree, root, t)

			switches.append((cond, ast.Suite([bindType, body])))

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

def handleUniformType(compiler, self, tree, root, t):
	statements = []

	if intrinsics.isIntrinsicType(t):
		statements.append(bindUniform(compiler, self, tree.name, t, root))

	get = symbols.SymbolRewriter(compiler.extractor, uniformGetTemplate)

	# TODO mutually exclusive?

	for field, child in tree.fields.iteritems():
		if not intrinsics.isIntrinsicField(field):

			assert field.type == 'Attribute'

			name = field.name.pyobj
			descriptor = compiler.slots.reverse[name]
			cls  = descriptor.__objclass__
			attr = descriptor.__name__

			# HACK may have been renamed...
			assert cls.__dict__[attr] is descriptor, "Can't find original descriptor!"

			# This field is obviously not on the object
			if not issubclass(t, cls): continue

			target  = ast.Local('bogus')

			# Load the field
			assign = get.rewrite(cls=cls, attr=attr, root=root, target=target)
			statements.append(assign)

			# Recurse
			statements.extend(serializeUniformNode(compiler, self, child, target))

	return statements

uniformCodeTemplate = ast.Code(
	'bindUniforms',
	ast.CodeParameters(
		None,
		symbols.Symbol('args'),
		['self', 'shader'], [], None, None, []),
	symbols.Symbol('body')
)

def bindUniforms(compiler, uniforms):
	code = symbols.SymbolRewriter(compiler.extractor, uniformCodeTemplate)

	self   = ast.Local('self')
	shader = ast.Local('shader')
	body = ast.Suite(serializeUniformNode(compiler, self, uniforms, shader))

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

def bindStreams(context):
	code = symbols.SymbolRewriter(context.compiler.extractor, streamCodeTemplate)
	bind = symbols.SymbolRewriter(context.compiler.extractor, streamBindTemplate)

	self   = ast.Local('self')
	streams   = [ast.Local(param.name) for param in context.code.codeparameters.params[2:]]

	statements = []

	for tree, root in zip(context.trees.inputs, streams):
		shaderName = tree.name

		# Unused?
		if shaderName is None: continue

		assert len(tree.objMasks) == 1
		obj = tree.objMasks.keys()[0]
		assert intrinsics.isIntrinsicObject(obj)
		t = obj.xtype.obj.pythonType()
		attr = "bind_stream_" + t.__name__

		statements.append(bind.rewrite(self=self, attr=attr, shaderName=shaderName, name=root))

	body = ast.Suite(statements)

	args = [self]
	args.extend(streams)
	names = [arg.name for arg in args]

	return code.rewrite(args=args, argnames=names, body=body)

classTemplate = ast.ClassDef(
	'CompiledShader',
	[ast.GetAttr(
		ast.GetGlobal(existingConstant('pystreamruntime')),
		existingConstant('BaseCompiledShader')
	)],
	ast.Suite([
		ast.Assign(existingSymbol('vsCode'), [ast.Local('vs')]),
		ast.Assign(existingSymbol('fsCode'), [ast.Local('fs')]),
		ast.FunctionDef('bindUniforms', symbols.Symbol('bindUniforms'), []),
		ast.FunctionDef('bindStreams',  symbols.Symbol('bindStreams'), [])
	]),
	[]
)

def generateBindingClass(vscontext, fscontext):
	compiler = vscontext.compiler

	vsCode = vscontext.shaderCode
	fsCode = fscontext.shaderCode

	merged = vscontext.trees.uniformIn.merge(fscontext.trees.uniformIn, None)
	uniformCode = bindUniforms(vscontext.compiler, merged)
	streamCode = bindStreams(vscontext)


	code = symbols.SymbolRewriter(vscontext.compiler.extractor, classTemplate)

	cdef = code.rewrite(vsCode=vsCode, fsCode=fsCode, bindUniforms=uniformCode, bindStreams=streamCode)
	cdef = existingtransform.evaluateAST(compiler, cdef)

	#pprint(cdef)

	buffer = cStringIO.StringIO()
	SimpleCodeGen(buffer).process(cdef)

	s = buffer.getvalue()

	# HACK for imports
	s = "import pystreamruntime\nimport tests.full.physics\n\n" + s

	print
	print s
	print

	filesystem.writeData('summaries', 'compiledshader', 'py', s)

	return cdef
