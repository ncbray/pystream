from . import symbolic
from . import algorithim

from oplut import opLUT

import types

from programIR.python.program import Object

class NewConstraintExtractor(object):
	def __init__(self, extractor, rootContext):
		self.extractor = extractor
		self.prgm = symbolic.SymbolicProgram(algorithim.FIAnalyze)
		self.makeDefaultSymbols()

		self.rootContext = rootContext

	def makeInterpreter(self, domainOrder=None):
		self.prgm.link(domainOrder)
		return self.prgm

	def containsSymbol(self, d, s):
		return s in self.prgm.domains[d]

	def addSymbol(self, d, s):
		self.prgm.domains[d].add(s)

	def addTuple(self, r, *values):
		self.prgm.relations[r].add(*values)

	def makeDefaultSymbols(self):
		# HACK functions may have no more than eight parameters
		# TODO precompute
		for i in range(8):
			self.addSymbol('parameter', i)

		### Object field types ###
		# What type of pointers can an object hold?
		self.addSymbol('fieldtype', 'LowLevel')		# System slot
		self.addSymbol('fieldtype', 'Attribute') 	# User slot
		self.addSymbol('fieldtype', 'Array')		# Linear container
		self.addSymbol('fieldtype', 'Dictionary')	# Non-linear container

##		### Object model operations ###
##		for op, name in opLUT.iteritems():
##			self.addSymbol('optype', op)

	def makeBytecode(self, func, node, advance=True):
		self.addSymbol('bytecode', node)
		self.addTuple('containsBytecode', func, node)

		if advance:
			self.addTuple('advanceContext', node)


	def makeVariable(self, func, node):
		self.addSymbol('variable', node)
		self.addTuple('containsVariable', func, node)

	def makeSlot(self, obj):
		name = obj.pyobj
		assert isinstance(name, str), name
		self.makeFieldTuple(obj, 'Attribute', name)
		#return name
		return ('Attribute', obj)


	def makeIndex(self, obj):
		assert isinstance(obj, Object), index
		index = obj.pyobj
		assert isinstance(index, int)
		name = "[%d]" % index
		self.makeFieldTuple(obj, 'Array', name)
		#return name
		return ('Array', obj)



	def makeKey(self, obj):
		assert isinstance(obj, Object), obj
		pyobj = obj.pyobj
		if isinstance(pyobj, str):
			name = repr(pyobj)
		else:
			name = "#%d#" % hash(pyobj)
		self.makeFieldTuple(obj, 'Dictionary', name)
		#return name
		return ('Dictionary', obj)

	def makeLowLevel(self, obj):
		assert isinstance(obj, Object), obj
		pyobj = obj.pyobj
		assert isinstance(pyobj, str), pyobj

		name = "lowlevel#%s" % pyobj
		self.makeFieldTuple(obj, 'LowLevel', name)
		#return name
		return ('LowLevel', obj)

	def makeFieldTuple(self, obj, t, name):
		assert isinstance(obj, Object), obj
		assert isinstance(t, str)
		assert isinstance(name, str)

		
##		# Makes the assumtion that (obj, t) -> name
##		# results in a unique name.
##		if not self.containsSymbol('field', name):
##			self.addSymbol('field', name)
##			self.addTuple('fieldLUT', obj, t, name)
##		# TODO error on redefinition?


	def makeField(self, t, obj):
		if t=='Attribute':
			self.makeSlot(obj)
		elif t=='Array':
			self.makeIndex(obj)
		elif t=='Dictionary':
			self.makeKey(obj)
		elif t=='LowLevel':
			self.makeLowLevel(obj)
		else:
			assert False


	def setArgs(self, b, args):
		# Pass the parameters
		for i, arg in enumerate(args):
			self.addTuple('actualParam', b, i, arg)

		
##	def attachOperator(self, op, obj, f):
##		self.addTuple('operationLUT', op, obj, f)
