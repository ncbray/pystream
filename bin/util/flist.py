class FList(object):
	__slots__ = 'left', 'right'
	def __init__(self, left, right):
		self.left = left
		self.right = right

	def __iter__(self):
		stack = []
		current  = self

		while isinstance(current, FList):
			while isinstance(current.left, FList):
				stack.append(current)
				current = current.left

			yield current.left
			current = current.right

			while not isinstance(current, FList):
				yield current

				if stack:
					current = stack.pop().right
				else:
					return

	def __repr__(self):
		return "FList%s" % repr(tuple(iter(self)))

#print FList(FList(1, FList(2, 10)), FList(3, 4))
