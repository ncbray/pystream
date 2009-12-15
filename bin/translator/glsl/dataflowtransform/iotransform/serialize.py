import sys

from language.python import ast
from language.python.simplecodegen import SimpleCodeGen

from asttools.astpprint import pprint

from ... import intrinsics

import cStringIO

from util.io import filesystem

from . import existingtransform

def bindUniform(compiler, self, name, t, value):
	methodName = compiler.extractor.getObject("bind_uniform_" + t.__name__)
	
	shaderNameExpr = ast.Existing(compiler.extractor.getObject(name))
	
	op = ast.Call(ast.GetAttr(self, ast.Existing(methodName)), [shaderNameExpr, value], [], None, None)
	return ast.Discard(op)
	

# TODO mask?
def serializeUniformNode(compiler, self, tree, root):
	types = sorted(set([k.xtype.obj.pythonType() for k in tree.objMasks.iterkeys()]))
	assert len(types) > 0
	
	if len(types) == 1:
		return handleUniformType(compiler, self, tree, root, types[0])	
	else:
		switches = []
		for t in types:
			clsExpr = ast.Existing(compiler.extractor.getObject(t))
			isinstanceExpr = ast.GetGlobal(ast.Existing(compiler.extractor.getObject('isinstance')))
			cond  = ast.Call(isinstanceExpr, [root, clsExpr], [], None, None)
			suite = ast.Suite(handleUniformType(compiler, self, tree, root, t))
			
			# Bind an integer that indicated the type of the object?
			value = ast.Existing(compiler.extractor.getObject(len(types)))
			suite = ast.Suite([bindUniform(compiler, self, 'bogus', int, value) ,suite])
			
			switches.append((cond, suite))
		
		current = ast.Suite([ast.Assert(ast.Existing(compiler.extractor.getObject(False)), None)])
		
		for cond, suite in reversed(switches):
			current = ast.Switch(ast.Condition(ast.Suite([]), cond), suite, ast.Suite([current]))
		
		return [current]
	
def handleUniformType(compiler, self, tree, root, t):
	statements = []	
	
	if intrinsics.isIntrinsicType(t):	
		statements.append(bindUniform(compiler, self, tree.name, t, root))
	
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
			
			# Load the field
			clsExpr  = ast.Existing(compiler.extractor.getObject(cls))
			attrExpr = ast.Existing(compiler.extractor.getObject(attr))
			getExpr = ast.Existing(compiler.extractor.getObject('__get__'))
			
			op = ast.Call(ast.GetAttr(ast.GetAttr(clsExpr, attrExpr), getExpr), [root], [], None, None)
			childroot = ast.Local('bogus')
			assign = ast.Assign(op, [childroot]) 

			statements.append(assign)

			# Recurse
			statements.extend(serializeUniformNode(compiler, self, child, childroot))
		
	return statements

def bindUniforms(compiler, uniforms):
	self   = ast.Local('self')		
	shader = ast.Local('shader')
	
	body = ast.Suite(serializeUniformNode(compiler, self, uniforms, shader))
	
	params = ast.CodeParameters(None, [self, shader], ['self', 'shader'], [], None, None, [])
	code = ast.Code('bindUniforms', params, body)

	return code



def bindStreams(context):
	self   = ast.Local('self')		
	streams   = [ast.Local(param.name) for param in context.code.codeparameters.params[2:]] 

	statements = []
	
	for tree, root in zip(context.trees.inputs, streams):
		assert len(tree.objMasks) == 1
		obj = tree.objMasks.keys()[0]
		assert intrinsics.isIntrinsicObject(obj)
		t = obj.xtype.obj.pythonType()
		
		name = context.compiler.extractor.getObject("bind_stream_" + t.__name__)
		
		shaderName = tree.name
		
		if shaderName is not None:
			shaderNameExpr = ast.Existing(context.compiler.extractor.getObject(shaderName))
			
			op = ast.Call(ast.GetAttr(self, ast.Existing(name)), [shaderNameExpr, root], [], None, None)
			statements.append(ast.Discard(op))		

	
	body = ast.Suite(statements)
	
	args = [self]
	args.extend(streams)
	names = [arg.name for arg in args]
	params = ast.CodeParameters(None, args, names, [], None, None, [])
	code = ast.Code('bindStreams', params, body)
	
	return code

def generateBindingClass(vscontext, fscontext):
	compiler = vscontext.compiler
	
	vs = ast.Assign(ast.Existing(compiler.extractor.getObject(vscontext.shaderCode)), [ast.Local('vs')])
	fs = ast.Assign(ast.Existing(compiler.extractor.getObject(fscontext.shaderCode)), [ast.Local('fs')])
	
	merged = vscontext.trees.uniformIn.merge(fscontext.trees.uniformIn, None)
		
	code = bindUniforms(vscontext.compiler, merged)
	uniformfdef = ast.FunctionDef('bindUniforms', code, [])

	code = bindStreams(vscontext)
	streamfdef = ast.FunctionDef('bindStreams', code, [])
	
	statements = [vs, fs, uniformfdef, streamfdef]

	moduleExpr = ast.Existing(compiler.extractor.getObject('pystreamruntime'))	
	baseExpr = ast.Existing(compiler.extractor.getObject('BaseCompiledShader'))
	base = ast.GetAttr(ast.GetGlobal(moduleExpr), baseExpr)
	cdef = ast.ClassDef('CompiledShader', [base], ast.Suite(statements), [])

	cdef = existingtransform.evaluateAST(compiler, cdef)

	#pprint(cdef)
	
	buffer = cStringIO.StringIO()
	SimpleCodeGen(buffer).walk(cdef)
	
	s = buffer.getvalue()
	
	# HACK for imports
	s = "import pystreamruntime\nimport tests.full.physics\n\n" + s
	
	print
	print s
	print
	
	filesystem.writeData('summaries', 'compiledshader', 'py', s)
	
	return cdef
