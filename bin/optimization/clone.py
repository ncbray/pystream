# Split contexts unless types match
# Add type-switched disbatch where cloning does not work?

# Whole program optimization

import collections

from PADS.UnionFind import UnionFind

from util.typedispatch import *

from programIR.python import ast

from simplify import simplify

# Figures out what functions should have seperate implementations,
# to improve optimization / realizability
class ProgramCloner(object):
	def __init__(self, adb):
		self.adb = adb

		# func -> context -> context set
		self.different = collections.defaultdict(lambda: collections.defaultdict(set))

		# HACK, ensure the keys exist
		for func in adb.liveFunctions():
			different = self.different[func]
			for context in adb.functionContexts(func):
				different[context]




	def makeGroups(self):
		# Create groups of contexts
		self.groups = {}
		for func in self.adb.liveFunctions():
			groups = self.makeFuncGroups(func)

			if len(groups) > 1:
				print func.name, len(groups), "groups"

			self.groups[func] = groups

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

	def makeFuncGroups(self, func):
		groups = []

		different = self.different[func]

		for context in self.adb.functionContexts(func):
			assert context.signature.function is func, (context, func)
			for group in groups:
				assert context in different
				if not different[context].intersection(group):
					group.add(context)
					break
			else:
				groups.append(set((context,)))
		return groups

	def findConflicts(self):
		self.realizable = True
		for func in self.adb.liveFunctions():
			# Two contexts should not be the same if they contain an op that
			# invokes different sets of functions.
			for op in self.adb.functionOps(func):

				# Cache the contexts, as we'll need them later.
				contexts = frozenset(self.adb.functionContexts(func))

				lut = collections.defaultdict(set)
				label = {}
				u = UnionFind()

				# Find the different call patterns.
				# Using union find on the invocation edges
				# helps avoid a problem where the edges in one context
				# May be a subset of another context.
				for context in contexts:
					assert context.signature.function is func, (context, func)

					invocations = self.adb.invocationsForContextOp(func, op, context)
					translated = [self.groupLUT[dst] for dst in invocations]

					label[context] = translated[0] if translated else None
					translated = frozenset(translated)
					if len(translated) >= 2:
						u.union(*translated)

						print "Conflict"
						print func.name
						print type(op)
						for inv in invocations:
							print '\t*', self.groupLUT[inv], inv
						print

						# More that one call target.
						self.realizable = False

				for context in contexts:
					group = u[label[context]]
					lut[group].add(context)

				# Mark contexts with different call patterns as different.
				different = self.different[func]
				for group in lut.itervalues():
					assert contexts.issuperset(group), (func.name, [c.func.name for c in group])

					# Contexts not in the current group
					diff = contexts-group

					for context in group:
						different[context].update(diff)



	def rewriteProgram(self, extractor, entryPoints):
		newfunc = {}

		# Create the new functions.
		for func, groups in self.groups.iteritems():
			newfunc[func] = {}
			uid = 0
			for group in groups:
				if len(groups) > 1:
					name = "%s_clone_%d" % (func.name, uid)
				else:
					name = func.name

				newfunc[func][id(group)] = ast.Function(name, None)
				uid += 1

		# Clone all of the functions.
		for func, groups in self.groups.iteritems():
			for group in groups:
				f = newfunc[func][id(group)]

				# Transfer information that is tied to the context.
				self.adb.trackContextTransfer(func, f, group)

				fc = FunctionCloner(self.adb, newfunc, self.groupLUT, func, f, group)
				f.code = fc(func.code)


		# HACK Horrible, horrible hack: assumes that the entry point cannot be cloned.
		# This will be the case for most situations we're interested in... but still.  Ugly.
		newEP = []
		for func, funcobj, args in entryPoints:
			groups = newfunc[func]
			assert len(groups) == 1
			clonefunc = groups.items()[0][1]
			newEP.append((clonefunc, funcobj, args))


		# HACK Mutate the list.
		# Used so everyone gets the update version
		entryPoints[:] = newEP

		# Collect and return the new functions.
		funcs = []
		for func, groups in newfunc.iteritems():
			funcs.extend(groups.itervalues())

		for func in funcs:
			simplify(extractor, self.adb, func)

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


	@dispatch(ast.Local)
	def visitLocal(self, node):
		return self.translateLocal(node)


	@defaultdispatch
	def default(self, node):
		result = allChildren(self, node)
		self.transferAnalysisData(node, result)
		return result

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

def clone(extractor, entryPoints, adb):
	cloner = ProgramCloner(adb)
	print "=== Default ==="
	cloner.makeGroups() # Create default groups.
	print

	oldNumGroups = 0
	numGroups = len(adb.liveFunctions())

	while numGroups > oldNumGroups:
		oldNumGroups = numGroups

		cloner.findConflicts()

		print "=== Split ==="
		print cloner.realizable
		numGroups = cloner.makeGroups()
		print


		print "Num groups", numGroups, '/', oldNumGroups, '/', len(adb.liveFunctions())

	# Is cloning worth while?
	if numGroups > len(adb.liveFunctions()):
		cloner.rewriteProgram(extractor, entryPoints)

