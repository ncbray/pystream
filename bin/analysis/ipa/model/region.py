from . object import Object

class Region(object):
	__slots__ = 'context', 'objects'

	def __init__(self, context):
		self.context = context
		self.objects = {}

	def object(self, obj):
		if obj not in self.objects:
			result = Object(self.context, obj)
			self.objects[obj] = result
		else:
			result = self.objects[obj]

		return result
