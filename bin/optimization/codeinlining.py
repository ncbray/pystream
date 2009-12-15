from util.typedispatch import *
from language.python import ast

import optimization.simplify

from analysis.astcollector import getOps

# Determines the technical feasibility of inlining
class CodeInliningAnalysis(TypeDispatcher):
	def __init__(self):
		self.canInline   = {}
		self.invokeCount = {}
		self.numOps      = {}

	@dispatch(type(None), str, int, ast.Local, ast.Existing, ast.Code)
	def visitLeaf(self, node):
		pass

	@dispatch(ast.Suite, list, ast.Condition, ast.Assign, ast.Discard, ast.TypeSwitchCase)
	def visitOK(self, node):
		node.visitChildren(self)

	@dispatch(ast.Call, ast.DirectCall, ast.MethodCall, ast.Allocate, ast.Load, ast.Store, ast.Check)
	def visitOp(self, node):
		self.ops += 1

		invokes = node.annotation.invokes
		if invokes:
			# Eliminate duplicate code targets
			targets = set()
			for code, context in invokes[0]:
				targets.add(code)

			# Increment the count of each target
			for code in targets:
				if code not in self.invokeCount:
					self.invokeCount[code] = 1
				else:
					self.invokeCount[code] += 1

		if self.terminal:
			# Op after return prevents inlining
			self.inlinable = False

	@dispatch(ast.Return)
	def visitReturn(self, node):
		if self.terminal:
			# Return after return
			self.inlinable = False
		elif self.level > 0:
			# No returns from inside loops/trys/etc.
			# The would require manually unwinding the stack if inlined.
			self.inlinable = False

		# No more ops after return
		self.terminal = True

	def processSwitch(self, cases):
		original = self.terminal
		allterminal = original

		for case in cases:
			self.terminal = original
			self(case)
			allterminal |= self.terminal

		self.terminal |= allterminal

	@dispatch(ast.Switch)
	def visitSwitch(self, node):
		self(node.condition)
		self.processSwitch((node.t, node.f))

	@dispatch(ast.TypeSwitch)
	def visitTypeSwitch(self, node):
		self(node.conditional)
		self.processSwitch(node.cases)

	@dispatch(ast.For, ast.While)
	def visitControlFlow(self, node):
		self.level += 1
		node.visitChildren(self)
		self.level -= 1

	def process(self, node):
		self.level = 0
		self.ops = 0

		# Terminal indicates
		self.terminal = False

		# Initial value
		callee = node.codeParameters()
		self.inlinable = node.isStandardCode() and not isinstance(callee.vparam, ast.Local) and not isinstance(callee.kparam, ast.Local) and not node.annotation.descriptive

		if self.inlinable:
			self(node.ast)

		self.canInline[node] = self.inlinable
		self.numOps[node] = self.ops

# Emulates calling convention assignments
# Clones the code and translates the inlined contexts
class OpInliningTransform(TypeDispatcher):
	def __init__(self, analysis):
		self.analysis  = analysis

	def translateLocal(self, node):
		if not node in self.localMap:
			lcl = ast.Local(node.name)
			self.localMap[node] = lcl
			self.transferLocal(node, lcl)
		else:
			lcl = self.localMap[node]
		return lcl

	def transferAnalysisData(self, original, replacement):
		if not isinstance(original, (ast.Expression, ast.Statement)):    return
		if not isinstance(replacement, (ast.Expression, ast.Statement)): return
		assert original is not replacement, original

		replacement.annotation = original.annotation.contextSubset(self.contextRemap)
		replacement.rewriteAnnotation(origin=self.originalNode.annotation.origin+replacement.annotation.origin)

		assert replacement.annotation.compatable(self.dst.annotation)

	def transferLocal(self, original, replacement):
		assert original is not replacement, original
		replacement.annotation = original.annotation.contextSubset(self.contextRemap)

	@dispatch(type(None), str, int)
	def visitLeaf(self, node):
		return node

	@defaultdispatch
	def default(self, node):
		result = node.rewriteCloned(self)
		self.transferAnalysisData(node, result)
		return result

	@dispatch(ast.Local)
	def visitLocal(self, node):
		return self.translateLocal(node)

	@dispatch(ast.DoNotCare)
	def visitDoNotCare(self, node):
		return ast.DoNotCare()

	# Has internal slots, so as a hack it is "shared", so we must manually rewrite
	@dispatch(ast.Existing)
	def visitExisting(self, node):
		result = ast.Existing(node.object)
		self.transferLocal(node, result)
		return result

	@dispatch(ast.Code)
	def visitCode(self, node):
		return node

	@dispatch(ast.Return)
	def visitReturn(self, node):
		if self.returnargs is not None:
			# Inlined into assignment
			assert len(self.returnargs) == len(node.exprs)
			return [ast.Assign(self(src), [dst]) for src, dst in zip(node.exprs, self.returnargs)]
		else:
			# Inlined into discard
			return []

	def process(self, dst, originalNode, code, map, selfarg, args, returnargs):
		self.localMap = {}

		self.dst = dst
		self.originalNode = originalNode
		self.contextRemap = map

		self.returnargs = returnargs
		outp = []

		p = code.codeparameters

		# Do argument transfer
		if isinstance(p.selfparam, ast.Local):
			outp.append(ast.Assign(selfarg, [self(p.selfparam)]))

		for arg, param in zip(args, p.params):
			if isinstance(param, ast.Local):
				outp.append(ast.Assign(arg, [self(param)]))

		assert not isinstance(p.vparam, ast.Local), p.vparam
		#assert len(args) == len(p.params), "TODO: default arguments."

		outp.append(self(code.ast))


		return outp

# Performs depth-first traversal of call graph,
# inlines code in reverse postorder.
class CodeInliningTransform(TypeDispatcher):
	def __init__(self, analysis, compiler, intrinsics):
		self.analysis  = analysis
		self.compiler  = compiler
		self.intrinsics = intrinsics
		self.opinline = OpInliningTransform(analysis)
		self.processed = set()
		self.trace     = set()

		self.maxInvokes       = 1
		self.maxOps           = 4
		self.exhaustive       = True
		self.preserveContexts = not self.exhaustive

	# May contain inlinable nodes
	@dispatch(ast.Suite, list, ast.Condition, ast.Switch, ast.For, ast.While, ast.TypeSwitch, ast.TypeSwitchCase)
	def visitOK(self, node):
		return node.rewriteChildren(self)

	# Contains no inlinable nodes
	@dispatch(ast.Load, ast.Store, ast.Check, ast.Allocate,
		ast.Local, ast.Existing, ast.Code,
		ast.Return,
		type(None), str, int)
	def visitInlineLeaf(self, node, returnargs=None):
		return node

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		result = self(node.expr, node.lcls)
		return result if isinstance(result, list) else node

	@dispatch(ast.Discard)
	def visitDiscard(self, node):
		result = self(node.expr, None)
		return result if isinstance(result, list) else node

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node, returnargs):
		self.processInvocations(node)

		if not node.kargs and not node.vargs and not node.kwds:
			return self.tryInline(node, node.selfarg, node.args, returnargs)
		else:
			return None

	@dispatch(ast.Call)
	def visitCall(self, node, returnargs):
		self.processInvocations(node)

		if not node.kargs and not node.vargs and not node.kwds:
			return self.tryInline(node, node.expr, node.args, returnargs)
		else:
			return None

	@dispatch(ast.MethodCall)
	def visitMethodCall(self, node, returnargs):
		self.processInvocations(node)

		# TODO inline method calls?  This may require a bit of effort,
		# primarily in finding the correct value(s) for selfarg...
		return None

	def tryInline(self, node, selfarg, args, returnargs):
		# Don't inline anything into descriptive stubs
		if self.code.annotation.descriptive: return None

		# Do we have invocation information?
		invokes = node.annotation.invokes
		if invokes is None: return None

		allCode = None
		map = []
		for invs in invokes[1]:
			if len(invs) == 0:
				map.append(-1)
			elif len(invs) == 1:
				code, context = invs[0]

				# Must only invoke one code
				if allCode is None:
					# It must be possible to inline the code
					if not self.analysis.canInline[code]:
						return None
					allCode = code
				elif allCode != code:
					return None

				map.append(code.annotation.contexts.index(context))
			else:
				# Don't merge contexts, as precision will be lost?
				if self.preserveContexts: return None

				multi = []
				for code, context in invs:
					if allCode is None:
						# It must be possible to inline the code
						if not self.analysis.canInline[code]:
							return None
						allCode = code
					elif allCode != code:
						return None
					multi.append(code.annotation.contexts.index(context))

				map.append(multi)

		# No invocation
		if allCode is None: return None

		# Prevent recursive inlining
		if allCode in self.trace: return None

		# Only one calling point, or it's a small function
		tooManyInvokes = self.analysis.invokeCount[allCode] > self.maxInvokes
		tooManyOps     = self.analysis.numOps[allCode] > self.maxOps

		if not self.exhaustive and tooManyInvokes and tooManyOps:
			return None

		assert len(map) == len(self.code.annotation.contexts)

		# Prevent the inlining of potential intrinsics.
		if self.intrinsics(None, node) is not None:
#			print "INTRINSIC", node
#			print node.code.annotation.origin
#			print
			return None

		# Eliminate the call
		self.analysis.numOps[self.code] -= 1

		# Add the new ops
		# This is approximate, as post-inlining simplification can reduce the number
		self.analysis.numOps[self.code] += self.analysis.numOps[allCode]

		self.modified = True

		return self.opinline.process(self.code, node, allCode, map, selfarg, args, returnargs)

	def processInvocations(self, node):
		invokes = node.annotation.invokes
		if invokes:
			old = self.code
			oldM = self.modified
			for code, context in invokes[0]:
				self.process(code)
			self.code = old
			self.modified = oldM

	def process(self, node):
		if node not in self.processed:
			assert node.isCode(), type(node)

			self.processed.add(node)
			self.trace.add(node)
			self.modified = False
			self.code = node

			if node.isStandardCode():
				result = self(node.ast)
				if self.modified:
					node.ast = result
					# Always done imediately after inlining, so if we inline
					# this function, less needs to be processed.
					optimization.simplify.evaluateCode(self.compiler, node)
			else:
				ops, lcls = getOps(node)
				for op in ops:
					self.processInvocations(op)

			self.code = None
			self.trace.remove(node)

import translator.glsl.intrinsics

def evaluate(compiler):
	with compiler.console.scope('code inlining'):
		analysis  = CodeInliningAnalysis()
		for code in compiler.liveCode:
			analysis.process(code)

		intrinsics = translator.glsl.intrinsics.makeIntrinsicRewriter(compiler.extractor)

		transform = CodeInliningTransform(analysis, compiler, intrinsics)
		for code in compiler.interface.entryCode():
			if True:
				try:
					transform.process(code)
				except:
					compiler.console.output('Failed to transform %r' % code)
					raise
			else:
				transform.process(code)
