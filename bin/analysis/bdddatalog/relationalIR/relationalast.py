from __future__ import absolute_import

class RelationalOp(object):
	__slots__ = ()

class Rename(RelationalOp):
	def __init__(self, target, source, lut):
		self.target = target
		self.source = source
		self.lut = lut

	def __str__(self):
		return '%s = rename(%s, %s)' % (self.target, self.source, repr(self.lut))

	def translate(self, t, m):
		target = t.get(self.target, self.target)
		source = t.get(self.source, self.source)


		lut = {}
		for k, v in self.lut.iteritems():
			a = m[k]
			b = m[v]
			if not a == b:
				lut[a] = b
		return Rename(target, source, lut)


class Join(RelationalOp):
	def __init__(self, target, left, right):
		self.target = target
		self.left = left
		self.right = right

	def __str__(self):
		return '%s = join(%s, %s)' % (self.target, self.left, self.right)


	def translate(self, t, m):
		target = t.get(self.target, self.target)
		left = t.get(self.left, self.left)
		right = t.get(self.right, self.right)
		return Join(target, left, right)

class Project(RelationalOp):
	def __init__(self, target, source, fields):
		for field in fields:
			assert isinstance(field, int), field
		
		self.target = target
		self.source = source
		self.fields = frozenset(fields)

	def __str__(self):
		return '%s = project(%s, %s)' % (self.target, self.source, repr(tuple(self.fields)))

	def translate(self, t, m):
		target = t.get(self.target, self.target)
		source = t.get(self.source, self.source)
		fields = tuple([m[f] for f in self.fields])
		
		return Project(target, source, fields)


class RelProd(RelationalOp):
	def __init__(self, target, left, right, fields):
		for field in fields:
			assert isinstance(field, int), field
		
		self.target 	= target
		self.left 	= left
		self.right 	= right
		self.fields 	= frozenset(fields)

	def __str__(self):
		return '%s = relprod(%s, %s, %s)' % (self.target, self.left, self.right, repr(tuple(self.fields)))

	def translate(self, t, m):
		target = t.get(self.target, self.target)
		left = t.get(self.left, self.left)
		right = t.get(self.right, self.right)
		fields = tuple([m[f] for f in self.fields])
		return RelProd(target, left, right, fields)

class Union(RelationalOp):
	def __init__(self, target, left, right):
		self.target = target
		self.left = left
		self.right = right

	def __str__(self):
		return '%s = union(%s, %s)' % (self.target, self.left, self.right)

	def translate(self, t, m):
		target = t.get(self.target, self.target)
		left = t.get(self.left, self.left)
		right = t.get(self.right, self.right)
		return Union(target, left, right)

class Load(RelationalOp):
	def __init__(self, target, name):
		self.target 	= target
		self.name 	= name

	def __str__(self):
		return '%s = load(%s)' % (self.target, repr(self.name))

	def translate(self, t, m):
		return Load(t.get(self.target, self.target), self.name)

class Store(RelationalOp):
	def __init__(self, target, name):
		self.target 	= target
		self.name 	= name

	def __str__(self):
		return 'store(%s, %s)' % (self.target, repr(self.name))

	def translate(self, t, m):
		return Store(t.get(self.target, self.target), self.name)

class Invert(RelationalOp):
	def __init__(self, target, expr):
		self.target = target
		self.expr = expr

	def __str__(self):
		return '%s = invert(%s)' % (self.target, self.expr)

	def translate(self, t, m):
		newT = t.get(self.target, self.target)
		newE = t.get(self.expr, self.expr)
		return Invert(newT, newE)


class InstructionBlock(RelationalOp):
	def __init__(self):
		self.instructions = []
		self.read = set()
		self.modify = set()

	def addInstruction(self, op):
		if isinstance(op, (Loop, Expression)):
			# Don't add an empty loop.
			if op.block.instructions:
				self.read.update(op.read)
				self.modify.update(op.modify)			
				self.instructions.append(op)
		else:
			self.instructions.append(op)

class Loop(RelationalOp):
	def __init__(self, block):
		self.block = block
		self.read = block.read
		self.modify = block.modify

class Expression(RelationalOp):
	def __init__(self, block, read, modify, datalog):
		self.block = block
		self.read = read
		self.modify = modify
		self.datalog = datalog

class Program(RelationalOp):
	def __init__(self, domains, structures, relations, nameDomains, relationNames, body):
		self.domains = domains
		self.structures = structures
		self.relations = relations
		self.nameDomains = nameDomains
		self.relationNames = relationNames
		self.body = body



# Difference?
# Select?
# Universe?
# Boolean Operation? < <= > >=, etc.
