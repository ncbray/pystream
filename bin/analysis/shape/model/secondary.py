##def mergeIntersect(a, b):
##	if a is None or b is None:
##		result = None
##	else:
##		result = a.intersection(b)
##		if not result: result = None
##	return result

class SecondaryInformation(object):
	__slots__ = 'hits', 'misses'
	def __init__(self, hits, misses):
		assert hits is None or isinstance(hits, set), hits
		assert misses is None or isinstance(misses, set), misses

		if not hits:   hits = None
		if not misses: misses = None

		self.hits   = hits
		self.misses = misses

	def merge(self, other):
		if other is None: return self, False	

		changed = False

		hits = self.hits
		if hits:
			if other.hits:
				prelen = len(hits)

				hits.intersection_update(other.hits)
				
				if len(hits) != prelen:
					changed = True
				
				if not hits:
					self.hits = None
			else:
				self.hits = None
				changed = True
			
		misses = self.misses
		if misses:
			if other.misses:
				prelen = len(misses)

				misses.intersection_update(other.misses)
				
				if len(misses) != prelen:
					changed = True
				
				if not misses:
					self.misses = None
			else:
				self.misses = None
				changed = True
		return changed

	def __repr__(self):
		return "secondary(hits=%r, misses=%r)" % (self.hits, self.misses)

	def copy(self):
		hits = self.hits
		if hits: hits = set(hits)

		misses = self.misses
		if misses: misses = set(misses)

		return SecondaryInformation(hits, misses)


emptyInformation = SecondaryInformation(None, None)
