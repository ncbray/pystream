from language.python import ast

class IOTree(object):
	def __init__(self, parent, name, lcl, frequency):
		self.parent    = parent
		self.slots     = {}
		self.name      = name
		self.specialName = None
		self.frequency = frequency

		self.local     = ast.Local(self.fullName())
		self.local.annotation = lcl.annotation

	def extend(self, node, lcl, frequency):
		assert isinstance(node.name, ast.Existing)
		name = node.name.object
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
				return name.pyobj.split('#')[0]
			elif attrtype == 'Array':
				return "A"+str(name.pyobj)
			elif attrtype == 'LowLevel':
				return "L"+str(name.pyobj)
			else:
				assert False, (attrtype, name)
		else:
			return str(self.name)

	def fullName(self):
		if self.specialName is not None:
			return self.specialName
		elif self.parent is None:
			return self.partialName()
		else:
			return "%s_%s" % (self.parent.fullName(), self.partialName())

	def match(self, pathMatcher):
		assert isinstance(pathMatcher, dict), pathMatcher

		childMatcher = pathMatcher.get(self.name)
		if childMatcher is None:
			# No match
			return
		elif isinstance(childMatcher, dict):
			# Partial match
			if self.parent is not None:
				return self.parent.match(childMatcher)
		else:
			# Complete match
			return childMatcher

	def setSpecialName(self, name):
		self.specialName = name
		self.local.name  = name


class PythonShader(object):
	def __init__(self, code, pathMatcher):
		self.code     = code

		self.pathToLocal  = {}
		self.localToPath = {}
		self.roots = {}

		self.pathMatcher = pathMatcher

	def bindPath(self, path):
		assert isinstance(path, IOTree)
		self.pathToLocal[path] = path.local
		self.localToPath[path.local]  = path

	def extend(self, path, node, lcl, frequency):
		extendedpath = path.extend(node, lcl, frequency)

		# Check if it's a path that has been bound to a specialized shader I/O
		name = extendedpath.match(self.pathMatcher)
		if name: extendedpath.setSpecialName(name)

		self.bindPath(extendedpath)
		return extendedpath

	def getRoot(self, name, lcl, frequency):
		if name not in self.roots:
			path = IOTree(None, name, lcl, frequency)
			self.bindPath(path)
			self.roots[name] = path
		else:
			path = self.roots[name]
		return path