import sys

from language.python import ast
from language.python.simplecodegen import SimpleCodeGen

from asttools.astpprint import pprint

from ... import intrinsics

def serializeUniformNode(context, self, tree, root):
	statements = []

	assert len(tree.objMasks) == 1
	
	obj = tree.objMasks.keys()[0]
	if intrinsics.isIntrinsicObject(obj):
		t = obj.xtype.obj.pythonType()
		
		name = context.compiler.extractor.getObject("bind_" + t.__name__)
		
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

def serializeUniforms(context):
	uniforms = context.trees.uniformIn

	self   = ast.Local('self')		
	shader = ast.Local('shader')
	
	body = ast.Suite(serializeUniformNode(context, self, uniforms, shader))
	
	params = ast.CodeParameters(None, [self, shader], ['self', 'shader'], None, None, [])
	code = ast.Code('bindUniforms', params, body)
	
	#pprint(code)
	
	print
	SimpleCodeGen(sys.stdout).walk(code)
	print
	
	return code