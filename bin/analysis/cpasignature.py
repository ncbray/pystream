import util.canonical

Any  = util.canonical.Sentinel('<Any>')

class DoNotCareType(object):
	def isDoNotCare(self):
		return True
	def __repr__(self):
		return '<DoNotCare>'

DoNotCare = DoNotCareType()

# A canonical name for a CPAed parameter list.
class CPASignature(util.canonical.CanonicalObject):
	__slots__ = 'code', 'selfparam', 'params'

	def __init__(self, code, selfparam, params):
		params = tuple(params)

		# HACK - Sanity check.  Used for catching infinite loops in the analysis
		assert len(params) < 30, code

		self.code      = code
		self.selfparam = selfparam
		self.params    = params

		self.setCanonical(code, selfparam, params)

	def classification(self):
		return (self.code, self.numParams())

	# Is this signature more general than another signature?
	# Megamorphic and slop arguments are marked as "Any" which is
	# more general than a spesific type.
	def subsumes(self, other):
		if self.classification() == other.classification():
			subsume = False
			for sparam, oparam in zip(self.params, other.params):
				if sparam is Any and oparam is not Any:
					subsume = True
				elif sparam != oparam:
					return False
			return subsume
		else:
			return False

	def numParams(self):
		return len(self.params)

	def __repr__(self):
		return "%s(code=%s, self=%r, params=%r)" % (type(self).__name__, self.code.codeName(), self.selfparam, self.params)
