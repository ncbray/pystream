class ClassDecl(object):
	def __init__(self, t):
		self.type_ = t
		self.slots = {}
		self.methods = {}
		self.getters = set()

	def slot(self, name, types):
		if not isinstance(types, (tuple, list)):
			types = (types,)

		if name not in self.slots:
			self.slots[name] = list(types)
		else:
			self.slots[name].extend(types)

	def method(self, name, *args):
		if name not in self.methods:
			self.methods[name] = [args]
		else:
			self.methods[name].append(args)

	def getter(self, name):
		self.getters.add(name)


class ShaderDecl(ClassDecl):
	def vertex(self, *types):
		self.vertexIn = types

classes = {}

def class_(t):
	assert t not in classes, t
	cls = ClassDecl(t)
	classes[t] = cls
	return cls

def shader(t):
	assert t not in classes, t
	cls = ShaderDecl(t)
	classes[t] = cls
	return cls
