import weakref

dontTrack = (str, int, long, float, type(None), list, tuple, dict)

class AbstractAnalysisDatabase(object):
	# Single, non-contextual local reference
	# Returns object
	def singleObject(self, function, local):
		values = self.objectsForLocal(function, local)

		if len(values) == 1:
			obj = tuple(values)[0].xtype.obj
			if obj.isPreexisting():
				return obj
		return None

	# Single, non-contextual invocation edge
	# Returns function
	def singleCall(self, function, b):
		funcs = self.invocationsForOp(function, b)
		assert isinstance(funcs, (tuple, list, set, frozenset)), repr(funcs)
		if len(funcs) == 1:
			func = tuple(funcs)[0]
			return func

		return None

	def invocationsForContextOp(self, function, op, context):
		return self._invocationsForContextOp(function, op, context)

	def hasSideEffects(self, function, op):
		result = bool(self.modificationsForOp(function, op))
		return result


class DummyAnalysisDatabase(AbstractAnalysisDatabase):
	def objectsForLocal(self, function, local):
		return ()

	def invocationsForOp(self, function, op):
		return ()

	def hasSideEffects(self, function, op):
		return True

	def trackRewrite(self, function, original, newast):
		pass
