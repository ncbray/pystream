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
		refs = local.annotation.references
		if refs is not None:
			return refs[0]
		else:
			return ()

	# Returns a set of non-contextual functions
	def invocationsForOp(self, function, op):
		#assert op.annotation.invokes is not None, op

		if op.annotation.invokes is not None:
			return set([func for func, context in op.annotation.invokes[0]])
		else:
			return None

	# Returns a set of contexts.
	# TODO Should return a set of context functions?
	def _invocationsForContextOp(self, code, op, context):
		cindex  = code.annotation.contexts.index(context)
		invokes = op.annotation.invokes

		if invokes is not None:
			return set([context for func, context in invokes[1][cindex]])
		else:
			return set()

	# Returns a set of contextual objects
	def modificationsForOp(self, function, op):
		if hasattr(self.db, 'lifetime'):
			# HACK
			result = self.db.lifetime.modifyDB[function][op].forget()
			return result
		else:
			return ()

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

		#Annotation transfer
		newast.annotation = original.annotation

		# Lifetime info transfer
		if hasattr(self.db, 'lifetime'):
			if isinstance(original, (ast.Expression, ast.Statement)):
				if isinstance(newast, (ast.Expression, ast.Statement)):
					readDB = self.db.lifetime.readDB
					readDB[function].merge(newast, readDB[function][original])

					modifyDB = self.db.lifetime.modifyDB
					modifyDB[function].merge(newast, modifyDB[function][original])

	def trackContextTransfer(self, srcFunc, dstFunc, contexts):
		if hasattr(self.db, 'lifetime'):
			live = self.db.lifetime.live
			killed = self.db.lifetime.contextKilled

			for context in contexts:
				data = live.get((srcFunc, context))
				if data: live[(dstFunc, context)] = data

				data = killed.get((srcFunc, context))
				if data: killed[(dstFunc, context)] = data


	def trackOpTransfer(self, srcFunc, srcOp, dstFunc, dstOp, contexts, invokeMap=None):
		assert isinstance(srcOp, (ast.Expression, ast.Statement)), srcOp
		assert isinstance(dstOp, (ast.Expression, ast.Statement)), dstOp

		# Lifetime info transfer
		if hasattr(self.db, 'lifetime'):
			readDB = self.db.lifetime.readDB
			srcInfo = readDB[srcFunc][srcOp]
			dstInfo = readDB[dstFunc][dstOp]
			for context in contexts:
				dstInfo.merge(context, srcInfo[context])

			modifyDB = self.db.lifetime.modifyDB
			srcInfo = modifyDB[srcFunc][srcOp]
			dstInfo = modifyDB[dstFunc][dstOp]
			for context in contexts:
				dstInfo.merge(context, srcInfo[context])

	def origin(self, function, op):
		return op

