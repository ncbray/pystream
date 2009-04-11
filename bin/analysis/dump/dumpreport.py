from util.xmloutput  import XMLOutput
from language.python import simplecodegen
import common.astpprint

import config
import os.path
from util import assureDirectoryExists, itergroupings

from analysis import programculler

from . import dumpgraphs
from . dumputil import *

import collections
from analysis import tools

import util.graphalgorithim.dominator

import urllib

from language.python import ast

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

def outputOrigin(out, origin):
	if origin:
		out.begin('a', href="file:%s"%(urllib.pathname2url(origin.filename),))
		out << "%s - %s:%d" % origin
		out.end('a')
	else:
		out << '<unknown origin>'

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


def printLabel(out, label):
	out.begin('div')
	out.begin('b')
	out << label
	out.end('b')
	out.end('div')
	out.endl()

def tableRow(out, links, label, *args):
	out.begin('tr')
	out.begin('td')
	out.begin('b')
	out << label
	out.end('b')
	out.end('td')
	out.begin('td')

	first = True
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

def dumpFunctionInfo(func, data, links, out, scg):
	code = func
	out.begin('h3')
	outputCodeShortName(out, func)
	out.end('h3')

	funcOps, funcLocals = tools.codeOpsLocals(func)

	if code.annotation.descriptive: printLabel(out, 'descriptive')
	if code.annotation.staticFold:  printLabel(out, 'static fold')
	if code.annotation.dynamicFold: printLabel(out, 'dynamic fold')

	origin = code.annotation.origin
	if origin:
		out.begin('div')
		outputOrigin(out, origin)
		out.end('div')
		out.endl()


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

	printLabel(out, '%d contexts' % len(code.annotation.contexts))

	for cindex, context in enumerate(code.annotation.contexts):
		out.tag('hr')
		out.begin('div')

		cref = links.contextRef(context)
		out.tag('a', name=cref)

		out.begin('p')
		out << context
		out.end('p')
		out.endl()
		out.endl()


		# Print call/return information for the function.
		code = func
		out.begin('p')
		out.begin('table')

		sig = context.signature
		if code.selfparam is not None:
			objs = code.selfparam.annotation.references[1][cindex]
			tableRow(out, links, 'self', *objs)

		numParam = len(sig.code.parameters)
		for i, param in enumerate(code.parameters):
			refs = param.annotation.references
			if refs:
				objs = refs[1][cindex]
			else:
				objs = ('?',)
			tableRow(out, links, 'param %d' % i, *objs)

		if code.vparam is not None:
			objs = code.vparam.annotation.references[1][cindex]
			tableRow(out, links, 'vparamObj', *objs)

			for vparamObj in objs:
				for i, arg in enumerate(sig.params[numParam:]):
					name = data.sys.canonical.fieldName('Array', data.sys.extractor.getObject(i))
					slot = vparamObj.knownField(name)
					tableRow(out, links, 'vparam %d' % i, *slot)

		if code.kparam is not None:
			objs = code.kparam.annotation.references[1][cindex]
			tableRow(out, links, 'kparamObj', *objs)

		for i, param in enumerate(code.returnparams):
			objs = param.annotation.references[1][cindex]
			tableRow(out, links, 'return %d' % i, *objs)

		out.end('table')
		out.end('p')
		out.endl()
		out.endl()

		origin = -1

		out.begin('pre')
		for op in funcOps:
			currentOrigin = op.annotation.origin
			if currentOrigin != origin:
				origin = currentOrigin
				out << '\t'
				outputOrigin(out, origin)
				out.endl()
				out.endl()

			out << '\t\t'
			out << op
			out.endl()

			if op.annotation.invokes:
				callees = op.annotation.invokes[1][cindex]
				for dstF, dstC in callees:
					out << '\t\t\t'
					outputCodeShortName(out, dstF, links, dstC)
					out.endl()
			else:
				out << "\t\t\t?"
				out.endl()


			read   = op.annotation.reads
			modify = op.annotation.modifies
			allocate = op.annotation.allocates

			s = ''
			if read and read[1][cindex]: s += "R"
			if modify and modify[1][cindex]: s += "M"
			if allocate and allocate[1][cindex]: s += "A"


			if s:
				out << '\t\t\t'
				out.begin('i')
				out << s
				out.end('i')
				out.endl()

			out.endl()

		out.endl()


		def printTabbed(out, name, values, links):
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

		for lcl in funcLocals:
			crefs = lcl.annotation.references
			if crefs is not None:
				refs = lcl.annotation.references[1][cindex]
			else:
				print "No refs for local?", code, lcl
				refs = ('?',)

			if isinstance(lcl, ast.Local):
				lclName = str(lcl) + ' / ' + scg.getLocalName(lcl)
			else:
				lclName = str(lcl)

			printTabbed(out, lclName, refs, links)
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


		live   = code.annotation.live
		killed = code.annotation.killed

		if live is not None:
			live   = live[1][cindex]
			killed = killed[1][cindex]

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

	printLabel(out, '%d contexts' % len(contexts))

	out.begin('pre')

	for context in contexts:
		out.begin('div')
		cref = links.contextRef(context)
		out.tag('a', name=cref)

		out << '\t'
		outputObjectShortName(out, context)
		out.endl()

		for slot in context:
			# Only print the slot if it can point to something.
			if slot.refs:
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
	liveFunctions, liveInvocations = programculler.findLiveFunctions(entryPoints)

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
				numContexts = len(func.annotation.contexts)
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


class DerivedData(object):
	def __init__(self, db):
		self.db = db

		self.invokeDestination = collections.defaultdict(set)
		self.invokeSource      = collections.defaultdict(set)
		self.funcReads         = collections.defaultdict(lambda: collections.defaultdict(set))
		self.funcModifies      = collections.defaultdict(lambda: collections.defaultdict(set))

		for func in db.liveFunctions():
			ops = tools.codeOps(func)
			for op in ops:
				self.handleOpInvokes(func, op)
				self.handleOpReads(func, op)
				self.handleOpModifies(func, op)


	def handleOpInvokes(self, code, op):
		invokes = op.annotation.invokes
		if invokes is not None:
			for cindex, context in enumerate(code.annotation.contexts):
				src = (code, context)

				for dst in invokes[1][cindex]:
					self.invokeDestination[src].add(dst)
					self.invokeSource[dst].add(src)

	def handleOpReads(self, code, op):
		reads = op.annotation.reads
		if reads is not None:
			for cindex, context in enumerate(code.annotation.contexts):
				creads = reads[1][cindex]
				self.funcReads[code][context].update(creads)

	def handleOpModifies(self, code, op):
		modifies = op.annotation.modifies
		if modifies is not None:
			for cindex, context in enumerate(code.annotation.contexts):
				cmods = modifies[1][cindex]
				self.funcModifies[code][context].update(cmods)


	def callers(self, function, context):
		return self.invokeSource[(function, context)]

	def callees(self, function, context):
		return self.invokeDestination[(function, context)]


def dump(name, extractor, dataflow, entryPoints):
	data = DerivedData(dataflow.db)
	data.sys = dataflow # HACK?
	dumpReport(name, data, entryPoints)

