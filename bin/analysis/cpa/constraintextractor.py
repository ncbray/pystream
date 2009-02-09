from util.typedispatch import *

from programIR.python import ast
from programIR.python import program

from common import opnames

from constraints import *



class ExtractDataflow(object):
	__metaclass__ = typedispatcher

	def __init__(self, system, context):
		self.system  = system
		self.context = context
		self.code = self.context.signature.code

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
			return group.root(sys, name, group.regionHint)
		else:
			return None

	def existingSlot(self, obj):
		sys = self.system
		name = sys.canonical.existingName(self.code, obj, self.context)
		group = self.context.group
		return group.root(sys, name, group.regionHint)

	def contextOp(self, node):
		return self.system.canonical.opContext(self.code, node, self.context)

	def directCall(self, node, code, selfarg, args, vargs, kargs, target):
		if self.doOnce(node):
			assert isinstance(code, ast.Code), type(code)
			op   = self.contextOp(node)
			kwds = [] # HACK
			con = DirectCallConstraint(op, code, selfarg, args, kwds, vargs, kargs, target)
			con.attach(self.system) # TODO move inside constructor?
		return target

	def assign(self, src, dst):
		self.system.createAssign(src, dst)

	def init(self, node, obj):
		result = self.existingSlot(obj)
		if self.doOnce(node):
			sys = self.system
			result.initializeType(sys, sys.canonical.existingType(obj))
		return result

	def call(self, node, expr, args, kwds, vargs, kargs, target):
		if self.doOnce(node):
			op   = self.contextOp(node)
			con = CallConstraint(op, expr, args, kwds, vargs, kargs, target)
			con.attach(self.system) # TODO move inside constructor?
		return target

	def load(self, node, expr, fieldtype, name, target):
		if self.doOnce(node):
			op   = self.contextOp(node)
			con = LoadConstraint(op, expr, fieldtype, name, target)
			con.attach(self.system) # TODO move inside constructor?
		return target

	def store(self, node, expr, fieldtype, name, value):
		op   = self.contextOp(node)
		con = StoreConstraint(op, expr, fieldtype, name, value)
		con.attach(self.system) # TODO move inside constructor?

	def allocate(self, node, expr, target):
		if self.doOnce(node):
			op   = self.contextOp(node)
			con = AllocateConstraint(op, expr, target)
			con.attach(self.system) # TODO move inside constructor?
		return target

	def check(self, node, expr, fieldtype, name, target):
		if self.doOnce(node):
			op   = self.contextOp(node)
			con = CheckConstraint(op, expr, fieldtype, name, target)
			con.attach(self.system) # TODO move inside constructor?
		return target

	##################################
	### Generic feature extraction ###
	##################################

	@defaultdispatch
	def default(self, node, *args):
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
	def visitConvertToBool(self, node, target):
		return self.directCall(node, self.exports['convertToBool'],
			None, [self(node.expr)],
			None, None, target)

	@dispatch(ast.Not)
	def visitNot(self, node, target):
		return self.directCall(node, self.exports['invertedConvertToBool'],
			None, [self(node.expr)],
			None, None, target)

	@dispatch(ast.BinaryOp)
	def visitBinaryOp(self, node, target):
		if node.op in opnames.inplaceOps:
			opname = opnames.inplace[node.op[:-1]]
		else:
			opname = opnames.forward[node.op]

		return self.directCall(node, self.exports['interpreter%s' % opname],
			None, [self(node.left), self(node.right)],
			None, None, target)

	@dispatch(ast.UnaryPrefixOp)
	def visitUnaryPrefixOp(self, node, target):
		opname = opnames.unaryPrefixLUT[node.op]
		return self.directCall(node, self.exports['interpreter%s' % opname],
			None, [self(node.expr)],
			None, None, target)

	@dispatch(ast.GetGlobal)
	def visitGetGlobal(self, node, target):
		return self.directCall(node, self.exports['interpreterLoadGlobal'],
			None, [self(self.code.selfparam), self(node.name)],
			None, None, target)

	@dispatch(ast.SetGlobal)
	def visitSetGlobal(self, node):
		return self.directCall(node, self.exports['interpreterStoreGlobal'],
			None, [self(self.code.selfparam), self(node.name), self(node.value)],
			None, None, None)

	@dispatch(ast.GetIter)
	def visitGetIter(self, node, target):
		return self.directCall(node, self.exports['interpreter_iter'],
			None, [self(node.expr)],
			None, None, target)

	@dispatch(ast.Call)
	def visitCall(self, node, target):
		return self.call(node, self(node.expr),
			self(node.args), self(node.kwds),
			self(node.vargs), self(node.kargs), target)

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node, target):
		return self.directCall(node, node.func,
			self(node.selfarg), self(node.args),
			self(node.vargs), self(node.kargs), target)

	@dispatch(ast.BuildList)
	def visitBuildList(self, node, target):
		return self.directCall(node, self.exports['buildList'],
			None, self(node.args),
			None, None, target)

	@dispatch(ast.BuildTuple)
	def visitBuildTuple(self, node, target):
		return self.directCall(node, self.exports['buildTuple'],
			None, self(node.args),
			None, None, target)

	@dispatch(ast.UnpackSequence)
	def visitUnpackSequence(self, node):
		# HACK oh so ugly... does not resemble what actually happens.
		for i, arg in enumerate(node.targets):
			obj = self.system.extractor.getObject(i)
			target = self.localSlot(arg)
			self.directCall(node, self.exports['interpreter_getitem'],
				None, [self(node.expr), self(ast.Existing(obj))],
				None, None, target)

	@dispatch(ast.GetAttr)
	def visitGetAttr(self, node, target):
		return self.directCall(node, self.exports['interpreter_getattribute'],
			None, [self(node.expr), self(node.name)],
			None, None, target)

	@dispatch(ast.SetAttr)
	def visitSetAttr(self, node):
		return self.directCall(node, self.exports['interpreter_setattr'],
			None, [self(node.expr), self(node.name), self(node.value)],
			None, None, None)

	@dispatch(ast.GetSubscript)
	def visitGetSubscript(self, node, target):
		return self.directCall(node, self.exports['interpreter_getitem'],
			None, [self(node.expr), self(node.subscript)],
			None, None, target)

	@dispatch(ast.SetSubscript)
	def visitSetSubscript(self, node):
		return self.directCall(node, self.exports['interpreter_setitem'],
			None, [self(node.expr), self(node.subscript), self(node.value)],
			None, None, None)


	@dispatch(ast.Assign)
	def visitAssign(self, node):
		self(node.expr, self(node.lcl))

	@dispatch(ast.Discard)
	def visitDiscard(self, node):
		self(node.expr, None)

	@dispatch(ast.Return)
	def visitReturn(self, node):
		self.assign(self(node.expr), self(self.code.returnparam))

	@dispatch(ast.Local)
	def visitLocal(self, node, target=None):
		value = self.localSlot(node)

		if target is not None:
			self.assign(value, target)
		else:
			return value

	@dispatch(ast.Existing)
	def visitExisting(self, node, target=None):
		value = self.init(node.object, node.object)

		if target is not None:
			target.initializeType(self.system, self.system.canonical.existingType(node.object))
			#self.assign(value, target)
		else:
			return value

	@dispatch(ast.Load)
	def visitLoad(self, node, target):
		return self.load(node, self(node.expr), node.fieldtype, self(node.name), target)

	@dispatch(ast.Store)
	def visitStore(self, node):
		return self.store(node, self(node.expr), node.fieldtype, self(node.name), self(node.value))

	@dispatch(ast.Allocate)
	def visitAllocate(self, node, target):
		return self.allocate(node, self(node.expr), target)

	@dispatch(ast.Check)
	def visitCheck(self, node, target):
		return self.check(node, self(node.expr), node.fieldtype, self(node.name), target)

	@dispatch(ast.Switch)
	def visitSwitch(self, node):
		self(node.condition)

		cond = self.localSlot(node.condition.conditional)
		con = DeferedSwitchConstraint(self, cond, node.t, node.f)
		con.attach(self.system) # TODO move inside constructor?

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

	def process(self):
		self(self.code)