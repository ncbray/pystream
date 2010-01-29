from util.typedispatch import *
from language.python import ast
from .. import intrinsics

class ObjectAnalysis(TypeDispatcher):
	def __init__(self, compiler, code):
		self.compiler = compiler
		self.code = code

		self.allocated = set()
		self.nonfinal  = set()
		self.unique    = set()

		self.loopLevel = 0

	def handleAnnotation(self, annotation):
		allocated = annotation.allocates.merged

		for obj in allocated:
			assert obj not in self.allocated, "Temporary limitation: all allocated objects must have unique names"
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

	@dispatch(ast.Suite)
	def visitSuite(self, node):
		node.visitChildren(self)

	def postProcess(self):
		for obj in self.allocated:
			unique = obj in self.unique
			final  = obj not in self.nonfinal
			obj.rewriteAnnotation(unique=unique, final=final)

			if unique:
				assert obj.xtype.obj.pythonType() is not list, "Temporary Limitation: Cannot handle unique lists"
				for field in obj:
					field.rewriteAnnotation(unique=True)

	def process(self):
		self.code.visitChildrenForced(self)
		self.postProcess()

def process(compiler, code):
	oa = ObjectAnalysis(compiler, code)
	oa.process()
