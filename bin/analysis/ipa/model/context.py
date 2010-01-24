from . import invocation, region, objectname
from .. constraints import flow, calls, qualifiers, node

class Context(object):
	def __init__(self, analysis, signature):
		self.analysis    = analysis
		self.signature   = signature

		self.vparamField = []

		self.region = region.Region(self)
		self.locals = {}
		self.fields = {}

		self.constraints = []

		self.calls       = []
		self.dcalls      = []
		self.fcalls      = []

		self.dirtycalls       = []
		self.dirtydcalls      = []
		self.dirtyfcalls      = []

		self.invokeIn  = {}
		self.invokeOut = {}

		self.external = False

	def existingPyObj(self, pyobj, qualifier=qualifiers.HZ):
		obj = self.analysis.pyObj(pyobj)
		xtype = self.analysis.canonical.existingType(obj)
		return self.analysis.objectName(xtype, qualifier)

	def allocatePyObj(self, pyobj):
		ao  = self.existingPyObj(pyobj, qualifiers.HZ)

		# TODO do we need to set the type pointer?
		tao = self.existingPyObj(type(pyobj), qualifiers.HZ) # Yes, it is not global
		self.setTypePointer(ao, tao)

		return ao

	def setTypePointer(self, obj, typeObj):
		assert isinstance(obj, objectname.ObjectName), obj
		assert isinstance(typeObj, objectname.ObjectName), typeObj

		typeptr = self.field(obj, 'LowLevel', self.analysis.pyObj('type'))
		typeptr.clearNull()
		typeptr.updateSingleValue(typeObj)

	def allocate(self, typeObj, node):
		assert isinstance(typeObj, objectname.ObjectName), typeObj

		inst = typeObj.xtype.obj.typeinfo.abstractInstance
		xtype = self.analysis.canonical.pathType(None, inst, node)
		obj = self.analysis.objectName(xtype, qualifiers.HZ)

		self.setTypePointer(obj, typeObj)

		return obj

	def getInvoke(self, op, dst):
		key = op, dst
		inv = self.invokeOut.get(key)
		if inv is None:
			inv = invocation.Invocation(self, op, dst)
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
		return self.analysis.objectName(xtype, qualifiers.HZ)

	def setupVParam(self, vparam):
		# Assign the vparam object to the vparam local
		vparamObj = self.vparamObj()
		lcl = self.local(vparam)
		lcl.updateSingleValue(vparamObj)

		numVParam = len(self.signature.vparams)

		# Set the length of the vparam object
		slot = self.field(vparamObj, 'LowLevel', self.analysis.pyObj('length'))
		slot.clearNull()
		slot.updateSingleValue(self.allocatePyObj(numVParam))

		# Copy the vparam locals into the vparam fields
		for i in range(numVParam):
			# Create a vparam field
			slot = self.field(vparamObj, 'Array', self.analysis.pyObj(i))
			slot.clearNull()
			self.vparamField.append(slot)


	def constraint(self, constraint):
		self.constraints.append(constraint)


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


	def local(self, lcl):
		if lcl not in self.locals:
			slot = node.ConstraintNode(self, lcl)
			self.locals[lcl] = slot
		else:
			slot = self.locals[lcl]
		return slot

	def field(self, obj, fieldType, name):
		return self.region.object(obj).field(fieldType, name)

	def assign(self, src, dst):
		constraint = flow.CopyConstraint(src, dst)
		self.constraint(constraint)

	def down(self, invoke, src, dst, fieldTransfer=False):
		assert src.context is not self
		assert dst.context is self

		constraint = flow.DownwardConstraint(invoke, src, dst, fieldTransfer)
		self.constraint(constraint)

	def updateCallgraph(self):
		changed = False

		for queue in (self.dirtycalls, self.dirtydcalls, self.dirtyfcalls):
			while queue:
				call = queue.pop()
				call.resolve(self)
				changed = True

		return changed
