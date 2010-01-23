from . import constraints, calls
from language.python import ast, program

class Invocation(object):
	def __init__(self, src, op, dst):
		self.src = src
		self.op  = op
		self.dst = dst

		self.dst.invokeIn[(src, op)] = self
		self.src.invokeOut[(op, dst)] = self

	def copyDown(self, obj):
		return self.dst.analysis.object(obj.name, constraints.DN)

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


		self.locals = {}
		self.fields = {}

		self.vparamTemp = []


		self.invokeIn  = {}
		self.invokeOut = {}

	def getInvoke(self, op, dst):
		key = op, dst
		inv = self.invokeOut.get(key)
		if inv is None:
			inv = Invocation(self, op, dst)
		return inv

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
		slot.updateSingleValue(self.analysis.pyObj(numVParam))

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

	def call(self, op, selfarg, args, kwds, varg, karg, targets):
		call = calls.CallConstraint(self, op, selfarg, args, kwds, varg, karg, targets)
		self.calls.append(call)

	def dcall(self, op, code, selfarg, args, kwds, varg, karg, targets):
		if varg is None:
			return self.fcall(op, code, selfarg, args, kwds, [], karg, targets)
		else:
			call = calls.DirectCallConstraint(self, op, code, selfarg, args, kwds, varg, karg, targets)
			self.dcalls.append(call)
			return call

	def fcall(self, op, code, selfarg, args, kwds, varg, karg, targets):
		call = calls.FlatCallConstraint(self, op, code, selfarg, args, kwds, varg, karg, targets)
		self.fcalls.append(call)
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

	def initDownwardField(self, slot):
		print "DN", slot

	def field(self, obj, fieldType, name):
		assert isinstance(obj, constraints.AnalysisObject), obj
		assert isinstance(fieldType, str), fieldType
		assert isinstance(name, program.AbstractObject), name

		key = (obj, fieldType, name)


		if key not in self.fields:
			slot = constraints.ConstraintNode(self, key)
			self.fields[key] = slot

			if obj.qualifier is constraints.DN:
				self.initDownwardField(slot)
			# TODO global

		else:
			slot = self.fields[key]
		return slot

	def assign(self, src, dst):
		assert isinstance(src, constraints.ConstraintNode), src
		assert isinstance(dst, constraints.ConstraintNode), dst

		constraint = constraints.CopyConstraint(src, dst)
		self.constraint(constraint)

	def down(self, invoke, src, dst):
		assert isinstance(src, constraints.ConstraintNode), src
		assert isinstance(dst, constraints.ConstraintNode), dst

		constraint = constraints.DownwardConstraint(invoke, src, dst)
		self.constraint(constraint)

	def updateCallgraph(self):
		changed = bool(self.dirtycalls or self.dirtydcalls or self.dirtyfcalls)

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

		return changed

	def dump(self):

		print "="*80
		print "SIGNATURE"
		print self.signature
		print

		print "IN"
		for invoke in self.invokeIn.itervalues():
			print invoke.src.signature
			print invoke.op
			print
		print

		print "OUT"
		for invoke in self.invokeOut.itervalues():
			print invoke.op
			print invoke.dst.signature
			print
		print

		print "LOCALS"
		for slot in self.locals.itervalues():
			print slot
			for value in slot.values:
				print '\t', value
			print
		print

		print "FIELDS"
		for slot in self.fields.itervalues():
			print slot
			for value in slot.values:
				print '\t', value
			print
		print
