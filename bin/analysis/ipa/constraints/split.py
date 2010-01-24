from language.python import ast
from . base import Constraint
from .. calling import cpa

class Splitter(Constraint):
	def addSplitCallback(self, callback):
		self.callbacks.append(callback)
		if self.objects: callback()

	def attach(self):
		self.src.addCallback(self.srcChanged)

	def makeConsistent(self):
		# Make constraint consistent
		if self.src.values:
			self.srcChanged(self.src.values)

	def doNotify(self):
		for callback in self.callbacks:
			callback()

class TypeSplitConstraint(Splitter):
	def __init__(self, context, src):
		assert src.isNode(), src
		self.context = context
		self.src = src
		self.objects = {}

		self.callbacks = []

		self.megamorphic = False

		self.attach()
		self.makeConsistent()

	def types(self):
		return self.objects.keys()

	def makeTempLocal(self):
		return self.context.local(ast.Local('type_split_temp'))

	def makeMegamorphic(self):
		assert not self.megamorphic
		self.megamorphic = True
		self.objects.clear()
		self.objects[cpa.anyType] = self.src
		self.doNotify()

	def srcChanged(self, diff):
		if self.megamorphic: return

		changed = False
		for obj in diff:
			cpaType = obj.cpaType()

			if cpaType not in self.objects:
				if len(self.objects) >= 4:
					self.makeMegamorphic()
					break
				else:
					temp = self.makeTempLocal()
					self.objects[cpaType] = temp
					changed = True
			else:
				temp = self.objects[cpaType]

			temp.updateSingleValue(obj)
		else:
			if changed: self.doNotify()




class ExactSplitConstraint(Splitter):
	def __init__(self, context, src):
		assert src.isNode(), src
		self.context = context
		self.src = src
		self.objects = {}
		self.callbacks = []

		self.attach()
		self.makeConsistent()

	def makeTempLocal(self):
		return self.context.local(ast.Local('exact_split_temp'))

	def srcChanged(self, diff):
		changed = False
		for obj in diff:
			if obj not in self.objects:
				temp = self.makeTempLocal()
				self.objects[obj] = temp
				changed = True
			else:
				temp = self.objects[obj]

			temp.updateSingleValue(obj)

		if changed: self.doNotify()
