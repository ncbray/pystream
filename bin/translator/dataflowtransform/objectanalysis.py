from util.typedispatch import *
from language.python import ast
from .. import intrinsics

immutableTypes = frozenset([float, int, long, bool, str, tuple, frozenset])

class ObjectAnalysis(TypeDispatcher):
	def __init__(self, compiler, prgm):
		self.compiler = compiler
		self.prgm = prgm

		self.allocated = set()
		self.nonfinal  = set()
		self.unique    = set()

		self.loopLevel = 0

	def handleAnnotation(self, annotation):
		allocated = annotation.allocates.merged

		for obj in allocated:
			if obj.xtype.obj.pythonType() not in (float, int, bool, long, str):
				assert obj not in self.allocated, "Temporary limitation: all allocated objects must have unique names (%r)" % obj
			self.allocated.add(obj)
			if self.loopLevel == 0:
				self.unique.add(obj)

		# If an object is modified but not allocated, it is nonfinal
		modified  = annotation.modifies.merged
		for field in modified:
			if field.object not in allocated:
				self.nonfinal.add(field.object)


	@dispatch(ast.leafTypes, ast.CodeParameters, ast.Return, ast.Local, ast.Existing)
	def visitLeaf(self, node):
		pass

	@dispatch(ast.Load, ast.Store, ast.Allocate, ast.Call, ast.DirectCall)
	def visitOp(self, node):
		self.handleAnnotation(node.annotation)

	@dispatch(ast.Assign, ast.Discard)
	def visitAssign(self, node):
		self(node.expr)

	@dispatch(ast.TypeSwitch)
	def visitTypeSwitch(self, node):
		for case in node.cases:
			self(case.body)

	@dispatch(ast.Switch)
	def visitSwitch(self, node):
		self(node.condition)
		self(node.t)
		self(node.f)

	@dispatch(ast.While)
	def visitWhile(self, node):
		self.loopLevel += 1
		self(node.condition)
		self(node.body)
		self.loopLevel -= 1
		self(node.else_)

	@dispatch(ast.OutputBlock)
	def visitOutputBlock(self, node):
		pass

	@dispatch(ast.Suite, ast.Condition)
	def visitOK(self, node):
		node.visitChildren(self)

	def fixupStoreGraph(self):
		region = self.prgm.storeGraph.regionHint
		for xtype, obj in region.objects.iteritems():
			assert xtype.obj.pythonType() is not list, "Temporary Limitation: Cannot handle lists"

			if xtype.obj.pythonType() in immutableTypes:
				obj.rewriteAnnotation(final=True)

			if xtype.isUnique():
				obj.rewriteAnnotation(unique=True)

			if obj.annotation.unique:
				for field in obj:
					field.rewriteAnnotation(unique=True)

			if xtype.isExisting() or xtype.isExternal():
				# HACK may be input?
				obj.rewriteAnnotation(uniform=True)

	def postProcess(self):
		for obj in self.allocated:
			unique = obj in self.unique
			final  = obj not in self.nonfinal
			obj.rewriteAnnotation(unique=unique, final=final)

			if unique:
				assert obj.xtype.obj.pythonType() is not list, "Temporary Limitation: Cannot handle unique lists"
				for field in obj:
					field.rewriteAnnotation(unique=True)

		self.fixupStoreGraph()

	def process(self, code):
		code.visitChildrenForced(self)

def process(compiler, prgm, *codeASTs):
	oa = ObjectAnalysis(compiler, prgm)
	for code in codeASTs:
		oa.process(code)

	oa.postProcess()
