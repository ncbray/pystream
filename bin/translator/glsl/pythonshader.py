from language.python import ast

class IOTree(object):
	def __init__(self, parent, name):
		self.parent = parent
		self.slots  = {}
		self.name   = name
		self.local  = None

	def extend(self, node):
		assert isinstance(node.name, ast.Existing)
		name = node.name.object.pyobj
		return self.getSlot((node.fieldtype, name))

	def getSlot(self, name):
		if name not in self.slots:
			slot = IOTree(self, name)
			self.slots[name] = slot
		else:
			slot = self.slots[name]
		return slot

	def partialName(self):
		if isinstance(self.name, ast.Local):
			return self.name.name
		elif isinstance(self.name, tuple):
			attrtype, name = self.name
			if attrtype == 'Attribute':
				return name.split('#')[0]
			elif attrtype == 'Array':
				return "A"+str(name)
			elif attrtype == 'LowLevel':
				return "L"+str(name)
			else:
				assert False, (attrtype, name)
		else:
			return str(self.name)

	def fullName(self):
		if self.parent is None:
			return self.name
		else:
			return "%s_%s" % (self.parent.fullName(), self.partialName())


class PythonShader(object):
	def __init__(self, code):
		self.code     = code

		self.pathToLocal  = {}
		self.frequency = {}
		self.roots = {}

	def bindPath(self, path, lcl):
		assert isinstance(path, IOTree)
		self.pathToLocal[path] = lcl
		path.local = lcl

	def getRoot(self, name, slot):
		if name not in self.roots:
			lcl = ast.Local(name)
			lcl.annotation = slot.annotation

			path = IOTree(None, name)
			self.bindPath(path, lcl)
			self.roots[name] = path
		else:
			path = self.roots[name]

		return path