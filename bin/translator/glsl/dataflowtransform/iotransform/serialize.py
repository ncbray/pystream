import sys

from language.python import ast
from language.python.simplecodegen import SimpleCodeGen

from asttools.astpprint import pprint

from ... import intrinsics

import cStringIO

import util.filesystem

def serializeUniformNode(context, self, tree, root):
	statements = []

	assert len(tree.objMasks) == 1
	
	obj = tree.objMasks.keys()[0]
	if intrinsics.isIntrinsicObject(obj):
		t = obj.xtype.obj.pythonType()
		
		name = context.compiler.extractor.getObject("bind_uniform_" + t.__name__)
		
		shaderName = tree.name
		shaderNameExpr = ast.Existing(context.compiler.extractor.getObject(shaderName))
		
		op = ast.Call(ast.GetAttr(self, ast.Existing(name)), [shaderNameExpr, root], [], None, None)
		statements.append(ast.Discard(op))
	
	for field, child in tree.fields.iteritems():
		if not intrinsics.isIntrinsicField(field):

			assert field.type == 'Attribute'
			
			name = field.name.pyobj
			descriptor = context.compiler.slots.reverse[name]
			cls  = descriptor.__objclass__
			attr = descriptor.__name__ 

			# HACK may have been renamed...
			assert cls.__dict__[attr] is descriptor, "Can't find original descriptor!"
			
			# Load the field
			clsExpr  = ast.Existing(context.compiler.extractor.getObject(cls))
			attrExpr = ast.Existing(context.compiler.extractor.getObject(attr))
			getExpr = ast.Existing(context.compiler.extractor.getObject('__get__'))
			
			op = ast.Call(ast.GetAttr(ast.GetAttr(clsExpr, attrExpr), getExpr), [root], [], None, None)
			childroot = ast.Local('bogus')
			assign = ast.Assign(op, [childroot]) 

			statements.append(assign)

			# Recurse
			statements.extend(serializeUniformNode(context, self, child, childroot))
		
	return statements

def bindUniforms(context):
	uniforms = context.trees.uniformIn

	self   = ast.Local('self')		
	shader = ast.Local('shader')
	
	body = ast.Suite(serializeUniformNode(context, self, uniforms, shader))
	
	params = ast.CodeParameters(None, [self, shader], ['self', 'shader'], None, None, [])
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
		shaderNameExpr = ast.Existing(context.compiler.extractor.getObject(shaderName))
		
		op = ast.Call(ast.GetAttr(self, ast.Existing(name)), [shaderNameExpr, root], [], None, None)
		statements.append(ast.Discard(op))		

	
	body = ast.Suite(statements)
	
	args = [self]
	args.extend(streams)
	names = [arg.name for arg in args]
	params = ast.CodeParameters(None, args, names, None, None, [])
	code = ast.Code('bindStreams', params, body)
	
	return code

def generateBindingClass(vscontext, fscontext):
	
	vs = ast.Assign(ast.Existing(vscontext.compiler.extractor.getObject(vscontext.shaderCode)), [ast.Local('vs')])
	fs = ast.Assign(ast.Existing(fscontext.compiler.extractor.getObject(fscontext.shaderCode)), [ast.Local('fs')])
	
	code = bindUniforms(vscontext)
	uniformfdef = ast.FunctionDef('bindUniforms', code, [])

	code = bindStreams(vscontext)
	streamfdef = ast.FunctionDef('bindStreams', code, [])

	
	statements = [fs, vs, uniformfdef, streamfdef]
	
	objectExpr = ast.Existing(vscontext.compiler.extractor.getObject('BaseCompiledShader'))
	cdef = ast.ClassDef('CompiledShader', [ast.GetGlobal(objectExpr)], ast.Suite(statements), [])

	#pprint(cdef)
	
	buffer = cStringIO.StringIO()
	SimpleCodeGen(buffer).walk(cdef)
	
	s = buffer.getvalue()
	
	print
	print s
	print
	
	util.filesystem.writeData('summaries', 'compiledshader', 'py', s)
	
	return cdef
