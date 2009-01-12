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

	def isTrivial(self):
		return True

null = NullExpr()

class LocalExpr(Expression):
	__slots__ = ()
	def __init__(self, slot):
		assert slot.isSlot(), slot		
		assert slot.isLocal(), slot
		self.slot = slot

	def stableLocation(self, sys, slot, stableValues):
		#assert slot.isSlot(), slot
		return True

	def stableValue(self, sys, slot, stableValues):
		#assert slot.isSlot(), slot		

		# TODO self will never be in stable values, as it would be trivial?
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

	def isTrivial(self):
		return True

class FieldExpr(Expression):
	__slots__ = 'parent'
	def __init__(self, parent, slot):
		assert parent.isExpression(), parent
		assert slot.isSlot(), slot
		assert slot.isHeap(), slot
		
		self.parent = parent
		self.slot  = slot

		
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

		mustHit, mustMiss = paths.classifyHitMiss(self)

		# A known hit
		if mustHit: return MustAlias

		# A known miss
		if mustMiss: return NoAlias

		# No idea if it matches...
		return MayAlias

	def isTrivial(self):
		return False
