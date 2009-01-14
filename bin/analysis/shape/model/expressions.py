MustAlias = 'MustAlias'
MayAlias  = 'MayAlias'
NoAlias   = 'NoAlias'

Unknown = 'Unknown'


class Expression(object):
	__slots__ = 'slot'

	def __init__(self):
		pass

	def __repr__(self):
		return "expr(%s)" % self.path()

	def isExpression(self):
		return True

	def isSlot(self):
		return False

	def isNull(self):
		return False

	def isExtendedParameter(self):
		return False

	def isTrivial(self):
		return len(self) <= 1

	def _pathAlias(self, paths):
		mustHit, mustMiss = paths.classifyHitMiss(self)

		# A known hit
		if mustHit: return MustAlias

		# A known miss
		if mustMiss: return NoAlias

		# No idea if it matches...
		return MayAlias

	def makeExtendedParameter(self, sys, parameters):
		if self.hasParameterRoot(parameters):
			return sys.canonical.extendedParameter(self)
		else:
			return None

##	def split(self):
##		return None, self.slot
##
##	def __iter__(self):
##		return iter(self.split())

class NullExpr(Expression):
	__slots__ = ()

	def __init__(self):
		self.slot = None # HACK?  Should there be a null slot?

	def stableLocation(self, sys, slot, stableValues):
		return True

	def stableValue(self, sys, slot, stableValues):
		return True

	def substitute(self, sys, eOld, eNew, unstableSlot=None, first=True):
		return self

	def path(self):
		return 'null'

	def refersTo(self, sys, index, paths):
		return NoAlias

	def isNull(self):
		return True

	def __len__(self):
		return 0

	def hasParameterRoot(self, parameters):
		return False
	
null = NullExpr()

class LocalExpr(Expression):
	__slots__ = ()
	def __init__(self, slot):
		assert slot.isSlot(), slot		
		assert slot.isLocal(), slot
		self.slot = slot

	def stableLocation(self, sys, slot, stableValues):
		return True

	def stableValue(self, sys, slot, stableValues):
		if self.slot == slot and (stableValues is None or self not in stableValues):
			return False
		else:
			return True


	# Assumes eNew is a stableLocation.
	def substitute(self, sys, eOld, eNew, unstableSlot=None, first=True):
		if self == eOld:
			return eNew
		else:
			return None

	def path(self):
		return str(self.slot)

	def refersTo(self, sys, index, paths):
		if index.referedToBySlot(self.slot):
			return MustAlias
		else:
			return NoAlias

	def __len__(self):
		return 1

	def hasParameterRoot(self, parameters):
		return self in parameters


class FieldExpr(Expression):
	__slots__ = 'parent', '_length'
	def __init__(self, parent, slot):
		assert parent.isExpression(), parent
		assert slot.isSlot(), slot
		assert slot.isHeap(), slot
		
		self.parent  = parent
		self.slot    = slot
		self._length = len(self.parent)+1
		
	def stableLocation(self, sys, slot, stableValues):
		#assert slot.isSlot(), slot
		return self.parent.stableValue(sys, slot, stableValues)

	def stableValue(self, sys, slot, stableValues):
		if self.slot == slot and (stableValues is None or self not in stableValues):
			return False
		else:
			return self.parent.stableValue(sys, slot, stableValues)

	def substitute(self, sys, eOld, eNew):
		if self == eOld:
			return eNew
		else:
			exprNew = self.parent.substitute(sys, eOld, eNew)
			if exprNew:
				return sys.canonical.fieldExpr(exprNew, self.slot)
			else:
				return None

	# Assumes eNew is a stableLocation.
	def substitute(self, sys, eOld, eNew, unstableSlot=None, first=True):
		if self == eOld:
			return eNew
		else:
			if first or self.slot != unstableSlot:
				exprNew = self.parent.substitute(sys, eOld, eNew, unstableSlot, False)
				if exprNew:
					return sys.canonical.fieldExpr(exprNew, self.slot)
		return None



	def path(self):
		return "%s.%s" % (self.parent.path(), str(self.slot))


	def refersTo(self, sys, index, paths):
		# TODO can we make this more precise?

		# Check reference points to this index
		if not index.referedToBySlot(self.slot):
			return NoAlias

		return self._pathAlias(paths)
		
##	def split(self):
##		return self.parent, self.slot


	def __len__(self):
		return self._length

	def hasParameterRoot(self, parameters):
		return self.parent.hasParameterRoot(parameters)

class ExtendedParameter(Expression):
	__slots__ = 'expr'
	def __init__(self, expr):
		assert expr.isExpression()
		self.expr = expr
		self.slot = expr.slot # HACK

	def stableLocation(self, sys, slot, stableValues):
		return True

	def stableValue(self, sys, slot, stableValues):
		if self.slot == slot and (stableValues is None or self not in stableValues):
			return False
		else:
			return True


	# Assumes eNew is a stableLocation.
	def substitute(self, sys, eOld, eNew, unstableSlot=None, first=True):
		if self == eOld:
			return eNew
		else:
			return None
		
	def path(self):
		return "ext(%s)" % self.expr.path()

	def refersTo(self, sys, index, paths):
		return self._pathAlias(paths)

	def __len__(self):
		return 1

	def hasParameterRoot(self, parameters):
		return False
