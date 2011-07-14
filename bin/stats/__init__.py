# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from analysis import astcollector

import collections
import sys
import os.path

import config
from util.io.filesystem import ensureDirectoryExists

import subprocess

from util.io.report import *

import optimization.cullprogram

import config

def classifyCode(code):
	if code.annotation.primitive:
		assert not code.annotation.interpreter, code
		assert not code.annotation.runtime, code
		return "primitive"
	elif code.annotation.interpreter:
		assert not code.annotation.runtime, code
		return "interp"
	elif code.annotation.runtime:
		return "runtime"
	else:
		if code.annotation.origin:
			filename = code.annotation.origin.filename
			if isGLSL(filename):
				return 'glsl'
		return 'user'


classes = 'user', 'glsl', 'interp', 'runtime', 'primitive'

def isGLSL(filename):
	if len(filename) > len(glslFiles):
		return filename[:len(glslFiles)].lower() == glslFiles
	return False

glslFiles = 'C:\\projects\\pystream\\bin\\shader'.lower()


class StatCollector(object):
	def __init__(self):
		self.limit = 16

		self.counts       = collections.defaultdict(lambda: collections.defaultdict(lambda: 0))
		self.codeCount    = collections.defaultdict(lambda: 0)
		self.contextCount = collections.defaultdict(lambda: 0)

		self.opCount        = collections.defaultdict(lambda: collections.defaultdict(lambda: 0))
		self.contextOpCount = collections.defaultdict(lambda: collections.defaultdict(lambda: 0))

		self.vargCount = 0
		self.contextVargCount = 0

		self.vparamCount = 0
		self.contextVparamCount = 0


		self.subfigures = []

		self.access = collections.defaultdict(lambda: 0)
		self.taccess = collections.defaultdict(lambda: 0)


	def code(self, cls, code):
		contexts = len(code.annotation.contexts)

		self.counts[min(contexts, self.limit)][cls] += 1

		self.codeCount[cls] += 1
		self.contextCount[cls] += contexts

		if code.codeparameters.vparam:
			self.vparamCount += 1
			self.contextVparamCount += contexts

	def op(self, cls, code, op):
		contexts = len(code.annotation.contexts)

		opT = type(op)
		self.opCount[cls][opT.__name__] += 1
		self.contextOpCount[cls][opT.__name__] += contexts

		if hasattr(op, 'vargs') and op.vargs:
			self.vargCount += 1
			self.contextVargCount += contexts


		ts = set()

		def handleSlot(slot):
			xtype = slot.object.xtype

			t = xtype.obj.pythonType()
			ts.add((t, slot.slotName))

			self.access[xtype] += 1


		for slot in op.annotation.opReads.merged:
			handleSlot(slot)

		for slot in op.annotation.opModifies.merged:
			handleSlot(slot)

		for t, f in ts:
			self.taccess[t] += 1


	def copies(self, cls, code, count):
		contexts = len(code.annotation.contexts)
		name = 'CopyLocal'

		self.opCount[cls][name] += count
		self.contextOpCount[cls][name] += count*contexts


	def digest(self):
		pass

	def contextOps(self):
		reindex = collections.defaultdict(lambda: 0)

		for cls in classes:
			for opT in asts:
				count = self.contextOpCount[cls][opT]
				reindex[opT] += count

		return reindex

def opRatios(collect, classOK):
	builder = TableBuilder('ops', '\%', 'c ops', '\%', 'ratio')
	builder.setFormats('%d', '%.1f', '%d', '%.1f', '%.1f')


	totalCode = 0
	totalContexts = 0

	for cls in classes:
		codeCount    = sumdict(collect.opCount[cls])
		contextCount = sumdict(collect.contextOpCount[cls])

		totalCode += codeCount
		totalContexts += contextCount

	if classOK:
		for cls in classes:
			codeCount    = sumdict(collect.opCount[cls])
			contextCount = sumdict(collect.contextOpCount[cls])

			builder.row(cls,
					codeCount, 100.0*codeCount/totalCode,
					contextCount, 100.0*contextCount/totalContexts,
					ratio(contextCount, codeCount))


	builder.row('total', totalCode, 100.0, totalContexts, 100.0, float(totalContexts)/totalCode)

	if not classOK: builder.rewrite(0, 2, 4)

	f = open(os.path.join(collect.reportdir, 'op-ratios.tex'), 'w')
	builder.dumpLatex(f, "%s-op-ratios" % collect.name)
	f.close()

	collect.subfigures.append(r"\include{op-ratios}")


def sumdict(d):
	amt = 0
	for v in d.itervalues():
		amt += v
	return amt

def ratio(top, bottom):

	if bottom:
		return float(top)/bottom
	else:
		return 0.0

def functionRatios(collect, classOK):
	builder = TableBuilder('functions', '\%', 'contexts', '\%', 'ratio')
	builder.setFormats('%d', '%.1f', '%d', '%.1f', '%.1f')


	totalCode = 0
	totalContexts = 0

	for cls in classes:
		codeCount    = collect.codeCount[cls]
		contextCount = collect.contextCount[cls]

		totalCode += codeCount
		totalContexts += contextCount

	for cls in classes:
		codeCount    = collect.codeCount[cls]
		contextCount = collect.contextCount[cls]

		if classOK:
			builder.row(cls,
					codeCount, ratio(100.0*codeCount, totalCode),
					contextCount, ratio(100.0*contextCount, totalContexts),
					ratio(contextCount, codeCount))


	builder.row('total', totalCode, 100.0, totalContexts, 100.0, float(totalContexts)/totalCode)

	if not classOK: builder.rewrite(0, 2, 4)

	f = open(os.path.join(collect.reportdir, 'context-ratios.tex'), 'w')
	builder.dumpLatex(f, "%s-context-ratios" % collect.name)
	f.close()

	collect.subfigures.append(r"\include{context-ratios}")


def opsRemoved(current, old):
	builder = TableBuilder('previous', 'current', '\% removed')
	builder.setFormats('%d', '%d', '%.1f')

	totalCode = 0
	totalContexts = 0

	oldOps     = old.contextOps()
	currentOps = current.contextOps()

	totalOld = 0.0
	totalCurrent = 0.0

	for name in asts:
		totalOld += oldOps[name]
		totalCurrent += currentOps[name]


	for name in asts:
		oldOp = oldOps[name]
		currentOp = currentOps[name]

		if oldOp:
			builder.row(name, oldOp, currentOp, 100.0*(oldOp-currentOp)/oldOp)
		else:
			if currentOp:
				builder.row(name, oldOp, currentOp, 0.0)

	builder.row('Total', totalOld, totalCurrent, 100.0*(totalOld-totalCurrent)/totalOld)

	f = open(os.path.join(current.reportdir, 'ops-removed.tex'), 'w')
	builder.dumpLatex(f, "%s-ops-removed" % current.name)
	f.close()

	current.subfigures.append(r"\include{ops-removed}")


def opPieChart(collect):
	reindex = collect.contextOps()

	pie = PieBuilder()

	for opT, color in zip(asts, astColors):
		pie.slice(opT, color, reindex[opT])

	filename = os.path.join(collect.reportdir, 'op-piechart.pl')
	f = open(filename, 'w')
	pie.dumpPloticus(f)
	f.close()

	subprocess.Popen("pl.exe -eps " + filename, shell=True)


	collect.subfigures.append(r"\subfloat[\label{fig:%s-op-piechard}]{\includegraphics[width=0.45\columnwidth]{op-piechart}" % collect.name)


def generateIndex(collect):
	filename = os.path.join(collect.reportdir, 'index.tex')
	f = open(filename, 'w')


	print >>f, r"\begin{figure}"
	for sub in collect.subfigures:
		print >>f, sub

	name = collect.name
	print >>f, r"\caption{%s Statistics}" % (name[0].upper() + name[1:])
	print >>f, r"\end{figure}"

def contextStats(compiler, prgm, name, classOK=False):
	if not config.dumpStats: return

	optimization.cullprogram.evaluate(compiler, prgm)

	reportdir = os.path.join(config.outputDirectory, 'stats', name)
	ensureDirectoryExists(reportdir)

	liveCode = prgm.liveCode

	collect = StatCollector()
	collect.name = name
	collect.reportdir = reportdir

	for code in liveCode:
		if not code.isStandardCode(): continue

		cls = classifyCode(code)

		collect.code(cls, code)

		if False:
			print code
			print cls, len(code.annotation.contexts)
			print code.annotation.origin

			print

		ops, lcls, copies = astcollector.getAll(code)

		for op in ops:
			collect.op(cls, code, op)

		collect.copies(cls, code, len(copies))

	# Histogram
	if False:
		for count in sorted(collect.counts.iterkeys()):
			print count
			for cls, num in collect.counts[count].iteritems():
				print '\t', cls, num
			print


	tw = collections.defaultdict(lambda: 0)
	tc = collections.defaultdict(lambda: 0)
	for xtype, count in collect.access.iteritems():
		tw[xtype.obj.pythonType()] += count
		tc[xtype.obj.pythonType()] += 1


	paw = 0
	tow = 0
	otc = 0
	for t, count in collect.taccess.iteritems():
		rel = tw[t]/float(tc[t])
		print t, count, rel
		paw += rel
		tow += count
		otc += 1

	tapo = float(tow)/otc
	papo = paw/otc
	print
	print tapo, papo, papo/tapo
	print

	functionRatios(collect, classOK)
	opRatios(collect, classOK)

	if prgm.stats:
		opsRemoved(collect, prgm.stats)

	if False:
		for cls, lut in collect.opCount.iteritems():
			print cls
			for opT, num in lut.iteritems():
				print '\t', opT, num
			print
		print


	opPieChart(collect)

	print "vparams"
	print collect.vparamCount, collect.contextVparamCount
	print

	print "vargs"
	print collect.vargCount, collect.contextVargCount
	print


	generateIndex(collect)

	prgm.stats = collect

	return collect
