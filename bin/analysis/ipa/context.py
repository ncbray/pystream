from . import constraints, calls
from language.python import ast, program

import collections

class Invocation(object):
	def __init__(self, src, op, dst):
		self.src = src
		self.op  = op
		self.dst = dst

		self.dst.invokeIn[(src, op)] = self
		self.src.invokeOut[(op, dst)] = self

		self.objForward = {}
		self.objReverse = collections.defaultdict(list)

	def copyDown(self, obj):
		# TODO copy down existing fields
		if obj not in self.objForward:
			remapped = self.dst.analysis.object(obj.name, constraints.DN)
			self.objForward[obj] = remapped
			self.objReverse[remapped].append(obj)
		else:
			remapped = self.objForward[obj]

		return remapped

	def copyFieldFromSources(self, slot):
		obj, fieldtype, name = slot.name
		assert isinstance(obj, constraints.AnalysisObject), obj

		prev = self.objReverse.get(obj)
		if not prev: return

		context = self.dst #?

		for prevobj in prev:
			prevfield = self.src.field(prevobj, fieldtype, name)
			context.down(self, prevfield, slot)


class Object(object):
	def __init__(self, context, name):
		self.context = context
		self.name   = name
		self.fields = {}

	def initDownwardField(self, slot):
		#print "DN COPY", slot
		for invoke in self.context.invokeIn.itervalues():
			invoke.copyFieldFromSources(slot)

	def initExistingField(self, slot):

		obj, fieldtype, fieldname = slot.name

		xtype = obj.name
		obj = xtype.obj

		assert isinstance(obj, program.AbstractObject), obj

		extractor = self.context.analysis.compiler.extractor

		extractor.ensureLoaded(obj)

		canonical = self.context.analysis.canonical

		if fieldtype == 'LowLevel' and fieldname.pyobj == 'type':
			# Type pointer
			self.updateExternal(slot, canonical.existingType(obj.type))
		elif xtype.isExternal():
			# User-specified memory image
			storeGraph = self.context.analysis.storeGraph
			sgobj = storeGraph.regionHint.object(xtype)
			canonicalField = canonical.fieldName(fieldtype, fieldname)
			sgfield = sgobj.field(canonicalField, storeGraph.regionHint)
			xtypes = sgfield.refs
			for ref in xtypes:
				self.updateExternal(slot, ref)
		else:
			# TODO
			#if isinstance(obj.pyobj, list):
			#	return set([canonical.existingType(t) for t in obj.array.itervalues()])
			
			# Extracted from memory
			if isinstance(obj, program.Object):
				if fieldtype == 'LowLevel':
					subdict = obj.lowlevel
				elif fieldtype == 'Attribute':
					subdict = obj.slot
				elif fieldtype == 'Array':
					subdict = obj.array
				elif fieldtype == 'Dictionary':
					subdict = obj.dictionary
				else:
					assert False, fieldtype
	
				if fieldname in subdict:
					self.updateExternal(slot, canonical.existingType(subdict[fieldname]))

	def updateExternal(self, slot, xtype):
		if xtype.isExternal():
			qualifier=constraints.HZ
		else:
			qualifier=constraints.GLBL
		
		ao = self.context.analysis.object(xtype, qualifier)
		slot.updateSingleValue(ao)

		if False:
			print "external"
			print slot
			print ao


	def field(self, fieldType, name):
		assert isinstance(fieldType, str), fieldType
		assert isinstance(name, program.AbstractObject), name

		key = (fieldType, name)

		if key not in self.fields:
			result = constraints.ConstraintNode(self.context, (self.name, fieldType, name))
			self.fields[key] = result

			if self.name.qualifier is constraints.DN:
				self.initDownwardField(result)
			elif self.context.external:
				self.initExistingField(result)
		else:
			result = self.fields[key]

		return result

class Region(object):
	def __init__(self, context):
		self.context = context
		self.objects = {}

	def object(self, obj):
		assert isinstance(obj, constraints.AnalysisObject), obj

		if obj not in self.objects:
			result = Object(self.context, obj)
			self.objects[obj] = result
		else:
			result = self.objects[obj]

		return result

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

		self.region = Region(self)

		self.external = False

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

	def field(self, obj, fieldType, name):
		assert isinstance(obj, constraints.AnalysisObject), obj
		assert isinstance(fieldType, str), fieldType
		assert isinstance(name, program.AbstractObject), name

		return self.region.object(obj).field(fieldType, name)


	def assign(self, src, dst):
		assert isinstance(src, constraints.ConstraintNode), src
		assert isinstance(dst, constraints.ConstraintNode), dst

		constraint = constraints.CopyConstraint(src, dst)
		self.constraint(constraint)

	def down(self, invoke, src, dst):
		assert isinstance(src, constraints.ConstraintNode), src
		assert isinstance(dst, constraints.ConstraintNode), dst

		assert src.context is not self
		assert dst.context is self

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

		print "OBJECTS"
		region = self.region
		for obj in region.objects.itervalues():
			print obj.name
			for slot in obj.fields.itervalues():
				print '\t', slot
				for value in slot.values:
					print '\t\t', value
			print
		print
