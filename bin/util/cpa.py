import util.calling
import util.canonical

Any  = util.canonical.Sentinel('<Any>')

# A canonical name for a CPAed parameter list.
class CPASignature(util.canonical.CanonicalObject):
	__slots__ = 'code', 'selfparam', 'params'

	def __init__(self, code, selfparam, params):
		params = tuple(params)

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
		return "{0}(code={1}, self={2}, params={3})".format(type(self).__name__, self.code.name, self.selfparam, self.params)

# Abstract base class
class CPAInfoProvider(object):
	# In the worst case, expr may be a user object with multiple
	# possible __call__ attibutes.  This is not likely, as classes should
	# be immutable, but there's no point in not futureproofing...
	def functions(self, expr):
		raise NotImplementedError

	def objects(self, node):
		raise NotImplementedError

	def vargLengths(self, obj):
		raise NotImplementedError

	def vargValues(self, obj, length):
		raise NotImplementedError

	def cpaType(self, obj):
		raise NotImplementedError


class CPAIterator(object):
	def iterExprFunc(self, node):
		exprs = self.objects(node)
		for expr in exprs:
			functions = self.functions(expr)
			for func in functions:
				yield exprs, func

	def iterVArgAndValues(self, node):
		if node is None:
			yield None, False
		else:
			vargs = self.objects(node)
			for varg in vargs:
				lengths = self.vargLengths(varg)
				for length in lengths:
					yield self.vargValues(varg, length), length < 0

	def marshalArgs(self, args, varg, length):
		# TODO transfer...
		linear = [self.objects(callee.arg) for arg in args]

		slop = None

		if length < 0:
			pass #???
		else:
			for i in range(length):
				linear.append(self.vargValues(varg, i))

		return linear,

	def call(self, *args):
		assert not case.kargs

#		for expr, func in info.iterExprFunc(case.expr):
#			for varg, length in info.iterVArgLength(case.vargs):
#			# copy?
#			functions = info.functions(expr)
#			for func in functions:
