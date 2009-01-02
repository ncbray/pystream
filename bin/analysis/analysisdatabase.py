import weakref

dontTrack = (str, int, long, float, type(None), list, tuple, dict)

class AbstractAnalysisDatabase(object):
	def __init__(self):
		self.opTracking = weakref.WeakKeyDictionary()

	def trackRewrite(self, function, original, newast):
		if isinstance(original, dontTrack):
			return

		if isinstance(newast, dontTrack):
			return

		if original is not newast:
			origin = self.origin(function, original)
			self.opTracking[newast] = origin

	def origin(self, function, op):
		return self.opTracking.get(op, op)

	
	# Single, non-contextual local reference
	# Returns object
	def singleObject(self, function, local):
		values = self.objectsForLocal(function, self.origin(function, local))

		if len(values) == 1:
			obj = tuple(values)[0].obj
			if obj.isPreexisting():
				return obj
		return None

	# Single, non-contextual invocation edge
	# Returns function
	def singleCall(self, function, b):
		funcs = self.invocationsForOp(function, self.origin(function, b))
		
		if len(funcs) == 1:
			func = tuple(funcs)[0]
			return func
		
		return None


	def invocationsForContextOp(self, function, op, context):
		return self._invocationsForContextOp(function, self.origin(function, op), context)

	def hasSideEffects(self, function, op):
		return bool(self.modificationsForOp(function, self.origin(function, op)))


class DummyAnalysisDatabase(AbstractAnalysisDatabase):
	def objectsForLocal(self, function, local):
		return ()

	def invocationsForOp(self, function, op):
		return ()

	def hasSideEffects(self, function, op):
		return True


