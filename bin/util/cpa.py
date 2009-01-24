import util.calling
import util.canonical

Any  = util.canonical.Sentinel('<Any>')
Slop = util.canonical.Sentinel('<Slop>')

# A canonical name for a CPA context.
class CPASignature(util.canonical.CanonicalObject):
	__slots__ = 'code', 'path', 'selfparam', 'params', 'vparams'

	def __init__(self, code, path, selfparam, params, vparams):
		if len(params) != len(code.parameters):
			raise TypeError, "Function has %d parameters, %d provided" % (len(code.parameters), len(params))

		params = tuple(params)

		if vparams is not None and vparams is not Slop:
			vparams = tuple(vparams)

		self.code      = code
		self.path      = path
		self.selfparam = selfparam
		self.params    = params
		self.vparams   = vparams

		self.setCanonical(code, path, selfparam, params, vparams)

	def classification(self):
		vparams = self.vparams
		if vparams is not None and vparams is not Slop:
			vparams = len(vparams)
		return (self.code, self.path, len(self.params), vparams)

	def subsumes(self, other):
		if self.classification() == other.classification():
			subsume = False
			for sparam, oparam in zip(self.params, other.params):
				if sparam is Any and oparam is not Any:
					subsume = True
				elif sparam != oparam:
					return False

			if self.vparam is not None and self.vparam is not Slop:
				for sparam, oparam in zip(self.vparams, other.vparams):
					if sparam is Any and oparam is not Any:
						subsume = True
					elif sparam != oparam:
						return False
			return subsume
		else:
			return False

	def vparamSlop(self):
		return self.vparams is Slop

	def __repr__(self):
		return "{0}(code={1}, path={2}, self={3}, params={4}, vparams={5})".format(type(self).__name__, self.code.name, id(self.path), self.selfparam, self.params, self.vparams)

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
