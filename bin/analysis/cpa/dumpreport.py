from util.xmloutput  import XMLOutput
from common import simplecodegen

import os.path
from util import assureDirectoryExists

from programIR.python.ast import isPythonAST
import programIR.python.ast as ast
import programIR.python.program as program

from . import base

from . import programculler

import config

class LinkManager(object):
	def __init__(self):
		self.functionFile = {}
		self.objectFile = {}
		self.contextName = {}

		self.cid = 0

	def contextRef(self, context):
		if not context in self.contextName:
			self.contextName[context] = "c%d" % self.cid
			self.cid += 1
			assert context in self.contextName
		return self.contextName[context]

	def objectRef(self, obj):
		if isinstance(obj, program.AbstractObject):
			if obj not in self.objectFile: return None
			return self.objectFile[obj]
		else:
			if obj.obj not in self.objectFile: return None

			fn = self.objectFile[obj.obj]
			cn = self.contextRef(obj.context)
			return "%s#%s" % (fn, cn)

	def codeRef(self, obj):
		if isinstance(obj, ast.Code) or obj is None:
			if obj not in self.functionFile: return None
			return self.functionFile[obj]
		else:
			if obj.code not in self.functionFile: return None
			fn = self.functionFile[obj.code]
			cn = self.contextRef(obj.context)
			return "%s#%s" % (fn, cn)

# TODO share this with CPA?
class CodeContext(object):
	__slots__ = 'code', 'context',
	def __init__(self, code, context):
		assert isinstance(code, ast.Code), type(code)
		self.code = code
		self.context = context

def codeShortName(out,code, links=None, context = None):
	if isinstance(code, str):
		name = func
		args = []
		vargs = None
		kargs = None
	elif code is None:
		name = 'external'
		args = []
		vargs = None
		kargs = None
	else:
		name = code.name
		args = list(code.parameternames)
		vargs = None if code.vparam is None else code.vparam.name
		kargs = None if code.kparam is None else code.kparam.name

	if vargs is not None: args.append("*"+vargs)
	if kargs is not None: args.append("**"+kargs)


	if links is not None:
		if context is not None:
			link = links.codeRef(CodeContext(code, context))
		else:
			link = links.codeRef(code)
	else:
		link = None


	if link: out.begin('a', href=link)
	out << "%s(%s)" % (name, ", ".join(args))
	if link: out.end('a')


def heapShortName(out, heap, links=None):
	if links != None:
		link = links.objectRef(heap)
	else:
		link = None

	if link:
		out.begin('a', href=link)
	out << repr(heap)
	if link:
		out.end('a')

def heapLink(out, heap, links=None):
	if links != None:
		link = links.objectRef(heap)
	else:
		link = None

	if link:
		out.begin('a', href=link)
	out << repr(heap)
	if link:
		out.end('a')


class TypeInferenceData(object):
	def liveFunctions(self):
		raise NotImplemented

	def liveHeap(self):
		raise NotImplemented

	def heapContexts(self, heap):
		raise NotImplemented

	def heapContextSlots(self, heapC):
		raise NotImplemented

	def heapContextSlot(self, slot):
		raise NotImplemented





def makeReportDirectory(moduleName):
	reportdir = os.path.join(config.outputDirectory, moduleName)
	assureDirectoryExists(reportdir)

	return reportdir

def makeOutput(reportDir, filename):
	fullpath = os.path.join(reportDir, filename)
	fout = open(fullpath, 'w')
	out = XMLOutput(fout)
	scg = simplecodegen.SimpleCodeGen(out) # HACK?
	return out, scg

def dumpHeader(out):
	out << "["
	out.begin('a', href="function_index.html")
	out << "Functions"
	out.end('a')
	out << " | "
	out.begin('a', href="object_index.html")
	out << "Objects"
	out.end('a')
	out << "]"
	out.tag('br')

def itergroupings(iterable, key):
	grouping = {}
	for i in iterable:
		group, data = key(i)
		if not group in grouping:
			grouping[group] = [data]
		else:
			grouping[group].append(data)
	return grouping.iteritems()

def dumpFunctionInfo(func, data, links, out, scg):
	out.begin('h3')
	codeShortName(out, func)
	out.end('h3')

	info = data.db.functionInfo(func)
	funcOps = data.adb.functionOps(func)
	funcLocals = data.adb.functionLocals(func)

	if info.descriptive:
		out.begin('p')
		out.begin('b')
		out << 'descriptive'
		out.end('b')
		out.end('p')

	if func is not None:
		out.begin('pre')
		scg.walk(func)
		out.end('pre')

	numContexts = len(data.functionContexts(func))

	out.begin('p')
	out.begin('b')
	out << '%d contexts' % numContexts
	out.end('b')
	out.end('p')


	for context in data.functionContexts(func):
		out.tag('hr')

		cref = links.contextRef(context)
		out.tag('a', name=cref)

		out.begin('p')
		out << context
		out.end('p')
		out.endl()
		out.endl()

		def tableRow(label, *args):
			first = True
			out.begin('tr')
			out.begin('td')
			out.begin('b')
			out << label
			out.end('b')
			out.end('td')
			out.begin('td')

			for arg in args:
				if not first:
					out.tag('br')
				obj = arg.obj
				link = links.objectRef(arg)
				if link: out.begin('a', href=link)
				out << arg
				if link: out.end('a')

				first = False

			out.end('td')
			out.end('tr')
			out.endl()

		# HACK should pull from function information and contextualize
		if isinstance(context, base.CPAContext):
			out.begin('p')
			out.begin('table')


			sig = context.signature
			if sig.selfparam is not None:
				tableRow('self', sig.selfparam)

			for i, arg in enumerate(sig.params):
				tableRow('param %d' % i, arg)

			for i, arg in enumerate(sig.vparams):
				tableRow('vparam %d' % i, arg)

			if context.vparamObj is not None:
				tableRow('vparamObj', context.vparamObj)

			if context.kparamObj is not None:
				tableRow('kparamObj', context.kparamObj)

			returnSlot = func.returnparam
			values = info.localInfo(returnSlot).context(context).references
			tableRow('return', *values)

			out.end('table')
			out.end('p')
			out.endl()
			out.endl()

		ops  = []
		lcls = []
		other = []

		for slot in data.functionContextSlots(func, context):
			if isinstance(slot.local, ast.Local):
				lcls.append(slot)
			elif isinstance(slot.local, program.AbstractObject):
				other.append(slot)
			else:
				ops.append(slot)

		def printTabbed(name, values):
			out << '\t'
			out << name
			out.endl()

			for value in values:
				out << '\t\t'
				link = links.objectRef(value)
				if link: out.begin('a', href=link)
				out << value
				if link: out.end('a')
				out.endl()


		out.begin('pre')
		for op in funcOps:
			printTabbed(op, info.opInfo(op).context(context).references)

			if hasattr(data.db, 'lifetime'):
				read   = data.db.lifetime.readDB[func][op][context]
				modify = data.db.lifetime.modifyDB[func][op][context]

				# HACK?
				if read or modify:
					out << '\t\t'
					out.begin('i')
					if read: out << "R"
					if modify: out << "M"
					out.end('i')
					out.endl()

		out.endl()

		for lcl in funcLocals:
			printTabbed(lcl, info.localInfo(lcl).context(context).references)
		out.end('pre')
		out.endl()


		out.begin('h3')
		out << "Callers"
		out.end('h3')
		out.begin('p')
		out.begin('ul')
		for callerF, callerC in data.callers(func, context):
			out.begin('li')
			codeShortName(out, callerF, links, callerC)
			out.end('li')
		out.end('ul')
		out.end('p')


		out.begin('h3')
		out << "Callees"
		out.end('h3')
		out.begin('p')
		out.begin('ul')
		for callerF, callerC in data.callees(func, context):
			out.begin('li')
			codeShortName(out, callerF, links, callerC)
			out.end('li')
		out.end('ul')
		out.end('p')


		if hasattr(data.db, 'lifetime'):
			live = data.db.lifetime.live[(func, context)]
			killed = data.db.lifetime.contextKilled[(func, context)]

			if live:
				out.begin('h3')
				out << "Live"
				out.end('h3')
				out.begin('p')
				out.begin('ul')
				for obj in live:
					out.begin('li')
					heapLink(out, obj, links)
					if obj in killed:
						out << " (killed)"
					out.end('li')
				out.end('ul')
				out.end('p')


			reads = data.funcReads[func][context]

			if reads:
				out.begin('h3')
				out << "Reads"
				out.end('h3')
				out.begin('p')
				out.begin('ul')
				for obj, slots in itergroupings(reads, lambda slot: (slot.obj, (slot.slottype, slot.key))):
					out.begin('li')
					heapLink(out, obj, links)

					out.begin('ul')
					for slot in slots:
						out.begin('li')
						out << "%s - %r" % slot
						out.end('li')
					out.end('ul')

					out.end('li')
				out.end('ul')
				out.end('p')


			modifies = data.funcModifies[func][context]

			if modifies:
				out.begin('h3')
				out << "Modifies"
				out.end('h3')
				out.begin('p')
				out.begin('ul')
				for obj, slots in itergroupings(modifies, lambda slot: (slot.obj, (slot.slottype, slot.key))):
					out.begin('li')
					heapLink(out, obj, links)

					out.begin('ul')
					for slot in slots:
						out.begin('li')
						out << "%s - %r" % slot
						out.end('li')
					out.end('ul')

					out.end('li')
				out.end('ul')
				out.end('p')

def dumpHeapInfo(heap, data, links, out):
	out.begin('h3')
	heapShortName(out, heap)
	out.end('h3')
	out.endl()

	heapInfo = data.db.heapInfo(heap)
	contexts = heapInfo.contexts

	out.begin('pre')

	for context in contexts:
		cref = links.contextRef(context)
		out.tag('a', name=cref)

		out << '\t'+str(context)+ '\n'

		for (slottype, key), info in heapInfo.slotInfos.iteritems():
			values = info.context(context).references
			if values:
				out << '\t\t%s / %s\n' % (str(slottype), str(key))
				for value in values:
					out << '\t\t\t'
					heapLink(out, value, links)
					out.endl()

#	la = data.db.lifetime

		# HACK no easy way to get the context object, anymore?
##		info = la.getObjectInfo(contextobj)
##
##		if info.heldByClosure:
##			out << '\t\tHeld by (closure)\n'
##			for holder in info.heldByClosure:
##				out << '\t\t\t'
##				heapLink(out, holder.obj, links)
##				out.endl()
		out.endl()

	out.end('pre')

import util.graphalgorithim.dominator

def makeFunctionTree(data):
	liveFunctions = data.liveFunctions()

	head = None
	invokes = {}
	for func in liveFunctions:
		info = data.db.functionInfo(func)

		invokes[func] = set()

		for opinfo in info.opInfos.itervalues():
			for dstc, dstf in opinfo.merged.invokes:
				invokes[func].add(dstf)

	util.graphalgorithim.dominator.makeSingleHead(invokes, head)
	tree = util.graphalgorithim.dominator.dominatorTree(invokes, head)
	return tree, head


def makeHeapTree(data):
	liveHeap= data.liveHeap()

	head = None
	points = {}
	for heap in liveHeap:
		heapInfo = data.db.heapInfo(heap)

		points[heap] = set()

		for (slottype, key), info in heapInfo.slotInfos.iteritems():
			values = info.merged.references
			for dst in values:
				points[heap].add(dst.obj)

	util.graphalgorithim.dominator.makeSingleHead(points, head)
	tree = util.graphalgorithim.dominator.dominatorTree(points, head)
	return tree, head

def dumpReport(data, entryPoints):
	reportDir = makeReportDirectory('cpa')

	links = LinkManager()

	heapToFile = {}
	funcToFile = {}

	# HACK for closure
	uid = [0,0]

	def makeHeapFile(heap):
		fn = "h%07d.html" % uid[0]
		links.objectFile[heap] = fn
		heapToFile[heap] = fn
		uid[0] += 1
		return fn

	def makeFunctionFile(func):
		fn = "f%07d.html" % uid[1]
		links.functionFile[func] = fn
		funcToFile[func] = fn
		uid[1] += 1
		return fn


	liveHeap = data.liveHeap()
	liveFunctions, liveInvocations = programculler.findLiveFunctions(data.db, entryPoints)

	out, scg = makeOutput(reportDir, 'function_index.html')
	dumpHeader(out)

	out.begin('h2')
	out << "Function Index"
	out.end('h2')


	head =  None
	tree = util.graphalgorithim.dominator.dominatorTree(liveInvocations, head)

	def printChildren(node):
		children = tree.get(node)
		if children:
			out.begin('ul')
			for func in sorted(children, key=lambda f: f.name):
				out.begin('li')
				makeFunctionFile(func)
				codeShortName(out, func, links)
				printChildren(func)
				out.end('li')
			out.end('ul')
			out.endl()

	printChildren(head)

	out, scg = makeOutput(reportDir, 'object_index.html')
	dumpHeader(out)

	out.begin('h2')
	out << "Object Index"
	out.end('h2')


	tree, head = makeHeapTree(data)
	nodes = set()
	def printHeapChildren(node):
		count = 0
		children = tree.get(node)
		if children:
			out.begin('ul')
			for heap in sorted(children, key=lambda o: repr(o)):
				out.begin('li')
				makeHeapFile(heap)
				link = links.objectRef(heap)
				if link: out.begin('a', href=link)
				out << heap
				nodes.add(heap)
				if link: out.end('a')
				count += printHeapChildren(heap) + 1
				out.end('li')
			out.end('ul')
			out.endl()
		return count

	count = printHeapChildren(head)

	if count != len(liveHeap):
		print "WARNING: tree contains %d elements, whereas there are %d expected." % (count, len(liveHeap))

##	print "Extra"
##	for node in nodes-set(liveHeap):
##		print node
##	print

	missing = set(liveHeap)-nodes
	if missing:
		print "Missing"
		for node in missing:
			print node
		print


##	out.begin('ul')
##	for heap in liveHeap:
##		out.begin('li')
##		out.begin('a', href=links.objectRef(heap))
##		out << heap
##		out.end('a')
##		out.end('li')
##	out.end('ul')
##	out.endl()

	out.close()

	for func in liveFunctions:
		out, scg = makeOutput(reportDir, funcToFile[func])
		dumpHeader(out)
		dumpFunctionInfo(func, data, links, out, scg)
		out.endl()
		out.close()


	for heap in liveHeap:
		out, scg = makeOutput(reportDir, heapToFile[heap])
		dumpHeader(out)
		dumpHeapInfo(heap, data, links, out)
		out.endl()
		out.close()


import collections
import base
from analysis.astcollector import getOps

class CPAData(object):
	def __init__(self, inter, db):

		self.db = db
		self.inter = inter

		self.lcls = collections.defaultdict(lambda: collections.defaultdict(set))
		self.objs = collections.defaultdict(lambda: collections.defaultdict(set))

		for slot, values in inter.slots.iteritems():
			if isinstance(slot, base.LocalSlot):
				self.lcls[slot.code][slot.context].add(slot)
			else:
				self.objs[slot.obj.obj][slot.obj].add(slot)


		self.calcInvocations()
		self.calcReadModify()

	def calcInvocations(self):
		# Derived
		self.invokeDestination = collections.defaultdict(set)
		self.invokeSource      = collections.defaultdict(set)

		for func, funcinfo in self.db.functionInfos.iteritems():
			ops, lcls = getOps(func)
			for op in ops:
				copinfo = funcinfo.opInfo(op)
				for context, opinfo in copinfo.contexts.iteritems():
					src = (func, context)
					for dstC, dstF in opinfo.invokes:
						dst = (dstF, dstC)
						self.invokeDestination[src].add(dst)
						self.invokeSource[dst].add(src)


	def calcReadModify(self):
		self.funcReads    = collections.defaultdict(lambda: collections.defaultdict(set))
		self.funcModifies = collections.defaultdict(lambda: collections.defaultdict(set))

		if hasattr(self.db, 'lifetime'):
			for func, ops in self.db.lifetime.readDB:
				for op, contexts in ops:
					for context, reads in contexts:
						if reads:
							self.funcReads[func][context].update(reads)

			for func, ops in self.db.lifetime.modifyDB:
				for op, contexts in ops:
					for context, modifies in contexts:
						if modifies:
							self.funcModifies[func][context].update(modifies)



	def liveFunctions(self):
		return self.db.liveFunctions()

	def functionContexts(self, func):
		return self.db.functionInfo(func).contexts

	def functionContextSlots(self, function, context):
		return self.lcls[function][context]

	def callers(self, function, context):
		return self.invokeSource[(function, context)]

	def callees(self, function, context):
		return self.invokeDestination[(function, context)]

	def slot(self, slot):
		return self.inter.slots[slot]

	def liveHeap(self):
		return self.objs.keys()

	def heapContexts(self, heap):
		return self.objs[heap].keys()

	def heapContextSlots(self, heapC):
		return self.objs[heapC.obj][heapC]


from . analysisdatabase import CPAAnalysisDatabase

def dump(extractor, dataflow, entryPoints):
	print
	print "Dumping report..."

	adb = CPAAnalysisDatabase(dataflow.db)
	data = CPAData(dataflow, dataflow.db)
	data.adb = adb
	dumpReport(data, entryPoints)

