from util.typedispatch import *
from programIR.python import ast

from . simplify import simplify

# Determines the technical feasability of inlining
class CodeInliningAnalysis(object):
	__metaclass__ = typedispatcher

	def __init__(self):
		self.canInline   = {}
		self.invokeCount = {}
		self.numOps      = {}

	@defaultdispatch
	def default(self, node):
		assert False, node

	@dispatch(type(None), str, int, ast.Local, ast.Existing, ast.Code)
	def visitLeaf(self, node):
		pass

	@dispatch(ast.Suite, list, ast.Condition, ast.Assign, ast.Discard)
	def visitOK(self, node):
		visitAllChildren(self, node)

	@dispatch(ast.Call, ast.DirectCall, ast.Allocate, ast.Load, ast.Store, ast.Check)
	def visitOp(self, node):
		self.ops += 1

		invokes = node.annotation.invokes
		if invokes:
			# Eliminate duplacate code targets
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


	@dispatch(ast.Switch)
	def visitSwitch(self, node):
		self(node.condition)

		original = self.terminal
		self(node.t)
		t = self.terminal

		self.terminal = original
		self(node.f)
		self.terminal |= t

	@dispatch(ast.For, ast.While)
	def visitControlFlow(self, node):
		self.level += 1
		visitAllChildren(self, node)
		self.level -= 1

	def process(self, node):
		self.level = 0
		self.ops = 0

		# Terminal indicates
		self.terminal = False

		# Inital value
		self.inlinable = not node.vparam and not node.kparam and not node.annotation.descriptive
		self(node.ast)

		self.canInline[node] = self.inlinable
		self.numOps[node] = self.ops

# Emulates calling convention assignments
# Clones the code and translates the inlined contexts
class OpInliningTransform(object):
	__metaclass__ = typedispatcher

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

		assert replacement.annotation.compatable(self.dst.annotation)

	def transferLocal(self, original, replacement):
		assert original is not replacement, original
		replacement.annotation = original.annotation.contextSubset(self.contextRemap)

	@defaultdispatch
	def default(self, node):
		result = allChildren(self, node, clone=True)
		self.transferAnalysisData(node, result)
		return result

	@dispatch(ast.Local)
	def visitLocal(self, node):
		return self.translateLocal(node)

	# Has internal slots, so as a hack it is "shared", so we must manually rewrite
	@dispatch(ast.Existing)
	def visitExisting(self, node):
		return ast.Existing(node.object)

	@dispatch(ast.Code)
	def visitCode(self, node):
		return node

	@dispatch(ast.Return)
	def visitReturn(self, node):
		if self.returnarg:
			# Inlined into assignment
			expr = self(node.expr)
			assert expr
			return ast.Assign(expr, self.returnarg)
		else:
			# Inlined into discard
			return []

	def process(self, dst, code, map, selfarg, args, returnarg):
		self.localMap = {}

		self.dst = dst
		self.contextRemap = map
		self.returnarg = returnarg
		outp = []

		# Do argument transfer
		if selfarg:
			outp.append(ast.Assign(selfarg, self(code.selfparam)))

		assert len(args) == len(code.parameters), "TODO: default arguments."
		for arg, param in zip(args, code.parameters):
			outp.append(ast.Assign(arg, self(param)))

		outp.append(self(code.ast))


		return outp

# Performs depth-first traversal of call graph,
# inlines code in reverse postorder.
class CodeInliningTransform(object):
	__metaclass__ = typedispatcher

	def __init__(self, analysis, dataflow, adb):
		self.analysis  = analysis
		self.dataflow = dataflow
		self.adb = adb
		self.opinline = OpInliningTransform(analysis)
		self.processed = set()
		self.trace     = set()

	@defaultdispatch
	def default(self, node):
		assert False, node

	# May contain inlinable nodes
	@dispatch(ast.Suite, list, ast.Condition, ast.Switch, ast.For, ast.While)
	def visitOK(self, node):
		return allChildren(self, node)

	# Contains no inlinable nodes
	@dispatch(ast.Load, ast.Store, ast.Check, ast.Allocate,
		ast.Local, ast.Existing, ast.Code,
		ast.Return,
		type(None), str, int)
	def visitInlineLeaf(self, node, returnarg=None):
		return node

	@dispatch(ast.Assign)
	def visitAssign(self, node):
		result = self(node.expr, node.lcl)
		return result if isinstance(result, list) else node

	@dispatch(ast.Discard)
	def visitDiscard(self, node):
		result = self(node.expr, None)
		return result if isinstance(result, list) else node

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node, returnarg):
		self.processInvocations(node)

		if not node.kargs and not node.vargs and not node.kwds:
			return self.tryInline(node, node.selfarg, node.args, returnarg)
		else:
			return None

	@dispatch(ast.Call)
	def visitCall(self, node, returnarg):
		self.processInvocations(node)

		if not node.kargs and not node.vargs and not node.kwds:
			return self.tryInline(node, node.expr, node.args, returnarg)
		else:
			return None

	def tryInline(self, node, selfarg, args, returnarg):
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
				# Must have one-to-one context correspondence
				# Otherwise, we're loosing CPA precision
				return None

		# No invocation
		if allCode is None: return None

		# Prevent recursive inlining
		if allCode in self.trace: return None

		# Only one calling point, or it's a small function
		if self.analysis.invokeCount[allCode] > 1 and self.analysis.numOps[allCode] > 3:
			return None

		assert len(map) == len(self.code.annotation.contexts)

		# Eliminate the call
		self.analysis.numOps[self.code] -= 1

		# Add the new ops
		# This is approximate, as post-inlining simplification can reduce the number
		self.analysis.numOps[self.code] += self.analysis.numOps[allCode]

		self.modified = True

		return self.opinline.process(self.code, allCode, map, selfarg, args, returnarg)

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
			self.processed.add(node)
			self.trace.add(node)

			self.modified = False
			self.code = node
			result = self(node.ast)
			self.code = None

			if self.modified:
				node.ast = result
				# Always done imediately after inlining, so if we inline
				# this function, less needs to be processed.
				simplify(self.dataflow.extractor, self.adb, node)

			self.trace.remove(node)

def inlineCode(dataflow, entryPoints, adb):
	analysis  = CodeInliningAnalysis()
	for code in adb.db.liveFunctions():
		analysis.process(code)

	transform = CodeInliningTransform(analysis, dataflow, adb)
	for func, funcobj, args in entryPoints:
		transform.process(func)
