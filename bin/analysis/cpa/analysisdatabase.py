from analysis.analysisdatabase import AbstractAnalysisDatabase
from analysis.astcollector import getOps
import programIR.python.ast as ast

dontTrack = (str, int, long, float, type(None), list, tuple, dict)

class CPAAnalysisDatabase(AbstractAnalysisDatabase):
	def __init__(self, db):
		AbstractAnalysisDatabase.__init__(self)
		self.db = db

	# Returns a set of contextual objects
	def objectsForLocal(self, function, local):
		return self.db.functionInfo(function).localInfo(local).merged.references

	# Returns a set of non-contextual functions
	def invocationsForOp(self, function, op):
		opinfo = self.db.functionInfo(function).opInfo(op).merged
		return set([func for context, func in opinfo.invokes])

	# Returns a set of contexts.
	# TODO Should return a set of context functions?
	def _invocationsForContextOp(self, function, op, context):
		opinfo = self.db.functionInfo(function).opInfo(op).context(context)
		return set([context for context, func in opinfo.invokes])


	# Returns a set of contextual objects
	def modificationsForOp(self, function, op):
		if hasattr(self.db, 'lifetime'):
			# HACK
			result = self.db.lifetime.modifyDB[function][op].forget()
			return result
		else:
			return ()

	def liveFunctions(self):
		return set(self.db.functionInfos.keys())

	def functionContexts(self, function):
		return self.db.functionInfo(function).contexts

	# Make standard?
	def functionOps(self, func):
		ops, lcls = getOps(func)
		return ops

	def functionLocals(self, func):
		ops, lcls = getOps(func)
		return lcls

	# TODO Tracking shouldn't be in base class?
	def trackRewrite(self, function, original, newast):
		if original is newast or isinstance(original, dontTrack) or isinstance(newast, dontTrack):
			return

		finfo = self.db.functionInfo(function)
		finfo.trackRewrite(original, newast)

		if hasattr(self.db, 'lifetime'):
			if isinstance(original, (ast.Expression, ast.Statement)):
				if isinstance(newast, (ast.Expression, ast.Statement)):
					readDB = self.db.lifetime.readDB
					readDB[function].merge(newast, readDB[function][original])

					modifyDB = self.db.lifetime.modifyDB
					modifyDB[function].merge(newast, modifyDB[function][original])


	def origin(self, function, op):
		return op

