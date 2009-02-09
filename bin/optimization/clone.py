# Split contexts unless types match
# Add type-switched disbatch where cloning does not work?

# Whole program optimization

import collections

from PADS.UnionFind import UnionFind

from util.typedispatch import *

from programIR.python import ast

from simplify import simplify

import copy

# Figures out what functions should have seperate implementations,
# to improve optimization / realizability
class ProgramCloner(object):
	def __init__(self, console, adb):
		self.console = console
		self.adb = adb

		# func -> context -> context set
		self.different = collections.defaultdict(lambda: collections.defaultdict(set))

		self.liveFunctions = self.adb.liveFunctions()

		self.liveContexts = {}
		self.liveOps = {}

		for code in self.liveFunctions:
			self.liveContexts[code] = frozenset(self.adb.functionContexts(code))
			self.liveOps[code] = self.adb.functionOps(code)

		# HACK, ensure the keys exist
		for func in self.liveFunctions:
			different = self.different[func]
			for context in adb.functionContexts(func):
				different[context]

	def listGroups(self):
		for func, groups in self.groups.iteritems():
			if len(groups) > 1:
				self.console.output("%s %d groups" % (func.name, len(groups)))

	def makeGroups(self):
		# Create groups of contexts
		self.groups = {}
		for func in self.liveFunctions:
			self.groups[func] = self.makeFuncGroups(func)

		# Create context -> group mapping
		self.groupLUT = {}
		numGroups = 0
		for func, groups in self.groups.iteritems():
			for group in groups:
				numGroups += 1
				for context in group:
					assert not context in self.groupLUT, context
					self.groupLUT[context] = id(group) # HACK, as sets are not hashable.

		return numGroups

	def makeFuncGroups(self, code):
		groups = []

		different = self.different[code]

		for context in self.adb.functionContexts(code):
			assert context.signature.code is code, (context, code)
			for group in groups:
				assert context in different
				if not different[context].intersection(group):
					group.add(context)
					break
			else:
				groups.append(set((context,)))
		return groups

	def findInitialConflicts(self):
		# Clone loads from different fields
		for code, codeinfo in self.adb.db.lifetime.readDB:
			contexts = self.liveContexts[code]
			for op, opinfo in codeinfo:
				# Only split loads for reading different fields
				if isinstance(op, ast.Load):
					lut = collections.defaultdict(set)
					for context, slots in opinfo:
						if slots:
							fields = frozenset([slot.slotName for slot in slots])
							lut[fields].add(context)

					self.markDifferentContexts(code, contexts, lut)


		# Clone stores to different fields
		for code, codeinfo in self.adb.db.lifetime.modifyDB:
			contexts = self.liveContexts[code]
			for op, opinfo in codeinfo:
				# Only split loads for reading different fields
				if isinstance(op, ast.Store):
					lut = collections.defaultdict(set)
					for context, slots in opinfo:
						if slots:
							fields = frozenset([slot.slotName for slot in slots])
							lut[fields].add(context)

					self.markDifferentContexts(code, contexts, lut)


		# Clone different allocates based on the type pointer
		for code in self.liveFunctions:
			# Two contexts should not be the same if they contain an op that
			# invokes different sets of functions.
			codeInfo = self.adb.db.functionInfo(code)
			contexts = self.liveContexts[code]

			for op in self.adb.functionOps(code):
				if isinstance(op, ast.Allocate):
					lut = collections.defaultdict(set)

					typeExpr = op.expr
					clclInfo = codeInfo.localInfo(typeExpr)
					for context, lclInfo in clclInfo.contexts.iteritems():
						types = frozenset([ref.xtype.obj for ref in lclInfo.references])
						lut[types].add(context)

					self.markDifferentContexts(code, contexts, lut)


	def findConflicts(self):
		self.realizable = True
		for code in self.liveFunctions:
			# Two contexts should not be the same if they contain an op that
			# invokes different sets of functions.
			for op in self.liveOps[code]:

				# Cache the contexts, as we'll need them later.
				contexts = self.liveContexts[code]

				lut = collections.defaultdict(set)
				label = {}
				u = UnionFind()

				# Find the different call patterns.
				# Using union find on the invocation edges
				# helps avoid a problem where the edges in one context
				# May be a subset of another context.
				for context in contexts:
					assert context.signature.code is code, (context, code)

					invocations = self.adb.invocationsForContextOp(code, op, context)
					translated = [self.groupLUT[dst] for dst in invocations]

					label[context] = translated[0] if translated else None
					translated = frozenset(translated)
					if len(translated) >= 2:
						u.union(*translated)

						print "Conflict"
						print code.name
						print type(op)
						for inv in invocations:
							print '\t*', self.groupLUT[inv], inv
						print

						# More that one call target.
						self.realizable = False

				for context in contexts:
					group = u[label[context]]
					lut[group].add(context)

				self.markDifferentContexts(code, contexts, lut)

	def markDifferentContexts(self, code, contexts, lut):
		# Mark contexts with different call patterns as different.
		different = self.different[code]
		for group in lut.itervalues():
			assert contexts.issuperset(group), (func.name, [c.code.name for c in group])

			# Contexts not in the current group
			diff = contexts-group

			for context in group:
				different[context].update(diff)

	def createNewCodeNodes(self):
		newfunc = {}

		# Create the new functions.
		for code, groups in self.groups.iteritems():
			newfunc[code] = {}
			uid = 0
			for group in groups:
				if len(groups) > 1:
					name = "%s_clone_%d" % (code.name, uid)
				else:
					name = code.name

				newfunc[code][id(group)] = ast.Code(name, None, None, None, None, None, None, None)
				uid += 1
		return newfunc


	def rewriteProgram(self, extractor, entryPoints):
		newfunc = self.createNewCodeNodes()

		# Clone all of the functions.
		for code, groups in self.groups.iteritems():
			for group in groups:
				newcode = newfunc[code][id(group)]

				# Transfer information that is tied to the context.
				self.adb.trackContextTransfer(code, newcode, group)

				fc = FunctionCloner(self.adb, newfunc, self.groupLUT, code, newcode, group)
				fc.process()
				simplify(extractor, self.adb, newcode)



		# HACK Horrible, horrible hack: assumes that the entry point cannot be cloned.
		# This will be the case for most situations we're interested in... but still.  Ugly.
		newEP = []
		for func, funcobj, args in entryPoints:
			groups = newfunc[func]
			assert len(groups) == 1
			clonecode = groups.items()[0][1]
			func = clonecode
			newEP.append((func, funcobj, args))


		# HACK Mutate the list.
		# Used so everyone gets the update version
		entryPoints[:] = newEP

		# Collect and return the new functions.
		funcs = []
		for func, groups in newfunc.iteritems():
			funcs.extend(groups.itervalues())

		return funcs



class FunctionCloner(object):
	__metaclass__ = typedispatcher

	def __init__(self, adb, newfuncLUT, groupLUT, sourcefunction, destfunction, group):
		self.adb = adb
		self.newfuncLUT = newfuncLUT
		self.groupLUT = groupLUT
		self.sourcefunction = sourcefunction
		self.destfunction   = destfunction
		self.group    = group

		self.localMap = {}


		self.originalInfo = self.adb.db.functionInfo(self.sourcefunction)
		self.newInfo      = self.adb.db.functionInfo(self.destfunction)

		# Keep the function annotations.
		self.newInfo.original    = self.originalInfo.original
		self.newInfo.descriptive = self.originalInfo.descriptive
		self.newInfo.returnSlot  = self.translateLocal(self.originalInfo.returnSlot)

		self.newInfo.contexts.update(group)

	def translateLocal(self, node):
		if not node in self.localMap:
			lcl = ast.Local(node.name)
			self.localMap[node] = lcl
			self.transferLocal(node, lcl)
		else:
			lcl = self.localMap[node]
		return lcl

	@defaultdispatch
	def default(self, node):
		result = allChildren(self, node)
		self.transferAnalysisData(node, result)
		return result

	@dispatch(ast.Local)
	def visitLocal(self, node):
		return self.translateLocal(node)

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node):
		tempresult = self.default(node)

		# Redirect the direct call to the new, cloned function.
		# If the op is unreachable in this context, there may be no invocations.
		invocations = self.adb.invocationsForOp(self.destfunction, tempresult)
		if invocations:
			# We do this computation after transfer, as it can reduce the number of invocations.
			func = self.adb.singleCall(self.destfunction, tempresult)
			if not func:
				names = [inv.name for inv in invocations]
				raise Exception, "Cannot clone the direct call, as it has multiple targets. %r" % names
			result = ast.DirectCall(func, *tempresult.children()[1:])

			self.adb.trackRewrite(self.destfunction, tempresult, result)
		else:
			result = tempresult

		return result

	def translateFunctionContext(self, func, context):
		newfunc = self.newfuncLUT[func][self.groupLUT[context]]
		return context, newfunc

	def transferAnalysisData(self, original, replacement):

		if not isinstance(original, (ast.Expression, ast.Statement)):    return
		if not isinstance(replacement, (ast.Expression, ast.Statement)): return

		def mapper(target):
			c, func = target
			return self.translateFunctionContext(func, c)

		self.adb.trackOpTransfer(self.sourcefunction, original, self.destfunction, replacement, self.group, mapper)

	def transferLocal(self, original, replacement):
		self.adb.trackLocalTransfer(self.sourcefunction, original, self.destfunction, replacement, self.group)

	def process(self):
		srccode = self.sourcefunction
		dstcode = self.destfunction

		dstcode.selfparam      = self(srccode.selfparam)
		dstcode.parameters     = self(srccode.parameters)
		dstcode.parameternames = self(srccode.parameternames)
		dstcode.vparam         = self(srccode.vparam)
		dstcode.kparam         = self(srccode.kparam)
		dstcode.returnparam    = self(srccode.returnparam)
		dstcode.ast            = self(srccode.ast)


def clone(console, extractor, entryPoints, adb):
	console.begin('analysis')
	cloner = ProgramCloner(console, adb)

	cloner.findInitialConflicts()
	cloner.makeGroups()

	oldNumGroups = 0
	originalNumGroups = len(cloner.liveFunctions)
	numGroups = originalNumGroups

	while numGroups > oldNumGroups:
		oldNumGroups = numGroups

		cloner.findConflicts()
		numGroups = cloner.makeGroups()

	console.output("=== Split ===")
	cloner.listGroups()
	console.output("Realizable: %r" % cloner.realizable)
	console.output("Num groups %d / %d / %d" %  (numGroups, oldNumGroups, originalNumGroups))
	console.output('')

	console.end()

	assert cloner.realizable

	# Is cloning worth while?
	if numGroups > originalNumGroups:
		console.begin('rewrite')
		cloner.rewriteProgram(extractor, entryPoints)
		console.end()