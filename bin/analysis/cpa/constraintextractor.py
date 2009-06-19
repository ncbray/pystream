from util.typedispatch import *

from language.python import ast
from language.python import program
from language.python import annotations

from common import opnames

from constraints import *



class ExtractDataflow(TypeDispatcher):
	def __init__(self, system, context, folded):
		self.system  = system
		self.context = context
		self.folded  = folded
		self.code    = self.context.signature.code

		self.processed = set()

	@property
	def exports(self):
		return self.system.extractor.stubs.exports

	def doOnce(self, node):
		return True

		if not node in self.processed:
			self.processed.add(node)
			return True
		else:
			return False

	def localSlot(self, lcl):
		if lcl is not None:
			sys = self.system
			name = sys.canonical.localName(self.code, lcl, self.context)
			group = self.context.group
			return group.root(name)
		else:
			return None

	def existingSlot(self, obj):
		sys = self.system
		name = sys.canonical.existingName(self.code, obj, self.context)
		group = self.context.group
		return group.root(name)

	def contextOp(self, node):
		return self.system.canonical.opContext(self.code, node, self.context)

	def directCall(self, node, code, selfarg, args, vargs, kargs, targets):
		if self.doOnce(node):
			assert code.isCode(), (("Incorrect code parameter %r\n" % code)+annotations.originTraceString(node.annotation.origin))
			op   = self.contextOp(node)
			kwds = [] # HACK
			DirectCallConstraint(self.system, op, code, selfarg, args, kwds, vargs, kargs, targets)
		return targets

	def assign(self, src, dst):
		self.system.createAssign(src, dst)

	def init(self, node, obj):
		result = self.existingSlot(obj)
		if self.doOnce(node):
			sys = self.system
			result.initializeType(sys.canonical.existingType(obj))
		return result

	def call(self, node, expr, args, kwds, vargs, kargs, targets):
		# HACK for all the examples we have, indirect calls should be resolved after the first pass!
		# In the future this may not be the case.
		assert self.system.firstPass, self.code

		if self.doOnce(node):
			op   = self.contextOp(node)
			CallConstraint(self.system, op, expr, args, kwds, vargs, kargs, targets)
		return targets

	def load(self, node, expr, fieldtype, name, targets):
		if self.doOnce(node):
			assert len(targets) == 1
			op   = self.contextOp(node)
			LoadConstraint(self.system, op, expr, fieldtype, name, targets[0])
		return targets

	def store(self, node, expr, fieldtype, name, value):
		op   = self.contextOp(node)
		StoreConstraint(self.system, op, expr, fieldtype, name, value)

	def allocate(self, node, expr, targets):
		if self.doOnce(node):
			assert len(targets) == 1
			op   = self.contextOp(node)
			AllocateConstraint(self.system, op, expr, targets[0])
		return targets

	def check(self, node, expr, fieldtype, name, targets):
		if self.doOnce(node):
			assert len(targets) == 1
			op   = self.contextOp(node)
			CheckConstraint(self.system, op, expr, fieldtype, name, targets[0])
		return targets

	##################################
	### Generic feature extraction ###
	##################################

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


	@dispatch(ast.Call)
	def visitCall(self, node, targets):
		return self.call(node, self(node.expr),
			self(node.args), self(node.kwds),
			self(node.vargs), self(node.kargs), targets)

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node, targets):
		return self.directCall(node, node.code,
			self(node.selfarg), self(node.args),
			self(node.vargs), self(node.kargs), targets)


	@dispatch(ast.Assign)
	def visitAssign(self, node):
		self(node.expr, self(node.lcls))

	@dispatch(ast.Discard)
	def visitDiscard(self, node):
		self(node.expr, None)

	@dispatch(ast.Return)
	def visitReturn(self, node):
		if not self.folded:
			callee = self.code.codeParameters()

			assert len(node.exprs) == len(callee.returnparams)
			for expr, param in zip(node.exprs, callee.returnparams):
				self.assign(self(expr), self(param))

	@dispatch(ast.Local)
	def visitLocal(self, node, targets=None):
		value = self.localSlot(node)

		if targets is not None:
			assert len(targets) == 1
			self.assign(value, targets[0])
		else:
			return value

	@dispatch(ast.Existing)
	def visitExisting(self, node, targets=None):
		value = self.init(node.object, node.object)

		if targets is not None:
			assert len(targets) == 1
			targets[0].initializeType(self.system.canonical.existingType(node.object))
		else:
			return value

	@dispatch(ast.Load)
	def visitLoad(self, node, targets):
		return self.load(node, self(node.expr), node.fieldtype, self(node.name), targets)

	@dispatch(ast.Store)
	def visitStore(self, node):
		return self.store(node, self(node.expr), node.fieldtype, self(node.name), self(node.value))

	@dispatch(ast.Allocate)
	def visitAllocate(self, node, targets):
		return self.allocate(node, self(node.expr), targets)

	@dispatch(ast.Check)
	def visitCheck(self, node, targets):
		return self.check(node, self(node.expr), node.fieldtype, self(node.name), targets)

	@dispatch(ast.Switch)
	def visitSwitch(self, node):
		self(node.condition)

		cond = self.localSlot(node.condition.conditional)
		DeferedSwitchConstraint(self.system, self, cond, node.t, node.f)

	@dispatch(ast.TypeSwitch)
	def visitTypeSwitch(self, node):
		op   = self.contextOp(None) # HACK logs the read onto the code.
		cond = self.localSlot(node.conditional)
		DeferedTypeSwitchConstraint(self.system, op, self, cond, node.cases)

	@dispatch(ast.Break)
	def visitBreak(self, node):
		pass # Flow insensitive

	@dispatch(ast.Continue)
	def visitContinue(self, node):
		pass # Flow insensitive


	@dispatch(ast.While)
	def visitWhile(self, node):
		self(node.condition)
		self(node.body)

		if node.else_:
			self(node.else_)

	@dispatch(ast.For)
	def visitFor(self, node):
		self(node.loopPreamble)

		self(node.bodyPreamble)
		self(node.body)

		if node.else_:
			self(node.else_)

	@dispatch(ast.Code)
	def visitCode(self, node):
		self(node.ast)

	### Entry point ###
	def process(self):
		if self.code.isStandardCode():
			self(self.code)
		else:
			self.code.extractConstraints(self)