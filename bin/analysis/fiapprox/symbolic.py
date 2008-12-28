# A symbolic wrapper for (numeric) BDD databases

import time
import math
from util import numbits

from analysis.bdddatalog import makeProgramDescription, makeInterpreter
from analysis.bdddatalog.relationalIR.interpreter import Interpreter

class BaseDomain(object):
	__slots__ = 'name',
	
	def bits(self):
		return numbits(len(self))

	def flattenNumeric(self, value, flat):
		flat.append(self.number(value))
		return flat


class SymbolicDomain(BaseDomain):
	def __init__(self, name):
		self.name = name
		self.numberToSymbol = []
		self.symbolToNumber = {}

	def add(self, symbol):
		#assert not symbol in self.symbolToNumber
		if not symbol in self.symbolToNumber:
			number = len(self.numberToSymbol)
			self.numberToSymbol.append(symbol)
			self.symbolToNumber[symbol] = number
		else:
			# For debugging.
			raise Exception, "Redefine %s/%s" % (self.name, repr(symbol))

	def extend(self, symbols):
		for symbol in symbols:
			self.add(symbol)

	def number(self, symbol):
		assert symbol in self.symbolToNumber, (self.name, symbol)
		return self.symbolToNumber[symbol]



	def symbol(self, number):
		assert number >= 0 and number < len(self.numberToSymbol), (self.name, number)
		return self.numberToSymbol[number]

	def __getitem__(self, index):
		return self.symbolToNumber[index]

	def __len__(self):
		return len(self.numberToSymbol)

	def __contains__(self, item):
		return item in self.symbolToNumber

	def __iter__(self):
		return iter(self.numberToSymbol)


	def checkSymbols(self, value, name):
		assert value in self, "Bad value for %s: %s not in %s." % (name, repr(value), self.name)


class NumericDomain(BaseDomain):
	def __init__(self, name, size):
		self.name = name
		self.size = size

	def number(self, symbol):
		return symbol

	def symbol(self, number):
		return number

	def __getitem__(self, index):
		return index

	def __len__(self):
		return self.size

	def checkSymbols(self, value, name):
		assert 0 <= value < self.size, "Bad value for %s: %s not in %s." % (name, repr(value), self.name)


class SymbolicStructure(object):
	def __init__(self, name, fields):
		assert isinstance(name, str)		
		assert isinstance(fields, (tuple, list)), fields
		
		self.name = name
		self.fields = fields


		self.fieldLUT = {}
		for name, d in self.fields:
			assert isinstance(name, str), name
			self.fieldLUT[name] = d

	def number(self, symbol):
		if isinstance(symbol, dict):
			outp = {}
			for k, v in symbol.iteritems():
				assert k in self.fieldLUT, (k, self.fieldLUT)
				outp[k] = self.fieldLUT[k].number(v)
			return outp
		else:
			assert isinstance(symbol, tuple) and len(symbol) == len(self.fields), (symbol, self.fields)
			return tuple([field.number(s) for s, (name, field) in zip(symbol, self.fields)])

	def flattenNumeric(self, values, flat):
		for (name, field), v, in zip(self.fields, values):
			field.flattenNumeric(v, flat)

		return flat

	def symbol(self, number):
		assert isinstance(number, tuple) and len(number) == len(self.fields), (self.fields, number)
		return tuple([field.symbol(n) for n, (name, field) in zip(number, self.fields)])

	def __getitem__(self, index):
		return self.symbol(index)

	def __contains__(self, symbol):
		if isinstance(symbol, tuple) and len(symbol) == len(self.fields):
			for s, (name, field) in zip(symbol, self.fields):
				if not s in field:
					return False
			return True
		else:
			return False

	def checkSymbols(self, symbol, name):
		assert isinstance(symbol, tuple) and len(symbol) == len(self.fields), "%s: expected a tuple of size %d, got %d." % (name, len(self.fields), len(symbol))
		for s, (fname, field) in zip(symbol, self.fields):				
			field.checkSymbols(s, "%s.%s" % (name, fname))


	def bits(self):
		bits = 0
		for name, d in self.fields:
			bits += d.bits()
		return bits

class TupleDatabase(object):
	def __init__(self, name, domain):
		self.name = name
		self.domain = domain
		self.data = []

		self.current = set()

	def add(self, *values):
		self.domain.checkSymbols(values, self.name)
		self.data.append(values)

		# HACK
		n = self.domain.number(values)

		# For some reason, merges generate redundant tuples?
		#assert self.name in ('returns', 'merge') or not n in self.current, (self.name, values)
		# Non-SSAed code may generate redundant tuples.
		self.current.add(n)

	def flattenNumeric(self, values):		
		flat = []
		self.domain.flattenNumeric(values, flat)
		return flat
		

	def addToRelation(self, interpreter):
		for values in self.data:
			flat = self.flattenNumeric(values)
			interpreter.setFlat(self.name, flat)
		
	def __len__(self):
		return len(self.data)

	def domainBits(self):
		return self.domain.bits()

	def totalBits(self):
		return len(self.data)*self.domain.bits()

	def dumpHTML(self, f):
		f.write("<h3>%s</h3>" % self.name)
		f.write("<table>\n")
		for row in self.data:
			f.write("<tr>")
			for col in row:
				f.write("<td>")
				f.write(repr(col))
				f.write("</td>")
			f.write("</tr>\n")
		f.write("</table>\n")


def getSymbolicDomain(d, domains):
	name = d.getName()
	if name in domains:
		sd = domains[name]
	else:
		# HACK always recreate symbolic structures.
		attr, lut = getSymbolicAttributes(d.attributes, domains)
		sd = SymbolicStructure(d.name, attr)
	return sd

def getSymbolicAttributes(attr, domains):
	attrout = []
	attrlut = {}
	for name, d in attr:
		assert isinstance(name, str)
		sd = getSymbolicDomain(d, domains)
		attrout.append((name, sd))
		attrlut[name] = sd
	
	return attrout, attrlut

class SymbolicRelation(object):
	def __init__(self, relation, domains):
		self.relation = relation
		self.attributes, self.attrLUT = getSymbolicAttributes(relation.attributes, domains)

		# HACK?
		self.__domains = domains


	def isFalse(self):
		return self.relation.isFalse()

	def isTrue(self):
		return self.relation.isTrue()

	def maybeFalse(self):
		return self.relation.maybeFalse()
	
	def maybeTrue(self):
		return self.relation.maybeTrue()

	def maybeEither(self):
		return self.relation.maybeEither()

	def __eq__(self, other):
		self.relation == other.relation

	def __ne__(self, other):
		self.relation != other.relation

	def __nonzero__(self):
		return bool(self.relation)

	def __or__(self, other):
		return SymbolicRelation(self.relation|other.relation, self.__domains)

	def __invert__(self):
		return SymbolicRelation(~self.relation, self.__domains)


	def invert(self):
		return SymbolicRelation(self.relation.invert(), self.__domains)

	def union(self, other):
		return SymbolicRelation(self.relation.union(other.relation), self.__domains)		

	def __translateRestriction(self, attr, restrict):
		translated = {}
		for name, symbol in restrict.iteritems():
			assert name in self.attrLUT, "Cannot restrict non-existant field %s." % repr(name)
			translated[name] = self.attrLUT[name].number(symbol)
		return translated

	def restrict(self, **kargs):
		translated = self.__translateRestriction(self.attributes, kargs)		
		restricted = self.relation.restrict(**translated)
		return SymbolicRelation(restricted, self.__domains)

	def rename(self, **kargs):
		return SymbolicRelation(self.relation.rename(**kargs), self.__domains)
		
	def relocate(self, **kargs):
		return SymbolicRelation(self.relation.relocate(**kargs), self.__domains)

	# Rename and relocate.
	def modify(self, **kargs):
		return SymbolicRelation(self.relation.modify(**kargs), self.__domains)

	def forget(self, *args):
		return SymbolicRelation(self.relation.forget(*args), self.__domains)

	
	def join(self, other):
		return SymbolicRelation(self.relation.join(other.relation), self.__domains)

	def compose(self, other):
		return SymbolicRelation(self.relation.compose(other.relation), self.__domains)

	def enumerateList(self):
		data = []		
		def addData(*args):
			data.append(args)

		self.enumerate(addData)
		return data

	def enumerateSet(self):
		data = set()		
		def addData(*args):
			assert len(args) == 1 # Ugly.
			data.add(args[0])

		self.enumerate(addData)
		return data

	def enumerate(self, callback):
		def translate(*args):
			translated = [d.symbol(arg) for (name, d), arg in zip(self.attributes, args)]
			callback(*translated)
		self.relation.enumerate(translate)

class SymbolicProgram(object):
	def __init__(self, algorithim):
		self.prgm = makeProgramDescription(algorithim)

		types = {}

		# Create symbolic domains.
		self.domains = {}
		for d in self.prgm.domains:
			sd = SymbolicDomain(d.name)
			self.domains[d.name] = sd
			types[d] = sd

		self.structures = {}

		for s in self.prgm.structures:
			domains = [(name, types[d]) for name, d in s.fields]
			ss = SymbolicStructure(s.name, domains)
			self.structures[s.name] = ss
			types[s] = ss

		self.types = types

		# Create databases for all the inputs.
		self.relations = {}
		for r in self.prgm.relations:
			if r.io == 'input':
				domains = [(name, types[d]) for name, d in r.fields]
				ss = SymbolicStructure(r.name, domains)
				self.relations[r.name] = TupleDatabase(r.name, ss)

	def link(self, domainOrder=None):
		bindings = {}
		for d in self.domains.itervalues():
			bindings[d.name] = len(d)

		start = time.clock()
		self.interp = Interpreter(self.prgm, bindings, domainOrder)
		print "Make interp: %.1fms" % ((time.clock()-start)*1000.0)


		bits = 0
		for r in self.relations.itervalues():
			bits += r.totalBits()
		print "Total bits: %d" % bits

		# Code for profiling the build process.
		if False:
			import hotshot, hotshot.stats
			prof = hotshot.Profile("build_relations.prof")
			prof.runcall(self.__buildInputs)
			prof.close()
			stats = hotshot.stats.load("build_relations.prof")
			stats.strip_dirs()
			stats.sort_stats('time', 'calls')
			stats.print_stats(40)
		else:
			self.__buildInputs()

	def __buildInputs(self):
		start = time.clock()
		for r in self.relations.itervalues():
			if r.name in self.interp.relations:
				r.addToRelation(self.interp)
		print "Build inputs: %.1fms" % ((time.clock()-start)*1000.0)
		print

		self.printNodeCounts()

	def printNodeCounts(self):
		print "Node Counts"
		for name, relation in self.interp.relations.iteritems():
			size = relation.data.DagSize()

			if size > 1:
				print "\t%-24.24s: %10.1d nodes" % (name, size)
		print



	def execute(self):
		time = self.interp.execute()
		self.createOutputs()
		#self.printNodeCounts()
		return time

	def createOutputs(self):
		self.inputs = {}
		self.outputs = {}
		for r in self.prgm.relations:
			if r.io == 'output':
				relation = self.interp.relations[r.name]
				self.outputs[r.name] = SymbolicRelation(relation, self.domains)
			elif r.io == 'input':
				relation = self.interp.relations[r.name]
				self.inputs[r.name] = SymbolicRelation(relation, self.domains)
