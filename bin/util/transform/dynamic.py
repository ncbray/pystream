from base import *

class DynamicTransformer(Transformer):
	pass


class UndefinedRule(object):
	pass
undefined = UndefinedRule()

##class RuleNotPresent(object):
##	pass
##notpresent = RuleNotPresent()

# TODO changesets?
class DynamicRuleScope(object):
	def __init__(self, parent, d=None):
		self.parent 	= parent

		if d is not None:
			self.setShared(d)
		else:
			self.rules 	= {}
			self.shared     = False

		#self.labels 	= set()

	def setShared(self, d):
		self.rules  = d
		self.shared = True

	# O(1) or O(n')?
	def define(self, rule, result):
		if self.shared:
			# Copy on write
			self.rules = dict(self.rules)
			self.shared = False
		self.rules[rule] = result

	# O(1)
	def undefine(self, rule):
		self.define(rule, undefined)

	# Look through the scopes
	# O(s)
	def lookup(self, rule):
		if rule in self.rules:
			return self.rules[rule]
		elif self.parent is not None:
			return self.parent.lookup(rule)
		else:
			return undefined

##	def label(self, label):
##		self.labels.add(label)
##
##	def defineLabeled(self, label, rule, result):
##		if label in self.labels:
##			self.define(rule, result)
##		elif self.parent:
##			self.parent.defineLabeled(label, rule)
##			self.define(rule, result) # HACK?
####			if rule in self.rules:
####				del self.rules[rule]
##		else:
##			assert False, "Attemped to define a non-existant label %s." % repr(label)
##
##	def undefineLabeled(self, label, rule):
##		self.defineLabeled(label, rule, undefined)

	# O(s)
	def copy(self):
		parent = self.parent.copy() if self.parent else None
		self.shared = True
		return DynamicRuleScope(parent, self.rules)

	# O(n) worst case
	def intersect(self, other):
		if id(self.rules) == id(other.rules):
			# If they're exactly the same, don't bother intersecting or unsharing.
			assert self.shared and other.shared
		else:
			newrules = {}
			modified = set(self.rules.iterkeys())
			modified.update(other.rules.iterkeys())

			for rule in modified:
				# Note we use "lookup" incase the rule is not defined in the local scope.
				# The allows better precision that simply undefining the rule.
				a = self.lookup(rule)
				b = other.lookup(rule)
				newrules[rule] = a if a == b else undefined
				
			self.rules  = newrules
			self.shared = False

		if self.parent: self.parent.intersect(other.parent)		


class DynamicRule(DynamicTransformer):
	def __init__(self):
		self.stack = []
		self.tos = DynamicRuleScope(None)

	def __call__(self, node, env):
		result = self.lookup(node)

		if result == undefined:
			return doFail()
		else:
			return result

	def lookup(self, rule):
		return self.tos.lookup(rule)

	def define(self, rule, result):
		self.tos.define(rule, result)

	def undefine(self, rule):
		self.tos.undefine(rule)
		
	def enterScope(self):
		self.stack.append(self.tos)
		self.tos = DynamicRuleScope(self.tos)

	def exitScope(self):
		self.tos = self.stack.pop()

	def copy(self):
		return self.tos.copy()

	def restore(self, other):
		self.tos = other.copy() # HACK

	def intersect(self, other):
		self.tos.intersect(other)

	def children(self):
		return ()

class DynDefine(Transformer):
	__metaclass__ = astnode
	__fields__    = 'rule'
	__types__     = {'rule':DynamicTransformer}

	def __call__(self, node, env):
		assert isinstance(node, tuple) and len(node) == 2, node
		self.rule.define(node[0], node[1])
		return self.rule
		
class DynUndefine(Transformer):
	__metaclass__ = astnode
	__fields__    = 'rule'
	__types__     = {'rule':DynamicTransformer}

	def __call__(self, node, env):
		self.rule.undefine(node)
		return self.rule


class DynScope(Transformer):
	__metaclass__ = astnode
	__fields__    = 'rule', 's'
	__types__     = {'rule':DynamicTransformer, 's':Transformer}
	
	def __call__(self, node, env):
		self.rule.enterScope()
		try:
			return self.s(node, env)
		finally:
			self.rule.exitScope()

class DynCopy(Transformer):
	__metaclass__ = astnode
	__fields__    = 'rule'
	__types__     = {'rule':DynamicTransformer}

	def __call__(self, node, env):
		return self.rule.copy()

class DynRestore(Transformer):
	__metaclass__ = astnode
	__fields__    = 'rule'
	__types__     = {'rule':DynamicTransformer}
	
	def __call__(self, node, env):
		self.rule.restore(node)
		return self.rule

class DynIntersect(Transformer):
	__metaclass__ = astnode
	__fields__    = 'rule'
	__types__     = {'rule':DynamicTransformer}
	
	def __call__(self, node, env):
		self.rule.intersect(node)
		return self.rule
