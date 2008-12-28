class DummyAlgorithim(object):
	def domains():
		pass

	def structures():
		pass

	def inputRelations():
		pass

	def internalRelations():
		pass

	def outputRelations():
		pass
	
	def expressions():
		pass

class Algorithim(DummyAlgorithim):
	def domains():
		state()

	def inputRelations():
		transition(('current',state), ('next',state))

	def internalRelations():
		pass

	def outputRelations():
		closure(('current',state), ('next',state))
		backwards(('current',state), ('next',state))

	def expressions():
		closure(s, n) <= transition(s, n)
		closure(s1, s3) <= closure(s1, s2) & closure(s2, s3)

		backwards(s, n) <= transition(n, s)
		backwards(s1, s3) <= backwards(s1, s2) & backwards(s2, s3)


class IsNotStratified(DummyAlgorithim):
	def domains():
		variable()
		heap()
		field()

	def inputRelations():
		varPointInit(('v',variable), ('h',heap))

		load(('dest',variable), ('base',variable), ('f',field))
		store(('base',variable), ('f',field), ('source',variable))
		assign(('dest',variable), ('source',variable))

	def internalRelations():
		pass

	def outputRelations():
		varPoint(('v',variable), ('h',heap))
		heapPoint(('h1',heap), ('f',field), ('h2',heap))


	def expressions():
		varPoint(v, h) <= varPointInit(v, h)
		varPoint(v1, h) <= assign(v1, v2)&varPoint(v2, h)
		heapPoint(h1, f, h2) <= store(v1, f, v2) & varPoint(v1, h1) & varPoint(v2, h2)
		varPoint(v1, h2) <= load(v1, v2, f) & varPoint(v2, h1) & ~heapPoint(h1, f, h2)


class FloatDomain(DummyAlgorithim):
	def domains():
		state()

class NegativeDomain(DummyAlgorithim):
	def domains():
		state()

class SymbolRedef(DummyAlgorithim):
	def domains():
		state()
		state()

class UnknownDomain(DummyAlgorithim):
	def domains():
		dummy()
		
	def inputRelations():
		transition(('current',state), ('next',state))

class BadExpression(DummyAlgorithim):
	def domains():
		state()

	def inputRelations():
		transition(('current',state), ('next',state))

	def internalRelations():
		pass

	def outputRelations():
		closure(('current',state), ('next',state))
		backwards(('current',state), ('next',state))
		
	def expressions():
		closure(s, n) <= fnord(s, n)

class BadType(DummyAlgorithim):
	def domains():
		state()
		foo()

	def inputRelations():
		b(('current',state), ('next',foo))

	def internalRelations():
		pass

	def outputRelations():
		a(('current',state), ('next',state))
		

	def expressions():
		a(s, n) <= b(s, n)

class BadSize(DummyAlgorithim):
	def domains():
		state()

	def inputRelations():
		b(('current',state))

	def internalRelations():
		pass

	def outputRelations():
		a(('current',state), ('next',state))

	def expressions():
		a(s, n) <= b(s, n)

class NameReuse(DummyAlgorithim):
	def domains():
		state()
		foo()

	def inputRelations():
		ts(('current',state), ('next',state))
		tf(('current',foo), ('next',foo))

	def internalRelations():
		pass

	def outputRelations():
		cs(('current',state), ('next',state))
		cf(('current',foo), ('next',foo))

	def expressions():
		cs(s1, s2) <= ts(s1, s2)
		cs(s1, s3) <= cs(s1, s2) & cs(s2, s3)

		cf(s1, s2) <= tf(s1, s2)
		cf(s1, s3) <= cf(s1, s2) & cf(s2, s3)

		

class PointsTo(DummyAlgorithim):
	def domains():
		variable()
		heap()
		field()

	def inputRelations():
		varPointInit(('v',variable), ('h',heap))

		load(('dest',variable), ('base',variable), ('f',field))
		store(('base',variable), ('f',field), ('source',variable))
		assign(('dest',variable), ('source',variable))

	def internalRelations():
		pass

	def outputRelations():
		varPoint(('v',variable), ('h',heap))
		heapPoint(('h1',heap), ('f',field), ('h2',heap))


	def expressions():
		varPoint(v, h) <= varPointInit(v, h)
		varPoint(v1, h) <= assign(v1, v2)&varPoint(v2, h)
		heapPoint(h1, f, h2) <= store(v1, f, v2) & varPoint(v1, h1) & varPoint(v2, h2)
		varPoint(v1, h2) <= load(v1, v2, f) & varPoint(v2, h1) & heapPoint(h1, f, h2)

class DeadCode(DummyAlgorithim):
	def domains():
		variable()
		heap()
		bytecode()
		field()

	def inputRelations():
		varPointInit(('v',variable), ('h',heap))

		load(('dest',variable), ('base',variable), ('f',field))
		store(('base',variable), ('f',field), ('source',variable))
		assign(('dest',variable), ('source',variable))

		dummy(('b', bytecode))

	def internalRelations():
		dummy2(('b', bytecode))

	def outputRelations():
		varPoint(('v',variable), ('h',heap))
		heapPoint(('h1',heap), ('f',field), ('h2',heap))


	def expressions():
		varPoint(v, h) <= varPointInit(v, h)
		varPoint(v1, h) <= assign(v1, v2)&varPoint(v2, h)
		heapPoint(h1, f, h2) <= store(v1, f, v2) & varPoint(v1, h1) & varPoint(v2, h2)
		varPoint(v1, h2) <= load(v1, v2, f) & varPoint(v2, h1) & heapPoint(h1, f, h2)


		dummy2(b) <= dummy(b)

class Temporary(DummyAlgorithim):
	def domains():
		variable()
		heap()
		field()

	def inputRelations():
		varPointInit(('v',variable), ('h',heap))

		load(('dest',variable), ('base',variable), ('f',field))
		store(('base',variable), ('f',field), ('source',variable))
		assign(('dest',variable), ('source',variable))

	def internalRelations():
		temp(('v', variable), ('f', field), ('h', heap))

	def outputRelations():
		varPoint(('v',variable), ('h',heap))
		heapPoint(('h1',heap), ('f',field), ('h2',heap))


	def expressions():
		varPoint(v, h) <= varPointInit(v, h)
		varPoint(v1, h) <= assign(v1, v2)&varPoint(v2, h)
		heapPoint(h1, f, h2) <= store(v1, f, v2) & varPoint(v1, h1) & varPoint(v2, h2)
		temp(v, f, h1) <= varPoint(v, h2) & heapPoint(h2, f, h1)
		varPoint(v1, h2) <= load(v1, v2, f) & temp(v2, f, h2)
