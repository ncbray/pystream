class Bracket(object):
	def __init__(self, data):
		self.data = data
		self.prev = None
		self.next = None

	def delete(self):
		assert not self.isOrphaned()


		self.prev.next = self.next
		self.next.prev = self.prev

		self.prev = None
		self.next = None

	def insertAfter(self, other):
		assert other.isOrphaned()

		other.prev = self
		other.next = self.next

		self.next.prev = other
		self.next = other


	def isOrphaned(self):
		return self.prev == None and self.next == None

	def __repr__(self):
		return "Bracket(%r)" % self.data

class BracketList(object):
	def __init__(self):
		self.root = Bracket(None)
		self.root.next = self.root
		self.root.prev = self.root
		self.__size = 0

	def size(self):
		return self.__size

	def push(self, bracket):
		self.root.insertAfter(bracket)
		self.__size += 1

	def top(self):
		return self.root.next

	def delete(self, bracket):
		bracket.delete()
		self.__size -= 1

	def forwards(self):
		current = self.root.next
		while current != self.root:
			yield current
			current = current.next

	def backwards(self):
		current = self.root.prev
		while current != self.root:
			yield current
			current = current.prev

	def concat(self, other):
		# Join the lists
		self.root.prev.next = other.root.next
		other.root.next.prev = self.root.prev

		# Connect the end of the new list too the root.
		self.root.prev = other.root.prev
		other.root.prev.next = self.root

		self.__size += other.__size

		# Reset the other root.
		other.root.next = other.root
		other.root.prev = other.root
		other.__size = 0
