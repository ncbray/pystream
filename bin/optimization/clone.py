# Split contexts unless types match
# Add type-switched disbatch where cloning does not work?

# Whole program optimization

import collections
from PADS.UnionFind import UnionFind
from util.typedispatch import *
from util.traversal import replaceAllChildren
from language.python import ast
import optimization.simplify
from analysis import programculler
from analysis import tools

class GroupUnifier(object):
	def __init__(self):
		self.unify         = UnionFind()
		self.unifyGroups   = {}
		self.dirty         = set()

	def init(self, context):
		self.unify[context]
		self.unifyGroups[context] = set((context,))
		self.dirty.add(context)

	def unifyContexts(self, contexts):
		for context in contexts:
			assert self.unify[context] is context, (context, self.unify[context])

		# Unify the contexts
		result = self.unify.union(*contexts)

		group = self.unifyGroups[result]

		for context in contexts:
			if context is result: continue

			group.update(self.unifyGroups[context])
			del self.unifyGroups[context]

			# The context may be unified, so make sure it doesn't hang arround.
			if context in self.dirty: self.dirty.remove(context)

		# Mark the context for processing.
		self.dirty.add(result)

		return result

	def iterGroups(self):
		return self.unifyGroups.iterkeys()

	def canonical(self, context):
		return self.unify[context]

	def group(self, context):
		return self.unifyGroups[context]

# Figures out what functions should have seperate implementations,
# to improve optimization / realizability
class ProgramCloner(object):
	def __init__(self, liveContexts):
		self.liveFunctions = set(liveContexts.iterkeys())
		self.liveContexts  = liveContexts


		self.liveOps = {}
		for code in self.liveFunctions:
			self.liveOps[code] = tools.codeOps(code)


		# func -> context -> context set
		self.different = collections.defaultdict(lambda: collections.defaultdict(set))

		# HACK, ensure the keys exist
		for func in self.liveFunctions:
			different = self.different[func]
			for context in self.liveContexts[func]:
				different[context]


		self.unifier = GroupUnifier()
		self.indirectGroup = {}

	def doUnify(self, code, contexts, indirect):
		# indirect indicates the contexts can be called from an object.
		# All indirect contexts must be unified, as only one function
		# can be called indirectly.
		if indirect and code in self.indirectGroup:
			contexts.add(self.indirectGroup[code])

		if len(contexts) > 1:
			indirectGroup =  self.indirectGroup.get(code)

			for context in contexts:
				if context is indirectGroup: indirect = True

			result = self.unifier.unifyContexts(contexts)

			if indirect: self.indirectGroup[code] = result
		elif indirect:
			self.indirectGroup[code] = contexts.pop()

	def unifyContexts(self, interface):
		# Calculates the fully cloned, realizable solution.
		# This is used as an upper bound for cloning.
		# This will never generate more functions than there are contexts.
		# It is undesirable to use it directly, as it gets crazy large
		# when path sensitivity is used.
		# TODO what happens if we can insert type switches?

		# All of the contexts are dirty
		for code, contexts in self.liveContexts.iteritems():
			for context in contexts:
				self.unifier.init(context)


		# Merge entry points that must have the same implementation.
		for entryPoint, contexts in interface.groupedEntryContexts().iteritems():
			self.doUnify(entryPoint.code, set(contexts), False)


		while self.unifier.dirty:
			current = self.unifier.dirty.pop()

			code    = current.signature.code
			group   = self.unifier.group(current)

			for op in self.liveOps[code]:
				dsts = collections.defaultdict(set)
				for context in group:
					invocations = tools.opInvokesContexts(code, op, context)
					for dst in invocations:
						udst = self.unifier.canonical(dst)
						assert self.unifier.canonical(udst) is udst
						dsts[udst.signature.code].add(udst)

				# Unify the destination contexts.
				# If there's more than one code target, this is an indirect call.
				indirect = len(dsts) > 1
				for dstcode, dstcontexts in dsts.iteritems():
					self.doUnify(dstcode, dstcontexts, indirect)

		self.codeGroups = {}
		self.groupsInvokeGroup = {}

		self.groupOpInvokes = {}

		for gid in self.unifier.iterGroups():
			code = gid.signature.code
			if code not in self.codeGroups:
				self.codeGroups[code] = set()
			self.codeGroups[code].add(gid)
			self.groupsInvokeGroup[gid] = set()

		for code, groups in self.codeGroups.iteritems():
			for op in self.liveOps[code]:
				for group in groups:
					ginv = set()
					for context in self.unifier.group(group):
						invocations = tools.opInvokesContexts(code, op, context)
						for inv in invocations:
							dst = self.unifier.canonical(inv)
							self.groupsInvokeGroup[dst].add(group)
							ginv.add(dst)
					self.groupOpInvokes[(group, op)] = ginv




	def listGroups(self, console):
		for func, groups in self.groups.iteritems():
			if len(groups) > 1:
				console.output("%s %d groups" % (func.name, len(groups)))

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
		doPack = True
		different = self.different[code]

		# Pack the groups
		for group in self.codeGroups[code]:
			if doPack:
				for packed in pack:
					if not different[group].intersection(packed):
						packed.add(group)
						break
				else:
					pack.append(set((group,)))
			else:
				pack.append(set((group,)))


		# Expand the packed groups
		groups = []
		for packed in pack:
			unpacked = set()
			for group in packed:
				unpacked.update(self.unifier.group(group))
			groups.append(unpacked)

		return groups

	def slotNames(self, slots):
		return [slot.slotName for slot in slots]

	def labelLoad(self, code, op, group):
		reads = op.annotation.reads

		if reads is None or not reads[0]:
			label = None
		else:
			contexts = self.unifier.group(group)

			slots = set()
			for context in contexts:
				cindex = code.annotation.contexts.index(context)
				slots.update(self.slotNames(reads[1][cindex]))

			if slots:
				label = frozenset(slots)
			else:
				label = False

		return label



	def labelStore(self, code, op, group):
		modifies = op.annotation.modifies

		if modifies is None or not modifies[0]:
			label = None
		else:
			contexts = self.unifier.group(group)

			slots = set()
			for context in contexts:
				cindex = code.annotation.contexts.index(context)
				slots.update(self.slotNames(modifies[1][cindex]))

			if slots:
				label = frozenset(slots)
			else:
				label = False
		return label



	def labelAllocate(self, code, op, group):
		contexts = self.unifier.group(group)

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
			return False

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
		self.dirty = set()
		assert not self.dirty

		# Clone loads from different fields
		for code, groups in self.codeGroups.iteritems():
			for op in self.liveOps[code]:
				# Only split loads for reading different fields
				if isinstance(op, (ast.Load, ast.Check)):
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
				newcode = code.clone()

				# If there's more that one group, make sure they're named differently.
				if len(groups) > 1:
					name = "%s_clone_%d" % (code.name, uid)
					uid += 1
					newcode.setCodeName(name)

				newfunc[code][id(group)] = newcode
				self.newLive.add(newcode)

		# All live functions accounted for?
		for code in self.liveFunctions:
			assert code in newfunc, code

		return newfunc


	def getIndirect(self, code, newfunc):
		oldContext = self.indirectGroup[code]
		return newfunc[code][self.groupLUT[oldContext]]

	def retargetEntryPoint(self, ep, newfunc):
		if ep.contexts:
			group = self.groupLUT[ep.contexts[0]]
			newcode = newfunc[ep.code][group]
		else:
			# HACK what should be done if analysis fails?
			newcode = ep.code

		ep.code = newcode

	def rewriteProgram(self, compiler):
		newfunc = self.createNewCodeNodes()

		# Clone all of the functions.
		for code, groups in self.groups.iteritems():
			for group in groups:
				newcode = newfunc[code][id(group)]

				fc = FunctionCloner(newfunc, self.groupLUT, newcode, group)
				fc.process()
				optimization.simplify.evaluateCode(compiler, newcode)

		# Entry points are considered to be "indirect"
		# As there is only one indirect function, we know it is the entry point.
		for entryPoint in compiler.interface.entryPoint:
			self.retargetEntryPoint(entryPoint, newfunc)

		# Rewrite the callLUT
		newCallLUT = {}
		for obj, code in compiler.extractor.desc.callLUT.iteritems():
			if code in self.indirectGroup:
				newCallLUT[obj] = self.getIndirect(code, newfunc)

		compiler.extractor.desc.callLUT = newCallLUT

		# Collect and return the new functions.
		funcs = []
		for func, groups in newfunc.iteritems():
			funcs.extend(groups.itervalues())
		return funcs



class FunctionCloner(TypeDispatcher):
	def __init__(self, newfuncLUT, groupLUT, code, group):
		self.newfuncLUT     = newfuncLUT
		self.groupLUT       = groupLUT
		self.code           = code
		self.group          = group

		# Remap contexts.
		self.contextRemap = []
		for i, context in enumerate(code.annotation.contexts):
			if context in group:
				self.contextRemap.append(i)

		code.annotation = code.annotation.contextSubset(self.contextRemap)

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
		result = ast.Existing(node.object)
		self.transferLocal(node, result)
		return result

	@dispatch(ast.DirectCall)
	def visitDirectCall(self, node):
		tempresult = self.default(node)

		invokes = tempresult.annotation.invokes
		assert invokes is not None, "All invocations must be resolved to clone."

		if invokes[0]:
			# We do this computation after transfer, as it can reduce the number of invocations.
			func = tools.singleCall(tempresult)
			if not func:
				names = tuple(set([code.name for code, context in invokes[0]]))
				raise Exception, "Cannot clone the direct call in %r, as it has multiple targets. %r" % (self.code, names)
		else:
			# HACK never actualy executed, so null the target?
			# This op should be subseqently eliminated.
			func = None

		result = ast.DirectCall(func, *tempresult.children()[1:])
		self.transferAnalysisData(node, result)

		return result

	@dispatch(ast.Code)
	def visitCode(self, node):
		return node

	def translateFunctionContext(self, func, context):
		newfunc = self.newfuncLUT[func][self.groupLUT[context]]
		return context, newfunc

	def annotationMapper(self, target):
		code, context = target
		group = self.groupLUT[context]
		newcode = self.newfuncLUT[code][group]
		return newcode, context

	def transferAnalysisData(self, original, replacement):
		if not isinstance(original, (ast.Expression, ast.Statement)):    return
		if not isinstance(replacement, (ast.Expression, ast.Statement)): return

		assert original is not replacement, original

		replacement.annotation = original.annotation.contextSubset(self.contextRemap, self.annotationMapper)


	def transferLocal(self, original, replacement):
		replacement.annotation = original.annotation.contextSubset(self.contextRemap)

	def process(self):
		replaceAllChildren(self, self.code)

def evaluate(compiler):
	with compiler.console.scope('clone'):
		with compiler.console.scope('analysis'):

			liveContexts = programculler.findLiveContexts(compiler.interface)

			cloner = ProgramCloner(liveContexts)

			cloner.unifyContexts(compiler.interface)
			cloner.findInitialConflicts()
			cloner.process()
			numGroups = cloner.makeGroups()
			originalNumGroups = len(cloner.liveFunctions)

			compiler.console.output("=== Split ===")
			cloner.listGroups(compiler.console)
			compiler.console.output("Num groups %d / %d" %  (numGroups, originalNumGroups))
			compiler.console.output('')

		liveCode = cloner.liveFunctions

		# Is cloning worthwhile?
		if numGroups > originalNumGroups:
			with compiler.console.scope('rewrite'):
				cloner.rewriteProgram(compiler)
				liveCode = cloner.newLive

		compiler.liveCode = liveCode