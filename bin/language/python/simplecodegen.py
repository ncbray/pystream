import types
import sys

from util.visitor import StandardVisitor
from util.pythonoutput import PythonOutput

from common import opnames, defuse

from language.python import ast, program

import re
isIdentifier = re.compile(r'^([a-zA-Z_]\w*)?$')

def typeString(t):
	if(t):
		return "<%s>" % ', '.join(set([str(label.baseType()) for label in t.labels]))
	else:
		return "<?>"

class UncollapsableCodeError(Exception):
	pass

def getConstant(node, t=None):
	assert isinstance(node, ast.Existing) and node.object.isConstant(), node
	if t != None: assert isinstance(node.object.pyobj, t)
	return node.object.pyobj


def getExistingStr(node):
	assert isinstance(node, ast.Existing)
	if node.object.isConstant():
		return repr(node.object.pyobj)
	else:
		return "[|%r|]" % node.object

class SimpleExprGen(StandardVisitor):
	def __init__(self, parent):
		StandardVisitor.__init__(self)

		# For renaming locals
		self.localLUT = {}
		self.names = set()
		self.uid = 0

		self.collapsed = {}

		self.parent = parent

	def generateUniqueLocalName(self, base):
		# The bytecode compiler can generate invalid names for list comprehensions/tuple comprehensions/etc.
		if not isIdentifier.match(base):
			base = ''

		name = base

		# Find a unique name.
		while not name or name in self.names:
			name = '%s_%d' % (base, self.uid)
			self.uid += 1
		return name

	def getLocalName(self, node):
		# HACK assumes locals will not conflict with non-local names
		# TODO preregister globals and cells
		# TODO preregister "MakeFunction" names.

		if not node in self.localLUT:
			base = node.name if node.name else ''
			name = self.generateUniqueLocalName(base)
			self.setLocalName(node, name)
		return self.localLUT[node]

	def setLocalName(self, node, name):
		assert not node in self.localLUT, "%r has already been named: %s." % (node, self.localLUT[node])

		if name is None:
			name = self.generateUniqueLocalName('')
			name = '!'+name
			self.names.add(name)
			self.localLUT[node] = name
		elif isIdentifier.match(name):
			self.names.add(name)
			self.localLUT[node] = name

	def visitLocal(self, node):
		return self.getLocalName(node), -1

	def visitExisting(self, node):
		s = getExistingStr(node)
		return s, -1

	def visitGetGlobal(self, node):
		name = getConstant(node.name, str)
		return name, -1

	def visitCell(self, node):
		return node.name, -1

	def visitGetCell(self, node):
		# HACK
		print "Warning: AST contains GetCell node."
		return "None", -1

	def visitGetCellDeref(self, node):
		return self.visit(node.cell)


	def visitImport(self, node):
		return ("__import__(%r, globals(), locals(), %r, %d)" % (node.name, node.fromlist, node.level)), 4


	def visitGetIter(self, node):
		return ("iter(%s)" % (self.process(node.expr, 24))), 4

	def visitConvertToBool(self, node):
		return ("bool(%s)" % (self.process(node.expr, 24))), 4


	def visitAllocate(self, node):
		# Synax for allocating containers.
		if isinstance(node.expr, ast.Existing):
			obj = node.expr.object
			if isinstance(obj, program.Object):
				pyobj = obj.pyobj
				if pyobj is list:
					return "[]", 2
				elif pyobj is dict:
					return "{}", 2

		return ("<allocate>(%s)" % (self.process(node.expr, 24))), 4

	def visitLoad(self, node):
		return ("<load>(%s, %r, %s)" % (self.process(node.expr, 24), node.fieldtype, self.process(node.name, 24))), 4

#	def visitStore(self, node):
#		return ("<store>(%s, %r, %s, %s)" % (self.process(node.expr, 24), node.fieldtype, self.process(node.name, 24), self.process(node.value, 24))), 4


	def visitCheck(self, node):
		return ("<check>(%s, %r, %s)" % (self.process(node.expr, 24), node.fieldtype, self.process(node.name, 24))), 4


	def visitGetAttr(self, node):
		# HACK
		#prec = 7
		prec = 4
		name = getConstant(node.name, str)
		return ("%s.%s" % (self.process(node.expr, prec), name)), prec

	def visitGetSubscript(self, node):
		# HACK
		#prec = 6
		prec = 4

		return ("%s[%s]" % (self.process(node.expr, prec), self.process(node.subscript, 2))), prec


	def visitUnaryPrefixOp(self, node):
		prec = opnames.unaryPrefixPrecedence[node.op]
		return (node.op + self.process(node.expr, prec)), prec

	def visitNot(self, node):
		prec = 20
		return ("not " + self.process(node.expr, prec)), prec

	def visitBinaryOp(self, node):
		assert not node.op in opnames.inplaceOps

		prec = opnames.binaryOpPrecedence[node.op]
		flipBinding = node.op == '**'

		# TODO flip l/r binding for **
		left = self.process(node.left, prec, flipBinding)
		right = self.process(node.right, prec, not flipBinding)

		op = node.op
		if op in opnames.mustHaveSpace:
			op = " %s " % op

		return (left + op + right), prec

	def visitYield(self, node):
		expr = self.process(node.expr, 24)
		return "yield %s" % expr, 24 # No parenth, so low precedence.	Otherwise, 3?


	def visitBuildTuple(self, node):
		args = [self.process(arg, 24) for arg in node.args]
		return ("%s," % ", ".join(args)), 24 # No parenth, so low precedence.	Otherwise, 3?

	def visitBuildList(self, node):
		args = [self.process(arg, 24) for arg in node.args]
		return ("[%s]" % ", ".join(args)), 2

	def visitBuildMap(self, node):
		return ("{}"), 2

	def processNone(self, node, prec, replace):
		if not node:
			return replace
		else:
			return self.process(node, prec)

	def visitBuildSlice(self, node):
		args = [self.processNone(arg, 24, 'None') for arg in (node.start, node.stop, node.step)]
		return ("slice(%s)" % ', '.join(args)), 4

	def visitGetSlice(self, node):
		prec = 4
		expr = self.process(node.expr, prec)

		if node.step:
			args = (node.start, node.stop, node.step)
		else:
			args = (node.start, node.stop)

		args = [self.processNone(arg, 24, '') for arg in args]
		return ("%s[%s]" % (expr, ':'.join(args))), prec

	def getArgString(self, node):
		args = [self.process(arg, 24) for arg in node.args]

		args.extend(["%s=%s" % (name, self.process(arg, 24)) for name, arg in node.kwds])

		if node.vargs:
			args.append("*%s" % self.process(node.vargs, 24))

		if node.kargs:
			args.append("**%s" % self.process(node.kargs, 24))

		return ', '.join(args)

	def visitCall(self, node):
		prec = 4
		expr = self.process(node.expr, prec)
		assert isinstance(expr, str)

		argstr = self.getArgString(node)

		return ("%s(%s)" % (expr, argstr)), prec

	def visitDirectCall(self, node):
		prec = 4

		if node.code is not None:
			funcname = node.code.name
		else:
			funcname = "???" # This is an error, but if it occurs we need to be able to visualize it.

		if node.selfarg:
			selfarg = self.process(node.selfarg, prec)
		else:
			selfarg = "None"

		argstr = self.getArgString(node)

		return ("<%s, %s>(%s)" % (funcname, selfarg, argstr)), prec

	def visitMethodCall(self, node):
		prec = 4

		expr = self.process(node.expr, prec)
		name = self.process(node.name, prec)

		argstr = self.getArgString(node)

		return ("%s{%s}(%s)" % (expr, name, argstr)), prec


	def visitCached(self, node):
		if node in self.collapsed:
			return self.collapsed[node]
		else:
			return self.visit(node)


	def visitShortCircutOr(self, node):
		prec = 22
		partial = []


		for i, term in enumerate(node.terms):
			assert isinstance(term, ast.Condition), term
			text, inner = self.parent.process(term)
			partial.append(protect(text, inner, prec))

			if i == 0: self.parent.enterSupress()

		self.parent.exitSupress()

		return " or ".join(partial), prec

	def visitShortCircutAnd(self, node):
		prec = 21
		partial = []
		for i, term in enumerate(node.terms):
			assert isinstance(term, ast.Condition), term
			text, inner = self.parent.process(term)
			partial.append(protect(text, inner, prec))
			if i == 0: self.parent.enterSupress()

		self.parent.exitSupress()
		return " and ".join(partial), prec


	def process(self, node, precedence=24, right=False):
		text, innerPrec = self.visitCached(node)
		text = protect(text, innerPrec, precedence, right)
		return text

	def processCollapsed(self, lcl, expr):
		assert lcl in self.collapsable, (lcl, self.collapsable)
		self.collapsed[lcl] = self.visitCached(expr)

def protect(text, inner, outer, right=False):
	if inner > outer or right and inner == outer:
		text = "(%s)" % text
	return text


class SimpleCodeGen(StandardVisitor):
	def __init__(self, out=None):
		if out is None:
			out = PythonOutput(sys.stdout)
		elif not isinstance(out, PythonOutput):
			out = PythonOutput(out)
		self.out = out

		self.collapsable = set()

		self.seg = SimpleExprGen(self)
		self.seg.collapsable = self.collapsable

		self.supressStatements = 0

	def getLocalName(self, node):
		return self.seg.getLocalName(node)

	def enterSupress(self):
		self.supressStatements += 1

	def exitSupress(self):
		assert self.supressStatements > 0
		self.supressStatements -= 1

	def emitStatement(self, stmt):
		if self.supressStatements:
			if False:
				raise UncollapsableCodeError, stmt
			else:
				print "Tried to emit %r inside a conditional." % stmt
				return

		self.out.emitStatement(stmt)

	def process(self, node):
##		assert hasattr(node, 'onEntry'), type(node)
##
##		for partialmerge in node.onEntry:
##			self.process(partialmerge)

		result = self.visit(node)

##		for partialmerge in node.onExit:
##			self.process(partialmerge)

		return result

	def processNoEmit(self, node):
		self.enterSupress()
		ret = self.process(node)
		self.exitSupress()
		return ret

	def visitReturn(self, node):
		expr = ", ".join([self.seg.process(expr) for expr in node.exprs])

		if expr != 'None':
			self.emitStatement("return %s" % expr)
		else:
			self.emitStatement("return")

	def visitRaise(self, node):
		args = []
		if node.exception:
			args.append(self.seg.process(node.exception))
			if node.parameter:
				args.append(self.seg.process(node.parameter))
				if node.traceback:
					args.append(self.seg.process(node.traceback))

		if args:
			self.emitStatement("raise %s" % ", ".join(args))
		else:
			# TODO make illegal outside of an except block?
			self.emitStatement("raise")


	def visitBreak(self, node):
		self.emitStatement("break")

	def visitContinue(self, node):
		self.emitStatement("continue")

	def visitSetAttr(self, node):
		name = getConstant(node.name, str)
		stmt = "%s.%s = %s" % (self.seg.process(node.expr, 7), name, self.seg.process(node.value))
		self.emitStatement(stmt)

	def visitDeleteAttr(self, node):
		name = getConstant(node.name, str)
		stmt = "del %s.%s" % (self.seg.process(node.expr, 7), name)
		self.emitStatement(stmt)

	def visitSetCellDeref(self, node):
		stmt = "%s = %s" % (self.seg.process(node.cell), self.seg.process(node.value))
		self.emitStatement(stmt)


	def handleSliceArgs(self, node):
		if node.step:
			args = (node.start, node.stop, node.step)
		else:
			args = (node.start, node.stop)

		args = [self.seg.processNone(arg, 24, '') for arg in args]
		return ':'.join(args)

	def visitSetSlice(self, node):
		value = self.seg.process(node.value)
		expr = self.seg.process(node.expr, 4)

		args = self.handleSliceArgs(node)

		stmt = "%s[%s] = %s" % (expr, args, value)

		self.emitStatement(stmt)

	def visitDeleteSlice(self, node):
		expr = self.seg.process(node.expr, 4)
		args = self.handleSliceArgs(node)

		stmt = "del %s[%s]" % (expr, args)

		self.emitStatement(stmt)

	def visitSetSubscript(self, node):
		value = self.seg.process(node.value)
		expr = self.seg.process(node.expr, 7)
		subscript = self.seg.process(node.subscript)

		stmt = "%s[%s] = %s" % (expr, subscript, value)

		self.emitStatement(stmt)


	def visitDeleteSubscript(self, node):
		expr = self.seg.process(node.expr, 7)
		subscript = self.seg.process(node.subscript)

		stmt = "del %s[%s]" % (expr, subscript)

		self.emitStatement(stmt)

	def visitSetGlobal(self, node):
		name = getConstant(node.name)
		value = self.seg.process(node.value)

		stmt = "%s = %s" % (name, value)
		self.emitStatement(stmt)

	def visitDeleteGlobal(self, node):
		name = getConstant(node.name)
		stmt = "del %s" % (name)
		self.emitStatement(stmt)


	def visitUnpackSequence(self, node):
		assert not self.supressStatements
		expr  = self.seg.process(node.expr)
		targets = [self.seg.process(target) for target in node.targets]
		stmt = "%s, = %s" % ((", ".join(targets)), expr)
		self.emitStatement(stmt)

	def visitAssign(self, node):
		if isinstance(node.expr, ast.BinaryOp) and node.expr.op in opnames.inplaceOps:
			assert len(node.lcls) == 1
			target = node.lcls[0]

			#assert not node.lcl in self.collapsable
			# Workarround for synthesizing inplace BinaryOps that don't put their result into the left argument.
			# If the operation actually is inplace, don't hack it.

			temp = node.expr.right
			if target != node.expr.left:
				if target == node.expr.right:
					# Take care of the case Assign(a, BinaryOp(b, inplace, a))
					# Otherwise the subsequent statement cobbers the right value.
					temp = Local()
					stmt = "%s = %s" % (self.seg.process(temp), self.seg.process(node.expr.right))
					self.emitStatement(stmt)

				stmt = "%s = %s" % (self.seg.process(target), self.seg.process(node.expr.left))
				self.emitStatement(stmt)

			stmt = "%s %s %s" % (self.seg.process(target), node.expr.op, self.seg.process(temp))
			self.emitStatement(stmt)
		elif isinstance(node.expr, ast.MakeFunction):
			assert len(node.lcls) == 1
			# HACK to rename the function
			self.process(node.expr)
			name = node.expr.code.name
			lcl = self.seg.process(node.lcls[0])
			if name != lcl:
				self.emitStatement("%s = %s" % (lcl, name))
		elif isinstance(node.expr, ast.Existing) and node.expr.object.isConstant() and isinstance(node.expr.object.pyobj, types.CodeType):
			# HACK
			pass
##		elif isinstance(node.expr, (ast.ShortCircutAnd, ast.ShortCircutOr)):
##			expr, p = self.visit(node.expr)
##
##			stmt = "%s = %s" % (self.seg.process(node.lcl), expr)
##			self.emitStatement(stmt)
		else:
			if len(node.lcls) == 1 and node.lcls[0] in self.collapsable and self.supressStatements:
			#if node.lcl in self.collapsable:
				self.seg.processCollapsed(node.lcls[0], node.expr)
			else:
				stmt = "%s = %s" % (', '.join([self.seg.process(lcl) for lcl in node.lcls]), self.seg.process(node.expr))

				self.emitStatement(stmt)

	def visitDiscard(self, node):
		stmt = self.seg.process(node.expr)
		self.emitStatement(stmt)

	def visitStore(self, node):
		stmt = "<store>(%s, %r, %s, %s)" % (self.seg.process(node.expr, 24), node.fieldtype, self.seg.process(node.name, 24), self.seg.process(node.value, 24))
		self.emitStatement(stmt)

	def visitDelete(self, node):
		lcl = self.seg.process(node.lcl)
		self.emitStatement("del %s" % lcl)

	def visitPrint(self, node):
		parts = []

		if node.target:
			target = self.seg.process(node.target)
			target = ">> "+target
			parts.append(target)

		if node.expr:
			expr = self.seg.process(node.expr)
			expr = expr+","
			parts.append(expr)

		if parts:
			self.emitStatement("print %s" % ", ".join(parts))
		else:
			self.emitStatement("print")

	def visitCondition(self, node):
		self.process(node.preamble)

		conditional = node.conditional

		if isinstance(conditional, ast.ConvertToBool):
			conditional = conditional.expr

		if conditional in self.seg.collapsed:
			return self.seg.collapsed[conditional]
		else:
			return self.seg.visit(conditional)

	def visitShortCircutOr(self, node):
		prec = 22
		partial = []
		for term in node.terms:
			text, inner = self.process(term)
			partial.append(protect(text, inner, prec))
		return " or ".join(partial), prec

	def visitShortCircutAnd(self, node):
		prec = 21
		partial = []
		for term in node.terms:
			text, inner = self.process(term)
			partial.append(protect(text, inner, prec))
		return " and ".join(partial), prec

	def visitSwitch(self, node):
		cond, prec = self.process(node.condition)

		self.out.startBlock('if %s' % cond)
		self.process(node.t)
		self.out.endBlock()

		if node.f and node.f.significant():
			self.out.startBlock("else")
			self.process(node.f)
			self.out.endBlock()

	def visitExceptionHandler(self, node):
		self.processNoEmit(node.preamble)

		t = self.seg.process(node.type)
		args = [t]

		if node.value:
			value = self.seg.process(node.value)
			args.append(value)

		self.out.startBlock('except %s' % ", ".join(args))
		self.process(node.body)
		self.out.endBlock()

	def visitTryExceptFinally(self, node):
		self.out.startBlock('try')
		self.process(node.body)
		self.out.endBlock()

		for handler in node.handlers:
			self.process(handler)

		if node.defaultHandler:
			self.out.startBlock("except")
			self.process(node.defaultHandler)
			self.out.endBlock()

		if node.else_:
			self.out.startBlock("else")
			self.process(node.else_)
			self.out.endBlock()

		if node.finally_:
			self.out.startBlock("finally")
			self.process(node.finally_)
			self.out.endBlock()


	def visitWhile(self, node):
		cond, prec = self.process(node.condition)

		self.out.startBlock('while %s' % cond)

		self.process(node.body)

		# Do the conditions for the next loop.
		# Should, in fact, produce nothing.
		cond, prec = self.process(node.condition)

		self.out.endBlock()

		if node.else_ and node.else_.significant():
			self.out.startBlock('else')
			self.process(node.else_)
			self.out.endBlock()

	def visitFor(self, node):
		iterator = node.iterator
		index = node.index
		self.out.startBlock('for %s in %s' % (self.seg.process(index), self.seg.process(iterator)))

		self.process(node.body)

		self.out.endBlock()

		if node.else_ and node.else_.significant():
			self.out.startBlock('else')
			self.process(node.else_)
			self.out.endBlock()


	def visitSuite(self, node):
		for child in node.blocks:
			self.process(child)

	def visitCode(self, node, name=None):
		if name is None: name = node.name
		assert isIdentifier.match(name), name

		(defines, uses), (globaldefines, globaluses), collapsable = defuse.defuse(node)
		self.collapsable.update(collapsable)

		p = node.codeparameters

		# Set parmeter names
		for lcl, pname in zip(p.params, p.paramnames):
			self.seg.setLocalName(lcl, pname)

		args = [self.seg.process(param) for param in p.params]

		if p.vparam:
			args.append("*%s" % self.seg.process(p.vparam))


		if p.kparam:
			args.append("**%s" % self.seg.process(p.kparam))


		self.out.startBlock("def %s(%s)" % (name, ', '.join(args)))

		# If globals are written to, define them here.
		glbldef = [name for name in globaldefines.iterkeys()]
		if glbldef: self.out.emitStatement("global %s" % ", ".join(glbldef))

		self.process(node.ast)
		self.out.endBlock()

	def visitMakeFunction(self, node):
		assert not node.defaults

		#assert not node.cells
		self.visit(node.code)

	def visitLibrary(self, node):
		self.emitStatement("# CANNOT GENERATE CODE FOR LIBRARY.")
