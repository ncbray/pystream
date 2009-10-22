class ArgumentWrapper(object):
	pass

# Thin wrappers made to work with decompiler.programextractor
class InstanceWrapper(ArgumentWrapper):
	def __init__(self, typeobj):
		self.typeobj = typeobj

	def getObject(self, extractor):
		return extractor.getInstance(self.typeobj)

	def get(self, dataflow):
		return dataflow.getInstanceSlot(self.typeobj)

class ExistingWrapper(ArgumentWrapper):
	def __init__(self, pyobj):
		self.pyobj = pyobj

	def getObject(self, extractor):
		return extractor.getObject(self.pyobj)

	def get(self, dataflow):
		return dataflow.getExistingSlot(self.pyobj)

class ReturnWrapper(ArgumentWrapper):
	def __init__(self, ep):
		self.ep = ep

	def get(self, dataflow):
		return dataflow.getReturnSlot(self.ep)

# Used when an argument, such as varg or karg, is not present.
class NullWrapper(ArgumentWrapper):
	def get(self, dataflow):
		return None

	def __nonzero__(self):
		return False

nullWrapper = NullWrapper()
