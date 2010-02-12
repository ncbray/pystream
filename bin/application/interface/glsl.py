import argwrapper
import language.python.shaderprogram

class PathDeclaration(object):
	__slots__ = 'parent'

	def attrslot(self, obj, name):
		child = AttrDeclaration(obj, name)
		child.parent = self
		return child

	def arrayslot(self, index):
		child = ArrayDeclaration(index)
		child.parent = self
		return child

	def extract(self, extractor):
		part = (self._extractPart(extractor),)

		if(self.parent):
			return self.parent.extract(extractor) + part
		else:
			return part


class AttrDeclaration(PathDeclaration):
	__slots__ = 'obj', 'name'

	def __init__(self, obj, name):
		assert isinstance(obj, argwrapper.ArgumentWrapper), obj
		assert isinstance(name, str), name

		self.parent = None
		self.obj = obj
		self.name = name

	def _extractPart(self, extractor):
		obj = self.obj.getObject(extractor)
		return extractor.getObjectAttr(obj, self.name)

class ArrayDeclaration(PathDeclaration):
	__slots__ = 'index'

	def __init__(self, index):
		assert isinstance(index, int), index

		self.parent = None
		self.index = index

	def _extractPart(self, extractor):
		return ('Array', extractor.getObject(self.index))

# A extension to the makefile for spesifying glsl-spesific things.
class GLSLDeclaration(object):
	def __init__(self):
		self.attr = []
		self._shader = []

	def input(self, path, name):
		self._attr(path, name, True, False)

	def output(self, path, name):
		self._attr(path, name, False, True)

	def inout(self, path, name):
		self._attr(path, name, True, True)

	def shader(self, shadercls, *args):
		assert isinstance(shadercls, type)
		self._shader.append((argwrapper.InstanceWrapper(shadercls), args))

	# Declares that the specified path through the heap should be replaced
	# with a special variable named "name".
	def _attr(self, path, name, input, output):
		assert isinstance(path, PathDeclaration), path
		assert isinstance(name, str), name
		self.attr.append((path, name, input, output))

	def _extract(self, extractor, interface):
		attr = []

		for path, name, input, output in self.attr:
			newpath = path.extract(extractor)
			attr.append((newpath, name, input, output))

		self.attr = attr


		for shader, args in self._shader:
			name = shader.typeobj.__name__

			vsobj, vscode = interface.getMethCode(shader, 'shadeVertex', extractor)
			fsobj, fscode = interface.getMethCode(shader, 'shadeFragment', extractor)

			if False:
				interface.createEntryPoint(vscode, vsobj, (shader,)+args)
				interface.createEntryPoint(fscode, fsobj, (shader,)+args)
			else:
				shaderargs = (vsobj, fsobj, shader,)+args
				interface.createEntryPoint(language.python.shaderprogram.createShaderProgram(extractor, name), None, shaderargs)

	def __nonzero__(self):
		return bool(self._shader)
