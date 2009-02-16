# Split contexts unless types match
# Add type-switched disbatch where cloning does not work?

# Whole program optimization

import collections
from PADS.UnionFind import UnionFind
from util.typedispatch import *
from programIR.python import ast
from simplify import simplify
from analysis.cpa import programculler

# Figures out what functions should have seperate implementations,
# to improve optimization / realizability
class ProgramCloner(object):
	def __init__(self, console, adb, liveContexts):
		self.console = console
		self.adb = adb

		# func -> context -> context set
		self.different = collections.defaultdict(lambda: collections.defaultdict(set))

		self.liveFunctions = set(liveContexts.iterkeys())
		self.liveContexts  = liveContexts

		self.liveOps = {}


		for code in self.liveFunctions:
			self.liveOps[code] = self.adb.functionOps(code)

		# HACK, ensure the keys exist
		for func in self.liveFunctions:
			different = self.different[func]
			for context in self.liveContexts[func]:
				different[context]

		# For finding the maximal clone.
		self.unify         = UnionFind()
		self.unifyGroups   = {}
		self.indirectGroup = {}
		self.dirty         = set()


	def doUnify(self, code, contexts, indirect):
		# indirect indicates the contexts can be called from an object.
		# All indirect contexts must be unified, as only one function
		# can be called indirectly.
		if indirect and code in self.indirectGroup:
			contexts.add(self.indirectGroup[code])

		if len(contexts) > 1:
			indirectGroup =  self.indirectGroup.get(code)
			# Build the new group
			group = set()
			for context in contexts:
				assert self.unify[context] is context, (context, self.unify[context])

				group.update(self.unifyGroups[context])
				del self.unifyGroups[context]

				# The context may be unified, so make sure it doesn't hand arround.
				if context in self.dirty:
					self.dirty.remove(context)

				if context is indirectGroup: indirect = True

			# Unify the contexts
			result = self.unify.union(*contexts)

			assert result is self.unify[context]
			assert result not in self.unifyGroups
			assert result not in self.dirty

			# Set the new group, and mark the context for processing.
			self.unifyGroups[result] = group
			self.dirty.add(result)

			if indirect: self.indirectGroup[code] = result
		elif indirect:
			self.indirectGroup[code] = contexts.pop()

	def unifyContexts(self):
		# Calculates the fully cloned, realizable solution.
		# This is used as an upper bound for cloning.
		# This will never generate more functions than there are contexts.
		# It is undesirable to use it directly, as it gets crazy large
		# when path sensitivity is used.
		# TODO what happens if we can insert type switches?

		# All of the contexts are dirty
		self.dirty = set()
		for code, contexts in self.liveContexts.iteritems():
			for context in contexts:
				self.unify[context]
				self.unifyGroups[context] = set((context,))
				self.dirty.add(context)

				if context.entryPoint:
					self.doUnify(code, set((context,)), True)

		while self.dirty:
			current = self.dirty.pop()
			code    = current.signature.code
			group   = self.unifyGroups[self.unify[current]]

			for op in self.liveOps[code]:
				dsts = collections.defaultdict(set)
				for context in group:
					invocations = self.adb.invocationsForContextOp(code, op, context)
					for dst in invocations:
						udst = self.unify[dst]
						assert self.unify[udst] is udst
						dsts[udst.signature.code].add(udst)

				indirect = len(dsts) > 1

				for dstcode, dstcontexts in dsts.iteritems():
					self.doUnify(dstcode, dstcontexts, indirect)

		self.codeGroups = {}
		self.groupsInvokeGroup = {}

		self.groupOpInvokes = {}

		for gid in self.unifyGroups.iterkeys():
			code = gid.signature.code
			if code not in self.codeGroups:
				self.codeGroups[code] = set()
			self.codeGroups[code].add(gid)
			self.groupsInvokeGroup[gid] = set()

		for code, groups in self.codeGroups.iteritems():
			for op in self.liveOps[code]:
				for group in groups:
					ginv = set()
					for context in self.unifyGroups[group]:
						src = self.unify[context]
						invocations = self.adb.invocationsForContextOp(code, op, context)
						for inv in invocations:
							dst = self.unify[inv]
							self.groupsInvokeGroup[dst].add(src)
							ginv.add(dst)
					self.groupOpInvokes[(group, op)] = ginv




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
		pack = []

		different = self.different[code]

		# Pack the groups
		for group in self.codeGroups[code]:
			for packed in pack:
				if not different[group].intersection(packed):
					packed.add(group)
					break
			else:
				pack.append(set((group,)))

		# Expand the packed groups
		groups = []
		for packed in pack:
			unpacked = set()
			for group in packed:
				unpacked.update(self.unifyGroups[group])
			groups.append(unpacked)

		return groups

	def labelLoad(self, code, op, group):
		contexts = self.unifyGroups[group]

		slots = set()
		for context in contexts:
			cindex = code.annotation.contexts.index(context)
			cslots = op.annotation.reads[1][cindex]
			for slot in cslots:
				slots.add(slot.slotName)

		if slots:
			return frozenset(slots)
		else:
			return None



	def labelStore(self, code, op, group):
		contexts = self.unifyGroups[group]

		slots = set()
		for context in contexts:
			cindex = code.annotation.contexts.index(context)
			cslots = op.annotation.modifies[1][cindex]
			for slot in cslots:
				slots.add(slot.slotName)

		if slots:
			return frozenset(slots)
		else:
			return None

	def labelAllocate(self, code, op, group):
		contexts = self.unifyGroups[group]

		crefs = op.expr.annotation.references

		types = set()

		if crefs is not None:
			for context in contexts:
				cindex = code.annotation.contexts.index(context)
				refs = crefs[1][cindex]
				ctypes = frozenset([ref.xtype.obj for ref in refs])

				if ctypes: types.update(ctypes)

		if types:
			if len(types) > 1:
				# No point in giving it a unique label, as it is indirect.
				return True
			else:
				return types.pop()

			return frozenset(types)
		else:
			return None

	def labelInvoke(self, code, op, group):
		targets = set([other.signature.code for other in self.groupOpInvokes[(group, op)]])

		if targets:
			if len(targets) > 1:
				# No point in giving it a unique label, as it is indirect.
				return True
			else:
				return targets.pop()
		else:
			# Do not make it a wildcard...
			return False



	def labeledMark(self, code, op, groups, labeler):
		lut = collections.defaultdict(set)
		wildcards = set()

		for group in groups:
			label = labeler(code, op, group)

			if label is not None:
				lut[label].add(group)
			else:
				# This load won't happen, so it can be paired with any other.
				# TODO when we support exceptions, be more precise.
				wildcards.add(group)

		if len(lut) > 1:
			self.markDifferentContexts(code, groups, lut, wildcards)

	def processCode(self, code):
		for code, groups in self.codeGroups.iteritems():
			for op in self.liveOps[code]:
				lut = {}
				for group in groups:
					invs = self.groupOpInvokes[(group, op)]

					if len(invs) == 1:
						inv = tuple(invs)[0]
						invCode = inv.signature.code

						for otherGroup, otherInv in lut.iteritems():
							if not self.isDifferent(code, group, otherGroup):
								otherCode = otherInv.signature.code
								if invCode is otherCode:
									if self.isDifferent(invCode, inv, otherInv):
										assert inv is not otherInv
										self.markDifferentSimple(code, group, otherGroup)

						lut[group] = inv
	def findInitialConflicts(self):
		assert not self.dirty

		# Clone loads from different fields
		for code, groups in self.codeGroups.iteritems():
			for op in self.liveOps[code]:
				# Only split loads for reading different fields
				if isinstance(op, ast.Load):
					self.labeledMark(code, op, groups, self.labelLoad)
				elif isinstance(op, ast.Store):
					self.labeledMark(code, op, groups, self.labelStore)
				elif isinstance(op, ast.Allocate):
					self.labeledMark(code, op, groups, self.labelAllocate)
				else:
					# Critical, as it allows calls to be turned into direct calls.
					self.labeledMark(code, op, groups, self.labelInvoke)

	def process(self):
		while self.dirty:
			current = self.dirty.pop()
			self.processCode(current)




	def isDifferent(self, code, c1, c2):
		diff = self.different[code]
		return c2 in diff[c1]

	def markDirty(self, context):
		newDirty = [c.signature.code for c in self.groupsInvokeGroup[context]]
		self.dirty.update(newDirty)


	def markDifferentSimple(self, code, a, b):
		different = self.different[code]
		if b not in different[a]:
			different[a].add(b)
			different[b].add(a)
			self.markDirty(a)
			self.markDirty(b)

	def markDifferentContexts(self, code, contexts, lut, wildcards=None):
		# Mark contexts with different call patterns as different.
		# This is nasty n^2, we should be keeping track of similar?
		different = self.different[code]

		if wildcards:
			certain = contexts-wildcards
		else:
			certain = contexts

		for group in lut.itervalues():
			if not certain.issuperset(group):
				print
				for c in certain:
					print c
				print
				for c in group:
					print c


			assert certain.issuperset(group), group

			# Contexts not in the current group
			other = certain-group

			for context in group:
				diff = other-different[context]
				if diff:
					different[context].update(diff)
					self.markDirty(context)

	def createNewCodeNodes(self):
		newfunc = {}

		self.newLive = set()

		# Create the new functions.
		for code, groups in self.groups.iteritems():
			newfunc[code] = {}
			uid = 0
			for group in groups:
				if len(groups) > 1:
					name = "%s_clone_%d" % (code.name, uid)
					uid += 1
				else:
					name = code.name

				newcode =  ast.Code(name, None, None, None, None, None, None, None)
				newcode.annotation = code.annotation

				newfunc[code][id(group)] = newcode
				self.newLive.add(newcode)

		# All live functions accounted for?
		for code in self.liveFunctions:
			assert code in newfunc, code

		return newfunc


	def rewriteProgram(self, extractor, entryPoints):
		newfunc = self.createNewCodeNodes()

		# Clone all of the functions.
		for code, groups in self.groups.iteritems():
			for group in groups:
				newcode = newfunc[code][id(group)]

				fc = FunctionCloner(self.adb, newfunc, self.groupLUT, code, newcode, group)
				fc.process()
				simplify(extractor, self.adb, newcode)


		def getIndirect(code):
			oldContext = self.indirectGroup[code]
			return newfunc[code][self.groupLUT[oldContext]]

		# Entry points are considered to be "indirect"
		# As there is only one indirect function, we know it is the entry point.
		newEP = []
		for func, funcobj, args in entryPoints:
			func = getIndirect(func)
			newEP.append((func, funcobj, args))

		# HACK Mutate the list.
		# Used so everyone gets the update version
		entryPoints[:] = newEP


		# Rewrite the callLUT
		newCallLUT = {}
		for obj, code in extractor.desc.callLUT.iteritems():
			if code in self.indirectGroup:
				newCallLUT[obj] = getIndirect(code)

		extractor.desc.callLUT = newCallLUT

		# Collect and return the new functions.
		funcs = []
		for func, groups in newfunc.iteritems():
			funcs.extend(groups.itervalues())

		return funcs



class FunctionCloner(object):
	__metaclass__ = typedispatcher

	def __init__(self, adb, newfuncLUT, groupLUT, sourcefunction, destfunction, group):
		self.adb            = adb
		self.newfuncLUT     = newfuncLUT
		self.groupLUT       = groupLUT
		self.sourcefunction = sourcefunction
		self.destfunction   = destfunction
		self.group          = group

		# Remap contexts.
		self.contextRemap = []
		for i, context in enumerate(sourcefunction.annotation.contexts):
			if context in group:
				self.contextRemap.append(i)

		destfunction.annotation = sourcefunction.annotation.contextSubset(self.contextRemap)

		# Maintain a reference to the original function.
		# Ugly, as it can prevent quite a bit of GC.
		# TODO "original" UID?
		if sourcefunction.annotation.original is None:
			destfunction.rewriteAnnotation(original=sourcefunction)

		# Transfer information that is tied to the code.
		self.adb.trackContextTransfer(sourcefunction, destfunction, group)


		self.localMap = {}


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

			self.transferAnalysisData(node, result)
		else:
			result = tempresult

		return result

	@dispatch(ast.Code)
	def visitCode(self, node):
		return node

	def translateFunctionContext(self, func, context):
		newfunc = self.newfuncLUT[func][self.groupLUT[context]]
		return context, newfunc

	def transferAnalysisData(self, original, replacement):
		if not isinstance(original, (ast.Expression, ast.Statement)):    return
		if not isinstance(replacement, (ast.Expression, ast.Statement)): return

		assert original is not replacement, original

		def annotationMapper(target):
			code, context = target
			group = self.groupLUT[context]
			newcode = self.newfuncLUT[code][group]
			return newcode, context

		replacement.annotation = original.annotation.contextSubset(self.contextRemap, annotationMapper)


	def transferLocal(self, original, replacement):
		replacement.annotation = original.annotation.contextSubset(self.contextRemap)

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

	liveContexts = programculler.findLiveContexts(adb.db, entryPoints)

	cloner = ProgramCloner(console, adb, liveContexts)

	cloner.unifyContexts()
	cloner.findInitialConflicts()
	cloner.process()
	numGroups = cloner.makeGroups()
	originalNumGroups = len(cloner.liveFunctions)

	console.output("=== Split ===")
	cloner.listGroups()
	console.output("Num groups %d / %d" %  (numGroups, originalNumGroups))
	console.output('')

	console.end()

	# Is cloning worth while?
	if numGroups > originalNumGroups:
		console.begin('rewrite')
		cloner.rewriteProgram(extractor, entryPoints)
		console.end()

		adb.db.liveCode = cloner.newLive