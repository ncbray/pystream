import antlr3
from . origin import Origin

def childText(node, index):
	return str(node.getChild(index).getText())

def name(index):
	def name_func(func):
		def name_wrapper(self, node):
			if self.isNone(node.getChild(index)):
				name = self.positionName()
			else:
				name = self.getName(node.getChild(index))

			result = func(self, node, name)
			self.attachOrigin(node, result) # Attach the origin before popping.
			self.pop()
			return result
		return name_wrapper
	return name_func


def fixedname(name):
	def name_func(func):
		def name_wrapper(self, node):
			self.push(name)
			result = func(self, node)
			self.attachOrigin(node, result) # Attach the origin before popping.
			self.pop()
			return result
		return name_wrapper
	return name_func

class ASTTranslator(object):
	def __init__(self, compiler, parser, filename):
		self.compiler = compiler
		self.parser   = parser
		self.filename = filename

		self.namestack = []
		self.name = None

		self.indexstack = []
		self.index = 0

		self.origincache = {}

		self.generateOutput = True

		self.dispatch = {}

	def generate(self, nodeType, *args):
		if self.generateOutput:
			return nodeType(*args)
		else:
			return None

	def default(self, node):
		assert False, "Unsupported AST node: %s" % self.nodeName(node)

	# Override to change how origin is wrapped in the annotation
	def originAnnotation(self, origin):
		return origin

	def makeOrigin(self, node):
		origin = Origin(self.fullName(), self.filename, node.getLine(), node.getCharPositionInLine())
		origin = self.origincache.setdefault(origin, origin)
		return self.originAnnotation(origin)

	def exceptionOrigin(self, e):
		origin = Origin(self.fullName(), self.filename, e.line, e.charPositionInLine)
		origin = self.origincache.setdefault(origin, origin)
		return origin

	def attachOrigin(self, node, result):
		if hasattr(result, 'annotation') and hasattr(result.annotation, 'origin'):
			if result.annotation.origin is result.__emptyAnnotation__.origin:
				result.rewriteAnnotation(origin=self.makeOrigin(node))

	def nodeName(self, node):
		return self.parser.typeName(node.getType())

	def getMethod(self, typeID):
		return getattr(self, 'visit_'+self.parser.typeName(typeID), self.default)

	def __call__(self, node):
		if isinstance(node, antlr3.tree.CommonErrorNode):
			self.generateOutput = False
			return None

		typeID = node.getType()
		m = self.dispatch.get(typeID)
		if m is None:
			m = getattr(self, 'visit_'+self.parser.typeName(typeID), self.default)
			self.dispatch[typeID] = m

		result = m(node)
		self.attachOrigin(node, result)
		return result

	def visitChildren(self, node, *indices):
		if len(indices) == 1:
			return self(node.getChild(indices[0]))
		else:
			return [self(node.getChild(index)) for index in indices]

	def fullName(self):
		return self.name

	def getName(self, node):
		name = str(node.getText())
		self.push(name)
		return name

	def positionName(self):
		name = self.index
		self.index += 1
		self.push(str(name))
		return name

	def push(self, name):
		self.namestack.append(self.name)
		if self.name is None:
			self.name = name
		else:
			self.name = ".".join([self.name, name])

		self.indexstack.append(self.index)
		self.index = 0

	def pop(self):
		self.name  = self.namestack.pop()
		self.index = self.indexstack.pop()
