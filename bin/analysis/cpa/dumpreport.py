from util.xmloutput  import XMLOutput
from common import simplecodegen
import common.astpprint

import os.path
from util import assureDirectoryExists, itergroupings

from programIR.python.ast import isPythonAST
import programIR.python.ast as ast
import programIR.python.program as program

from . import base
from . import storegraph

from . import programculler

from . import dumpgraphs

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
		context = None
		xtype   = None

		if isinstance(obj, storegraph.ObjectNode):
			context = obj
			xtype   = obj.xtype
			obj     = xtype.obj

		if obj not in self.objectFile: return None

		fn = self.objectFile[obj]

		if context:
			cn = self.contextRef(context)
			fn = "%s#%s" % (fn, cn)

		return fn


	def codeRef(self, code, context):
		if code not in self.functionFile:
			return None

		link = self.functionFile[code]

		if context is not None:
			link = "%s#%s" % (link,  self.contextRef(context))

		return link

# TODO share this with CPA?
class CodeContext(object):
	__slots__ = 'code', 'context',
	def __init__(self, code, context):
		assert isinstance(code, ast.Code), type(code)
		self.code = code
		self.context = context

def codeShortName(code):
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

	return "%s(%s)" % (name, ", ".join(args))


def objectShortName(obj):
	if isinstance(obj, storegraph.ObjectNode):
		context = obj
		xtype   = obj.xtype
		obj     = xtype.obj
		return repr(xtype)

	return repr(obj)

def outputCodeShortName(out, code, links=None, context=None):
	link = links.codeRef(code, context) if links is not None else None

	if link: out.begin('a', href=link)
	out << codeShortName(code)
	if link: out.end('a')


def outputObjectShortName(out, heap, links=None):
	if links != None:
		link = links.objectRef(heap)
	else:
		link = None

	if link:
		out.begin('a', href=link)
	out << objectShortName(heap)
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
	out.begin('a', href="invocations.svg")
	out << "Function Graph"
	out.end('a')
	out << " | "
	out.begin('a', href="object_index.html")
	out << "Objects"
	out.end('a')
	out << "]"
	out.tag('br')


def dumpFunctionInfo(func, data, links, out, scg):
	out.begin('h3')
	outputCodeShortName(out, func)
	out.end('h3')

	info = data.db.functionInfo(func)
	funcOps = data.adb.functionOps(func)
	funcLocals = data.adb.functionLocals(func)

	if info.descriptive:
		out.begin('div')
		out.begin('b')
		out << 'descriptive'
		out.end('b')
		out.end('div')

	if info.fold:
		out.begin('div')
		out.begin('b')
		out << 'fold'
		out.end('b')
		out.end('div')


	# Psedo-python output
	if func is not None:
		out.begin('pre')
		scg.walk(func)
		out.end('pre')

	# Pretty printer for debugging
	if False:
		out.begin('pre')
		common.astpprint.pprint(func, out)
		out.end('pre')

	numContexts = len(data.functionContexts(func))

	out.begin('div')
	out.begin('b')
	out << '%d contexts' % numContexts
	out.end('b')
	out.end('div')


	for context in data.functionContexts(func):
		out.tag('hr')
		out.begin('div')

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
				if not first: out.tag('br')
				link = links.objectRef(arg)
				if link: out.begin('a', href=link)
				out << objectShortName(arg)
				if link: out.end('a')

				first = False

			out.end('td')
			out.end('tr')
			out.endl()


		# Print call/return information for the function.
		code = func
		out.begin('p')
		out.begin('table')

		sig = context.signature
		if code.selfparam is not None:
			objs = info.localInfo(code.selfparam).context(context).references
			tableRow('self', *objs)

		numParam = len(sig.code.parameters)
		for i, param in enumerate(code.parameters):
			objs = info.localInfo(param).context(context).references
			tableRow('param %d' % i, *objs)

		if code.vparam is not None:
			objs = info.localInfo(code.vparam).context(context).references
			tableRow('vparamObj', *objs)

			for vparamObj in objs:
				for i, arg in enumerate(sig.params[numParam:]):
					name = data.sys.canonical.fieldName('Array', data.sys.extractor.getObject(i))
					slot = vparamObj.knownField(name)
					tableRow('vparam %d' % i, *slot)

		if code.kparam is not None:
			objs = info.localInfo(code.kparam).context(context).references
			tableRow('kparamObj', *objs)

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
			if slot.slotName.isLocal():
				lcls.append(slot)
			elif slot.slotName.isExisting():
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
				out << objectShortName(value)
				if link: out.end('a')
				out.endl()


		out.begin('pre')
		for op in funcOps:
			printTabbed(op, info.opInfo(op).context(context).references)

			callees = data.opCallees(func, op, context)
			for dstC, dstF in callees:
				out << '\t\t'
				outputCodeShortName(out, dstF, links, dstC)
				out.endl()

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

		out.endl()

		for lcl in funcLocals:
			printTabbed(lcl, info.localInfo(lcl).context(context).references)
		out.end('pre')
		out.endl()

		callers = data.callers(func, context)
		if callers:
			out.begin('h3')
			out << "Callers"
			out.end('h3')
			out.begin('p')
			out.begin('ul')
			for callerF, callerC in callers:
				out.begin('li')
				outputCodeShortName(out, callerF, links, callerC)
				out.end('li')
			out.end('ul')
			out.end('p')

		callees = data.callees(func, context)
		if callees:
			out.begin('h3')
			out << "Callees"
			out.end('h3')
			out.begin('p')
			out.begin('ul')
			for callerF, callerC in callees:
				out.begin('li')
				outputCodeShortName(out, callerF, links, callerC)
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
					outputObjectShortName(out, obj, links)
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
				for obj, slots in itergroupings(reads, lambda slot: slot.object, lambda slot: slot.slotName):
					out.begin('li')
					outputObjectShortName(out, obj, links)

					out.begin('ul')
					for slot in slots:
						out.begin('li')
						out << "%r" % slot
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
				for obj, slots in itergroupings(modifies, lambda slot: slot.object, lambda slot: slot.slotName):
					out.begin('li')
					outputObjectShortName(out, obj, links)

					out.begin('ul')
					for slot in slots:
						out.begin('li')
						out << "%r" % slot
						out.end('li')
					out.end('ul')

					out.end('li')
				out.end('ul')
				out.end('p')
		out.end('div')


def dumpHeapInfo(heap, data, links, out):
	out.begin('h3')
	outputObjectShortName(out, heap)
	out.end('h3')
	out.endl()

	heapInfo = data.db.heapInfo(heap)
	contexts = heapInfo.contexts

	call = data.sys.extractor.getCall(heap)
	if call:
		out.begin('div')
		out << 'On call: '
		outputCodeShortName(out, call, links)
		out.end('div')

	out.begin('div')
	out.begin('b')
	out << '%d contexts' % len(contexts)
	out.end('b')
	out.end('div')

	out.begin('pre')

	for context in contexts:
		out.begin('div')
		cref = links.contextRef(context)
		out.tag('a', name=cref)

		out << '\t'
		outputObjectShortName(out, context)
		out.endl()

		for slot in context:
			out << '\t\t%r' % slot.slotName
			if slot.null:
				out << " (null?)"
			out.endl()
			for ref in slot:
				out << '\t\t\t'
				outputObjectShortName(out, ref, links)
				out.endl()

		out.end('div')
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
	tree, idoms = util.graphalgorithim.dominator.dominatorTree(invokes, head)
	return tree, head


def makeHeapTree(data):
	liveHeap = data.db.liveObjects()

	head = None
	points = {}
	for heap in liveHeap:
		heapInfo = data.db.heapInfo(heap)

		points[heap] = set()

		for (slottype, key), info in heapInfo.slotInfos.iteritems():
			values = info.merged.references
			for dst in values:
				ogroup = dst.xtype.group()
				assert ogroup in liveHeap, (heap, ogroup)
				points[heap].add(ogroup)

	util.graphalgorithim.dominator.makeSingleHead(points, head)
	tree, idoms = util.graphalgorithim.dominator.dominatorTree(points, head)
	return tree, head

def dumpReport(name, data, entryPoints):
	reportDir = makeReportDirectory(name)

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


	liveHeap = data.db.liveObjects()
	liveFunctions, liveInvocations = programculler.findLiveFunctions(data.db, entryPoints)

	out, scg = makeOutput(reportDir, 'function_index.html')
	dumpHeader(out)

	out.begin('h2')
	out << "Function Index"
	out.end('h2')


	head =  None
	tree, idoms = util.graphalgorithim.dominator.dominatorTree(liveInvocations, head)

	def printChildren(node):
		children = tree.get(node)
		if children:
			out.begin('ul')
			for func in sorted(children, key=lambda f: f.name):
				out.begin('li')
				makeFunctionFile(func)
				outputCodeShortName(out, func, links)
				numContexts = len(data.functionContexts(func))
				if numContexts > 1:
					out << " "
					out << numContexts
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

				numContexts = len(data.db.heapInfo(heap).contexts)
				if numContexts > 1:
					out << " "
					out << numContexts
				count += printHeapChildren(heap) + 1
				out.end('li')
			out.end('ul')
			out.endl()
		return count

	count = printHeapChildren(head)

	if count != len(liveHeap):
		print "WARNING: tree contains %d elements, whereas there are %d expected." % (count, len(liveHeap))

	missing = set(liveHeap)-nodes
	if missing:
		print "Missing"
		for node in missing:
			print node
		print


	extra = nodes-liveHeap
	if extra:
		print "Extra"
		for node in extra:
			print node
		print

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

	dumpgraphs.dump(data, entryPoints, links, reportDir)

import collections
import base
from analysis.astcollector import getOps

class CPAData(object):
	def __init__(self, inter, db):

		self.db = db
		self.inter = inter

		self.lcls = collections.defaultdict(lambda: collections.defaultdict(set))
		self.objs = collections.defaultdict(lambda: collections.defaultdict(set))

		for slot in inter.roots:
			name = slot.slotName
			if name.isLocal():
				self.lcls[name.code][name.context].add(slot)

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

	def opCallees(self, code, op, context):
		return self.db.functionInfo(code).opInfo(op).context(context).invokes


	def slot(self, slot):
		return self.inter.slots[slot]

	def liveHeap(self):
		return self.objs.keys()

	def heapContexts(self, heap):
		return self.objs[heap].keys()

	def heapContextSlots(self, heapC):
		return self.objs[heapC.obj][heapC]


from . analysisdatabase import CPAAnalysisDatabase

def dump(name, extractor, dataflow, entryPoints):
	adb = CPAAnalysisDatabase(dataflow.db)
	data = CPAData(dataflow, dataflow.db)
	data.adb = adb
	data.sys = dataflow # HACK?
	dumpReport(name, data, entryPoints)

