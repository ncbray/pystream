from language.python import ast

class IOTree(object):
	def __init__(self, parent, name, lcl, frequency):
		self.parent    = parent
		self.slots     = {}
		self.name      = name
		self.local     = ast.Local(self.fullName())
		self.local.annotation = lcl.annotation
		self.frequency = frequency

	def extend(self, node, lcl, frequency):
		assert isinstance(node.name, ast.Existing)
		name = node.name.object.pyobj
		return self.getSlot((node.fieldtype, name), lcl, frequency)

	def getSlot(self, name, lcl, frequency):
		if name not in self.slots:
			slot = IOTree(self, name, lcl, frequency)
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
		self.localToPath = {}
		self.roots = {}

	def bindPath(self, path):
		assert isinstance(path, IOTree)
		self.pathToLocal[path] = path.local
		self.localToPath[path.local]  = path

	def extend(self, path, node, lcl, frequency):
		newpath = path.extend(node, lcl, frequency)
		self.bindPath(newpath)
		return newpath

	def getRoot(self, name, lcl, frequency):
		if name not in self.roots:
			path = IOTree(None, name, lcl, frequency)
			self.bindPath(path)
			self.roots[name] = path
		else:
			path = self.roots[name]
		return path