from . import constraints, calls
from language.python import ast, program

class Context(object):
	def __init__(self, analysis, signature):
		self.analysis    = analysis
		self.signature   = signature
		self.constraints = []

		self.calls       = []
		self.dcalls      = []
		self.fcalls      = []

		self.dirtycalls       = []
		self.dirtydcalls      = []
		self.dirtyfcalls      = []


		self.locals      = {}

		self.vparamTemp = []


	def setup(self):
		# Is this a real context?
		code = self.signature.code
		if code:
			params = code.codeParameters()
			if params.vparam is not None:
				self.setupVParam(params.vparam)

	def dirtySlot(self, slot):
		self.analysis.dirtySlot(slot)

	def dirtyCall(self, call):
		self.dirtycalls.append(call)

	def dirtyDCall(self, call):
		self.dirtydcalls.append(call)

	def dirtyFCall(self, call):
		self.dirtyfcalls.append(call)

	def vparamObj(self):
		inst = self.analysis.tupleInstance()
		xtype = self.analysis.canonical.contextType(self.signature, inst, None)
		return self.analysis.object(xtype, constraints.HZ)

	def setupVParam(self, vparam):
		# Assign the vparam object to the vparam local
		vparamObj = self.vparamObj()
		self.local(vparam, (vparamObj,))

		numVParam = len(self.signature.vparams)

		# Set the length of the vparam object
		slot = self.field(vparamObj, 'LowLevel', self.analysis.pyObj('length').name.obj)
		slot.updateValues(frozenset([self.analysis.pyObj(numVParam)]))

		# Copy the vparam locals into the vparam fields
		for i in range(numVParam):
			# Create a temporary local
			lcl = self.local(ast.Local('vparam%d'%i))
			self.vparamTemp.append(lcl)

			# Create a vparam field
			index = self.analysis.pyObj(i)
			slot = self.field(vparamObj, 'Array', index.name.obj)

			# Copy
			self.assign(lcl, slot)


	def constraint(self, constraint):
		self.constraints.append(constraint)
		self.analysis._constraint(self, constraint)

	def call(self, selfarg, args, kwds, varg, karg, targets):
		call = calls.CallConstraint(self, selfarg, args, kwds, varg, karg, targets)
		self.calls.append(call)
		self.analysis.dirtyCalls = True

	def dcall(self, code, selfarg, args, kwds, varg, karg, targets):
		if varg is None:
			return self.fcall(code, selfarg, args, kwds, 0, karg, targets)
		else:
			call = calls.DirectCallConstraint(self, code, selfarg, args, kwds, varg, karg, targets)
			self.dcalls.append(call)
			self.analysis.dirtyCalls = True
			return call

	def fcall(self, code, selfarg, args, kwds, varg, karg, targets):
		call = calls.FlatCallConstraint(self, code, selfarg, args, kwds, varg, karg, targets)
		self.fcalls.append(call)
		self.analysis.dirtyCalls = True
		return call


	def local(self, node, values=None):
		if node not in self.locals:
			cnode = constraints.ConstraintNode(self, node, values)
			self.locals[node] = cnode
		else:
			cnode = self.locals[node]

			# TODO remove this?
			if values is not None:
				cnode.updateValues(values)
		return cnode

	def field(self, obj, fieldType, name):
		assert isinstance(obj, constraints.AnalysisObject), obj
		assert isinstance(fieldType, str), fieldType
		assert isinstance(name, program.AbstractObject), name

		canonical = (obj, fieldType, name)
		return self.local(canonical) # HACK?

	def assign(self, src, dst, qualifier=constraints.HZ):
		assert isinstance(src, constraints.ConstraintNode), src
		assert isinstance(dst, constraints.ConstraintNode), dst

		constraint = constraints.CopyConstraint(src, dst)
		constraint.qualifier = qualifier
		self.constraint(constraint)

	def assignFiltered(self, src, typeFilter, dst, qualifier=constraints.HZ):
		assert isinstance(src, constraints.ConstraintNode), src
		assert isinstance(dst, constraints.ConstraintNode), dst

		constraint = constraints.FilteredCopyConstraint(src, typeFilter, dst)
		constraint.qualifier = qualifier
		self.constraint(constraint)

	def updateCallgraph(self):
		while self.dirtycalls:
			call = self.dirtycalls.pop()
			#print call
			call.resolve(self)

		while self.dirtydcalls:
			call = self.dirtydcalls.pop()
			#print call
			call.resolve(self)

		while self.dirtyfcalls:
			call = self.dirtyfcalls.pop()
			#print call
			call.resolve(self)


	def dump(self):

		print self.signature
		print

		for lc in self.locals.itervalues():
			print lc
			for value in lc.values:
				print '\t', value
			print
		print
