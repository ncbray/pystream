from util.typedispatch import *

from programIR.python import ast
from programIR.python import program

from common import opnames
from stubs.stubcollector import exports


from constraints import *



class ExtractDataflow(object):
	__metaclass__ = typedispatcher

	def __init__(self, system, context, func):
		self.system = system
		self.context = context
		self.function = func
		
		self.processed = set()

	def doOnce(self, node):
		return True
		
		if not node in self.processed:
			self.processed.add(node)
			return True
		else:
			return False

	def contextual(self, lcl):
		if lcl is not None:
			return self.system.local(self.context, self.function, lcl)
		else:
			return None


	def contextOp(self, node):
		return self.system.contextOp(self.context, self.function, node)

	def directCall(self, node, func, selfarg, args, vargs=None, kargs=None):
		result = self.contextual(node)
		
		if self.doOnce(node):
			op   = self.contextOp(node)
			path = self.context.path.advance(node)
			kwds = [] # HACK
			con = DirectCallConstraint(op, path, func, selfarg, args, kwds, vargs, kargs, result)
			con.attach(self.system) # TODO move inside constructor?

		return result

	def assign(self, src, dst):
		con = AssignmentConstraint(src, dst)
		con.attach(self.system) # TODO move inside constructor?


	def init(self, node, obj):
		result = self.contextual(node)
		if self.doOnce(node):
			self.system.update(result, (self.system.existingObject(obj),))			
		return result

	def call(self, node, expr, args, kwds, vargs, kargs):
		result = self.contextual(node)
		if self.doOnce(node):
			op   = self.contextOp(node)
			path = self.context.path.advance(node)
			con = CallConstraint(op, path, expr, args, kwds, vargs, kargs, result)
			con.attach(self.system) # TODO move inside constructor?
		return result

	def load(self, node, expr, fieldtype, name):
		result = self.contextual(node)
		if self.doOnce(node):
			op   = self.contextOp(node)
			con = LoadConstraint(op, expr, fieldtype, name, result)			
			con.attach(self.system) # TODO move inside constructor?
		return result

	def store(self, node, expr, fieldtype, name, value):
		op   = self.contextOp(node)		
		con = StoreConstraint(op, expr, fieldtype, name, value)
		con.attach(self.system) # TODO move inside constructor?

	def allocate(self, node, expr):
		result = self.contextual(node)
		if self.doOnce(node):
			op   = self.contextOp(node)			
			path = self.context.path.advance(node)
			con = AllocateConstraint(op, path, expr, result)
			con.attach(self.system) # TODO move inside constructor?
		return result


	##################################
	### Generic feature extraction ###
	##################################

	@defaultdispatch
	def default(self, node):
		assert False, repr(node)

	@dispatch(str, type(None))
	def visitJunk(self, node):
		pass

	@dispatch(ast.Suite, ast.Condition)
	def visitOK(self, node):
		for child in ast.children(node):
			self(child)


	@dispatch(list)
	def visitList(self, node):
		return [self(child) for child in node]

	@dispatch(tuple)
	def visitTuple(self, node):
		return tuple([self(child) for child in node])

	@dispatch(ast.ConvertToBool)
	def visitConvertToBool(self, node):
		return self.directCall(node, exports['convertToBool'], None, [self(node.expr)])


	@dispatch(ast.BinaryOp)
	def visitBinaryOp(self, node):
		if node.op in opnames.inplaceOps:
			opname = opnames.inplace[node.op[:-1]]
		else:
			opname = opnames.forward[node.op]				

		return self.directCall(node, exports['interpreter%s' % opname], None, [self(node.left), self(node.right)])

	@dispatch(ast.UnaryPrefixOp)
	def visitUnaryPrefixOp(self, node):
		opname = opnames.unaryPrefixLUT[node.op]
		return self.directCall(node, exports['interpreter%s' % opname], None, [self(node.expr)])

	@dispatch(ast.GetGlobal)
	def visitGetGlobal(self, node):
		return self.directCall(node, exports['interpreterLoadGlobal'], None, [self(self.function.code.selfparam), self(node.name)])

	@dispatch(ast.GetIter)
	def visitGetIter(self, node):
		return self.directCall(node, exports['interpreter_iter'], None, [self(node.expr)])

	@dispatch(ast.Call)
	def visitCall(self, node):
		return self.call(node, self(node.expr), self(node.args), self(node.kwds), self(node.vargs), self(node.kargs))

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node):
		return self.directCall(node, node.func, self(node.selfarg), self(node.args), self(node.vargs), self(node.kargs)) 

	@dispatch(ast.BuildList)
	def visitBuildList(self, node):
		return self.directCall(node, exports['buildList'], None, self(node.args))

	@dispatch(ast.BuildTuple)
	def visitBuildTuple(self, node):
		return self.directCall(node, exports['buildTuple'], None, self(node.args))

	@dispatch(ast.UnpackSequence)
	def visitUnpackSequence(self, node):
		# HACK oh so ugly... does not resemble what actually happens.
		for i, arg in enumerate(node.targets):
			obj = self.system.extractor.getObject(i)
			self.directCall(arg, exports['interpreter_getitem'], None, [self(node.expr), self(ast.Existing(obj))])

	@dispatch(ast.GetAttr)
	def visitGetAttr(self, node):
		return self.directCall(node, exports['interpreter_getattribute'], None, [self(node.expr), self(node.name)])

	@dispatch(ast.SetAttr)
	def visitSetAttr(self, node):
		return self.directCall(node, exports['interpreter_setattr'], None, [self(node.expr), self(node.name), self(node.value)])

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		self.assign(self(node.expr), self(node.lcl))

	@dispatch(ast.Discard)
	def visitDiscard(self, node):
		self(node.expr)

	@dispatch(ast.Return)
	def visitReturn(self, node):
		self.assign(self(node.expr), self(self.function.code.returnparam))

	@dispatch(ast.Local)
	def visitLocal(self, node):
		return self.contextual(node)

	@dispatch(ast.Existing)
	def visitExisting(self, node):
		# TODO refine?
		return self.init(node.object, node.object)

	@dispatch(ast.Load)
	def visitLoad(self, node):
		return self.load(node, self(node.expr), node.fieldtype, self(node.name))

	@dispatch(ast.Store)
	def visitStore(self, node):
		return self.store(node, self(node.expr), node.fieldtype, self(node.name), self(node.value))

	@dispatch(ast.Allocate)
	def visitAllocate(self, node):
		return self.allocate(node, self(node.expr))

	@dispatch(ast.Switch)
	def visitSwitch(self, node):
		self(node.condition)

		cond = self.contextual(node.condition.conditional)
		con = DeferedSwitchConstraint(self, cond, node.t, node.f)
		con.attach(self.system) # TODO move inside constructor?



##	def visitWhile(self, node):
##		self.visit(node.condition)
##		self.visit(node.body)
##		if node.else_: self.visit(node.else_)
##
	@dispatch(ast.For)
	def visitFor(self, node):

		#iterator = self(node.iterator)
		#self.directCall(node.index, exports['interpreter_next'], None, [iterator])

		self(node.loopPreamble)

		self(node.bodyPreamble)
		
		self(node.body)
		
		if node.else_:
			self(node.else_)


	@dispatch(ast.Code)
	def visitCode(self, node):
		self(node.ast)

	@dispatch(ast.Function)
	def visitFunction(self, node):
		self(node.code)


