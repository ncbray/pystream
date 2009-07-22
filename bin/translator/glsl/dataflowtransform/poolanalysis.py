import PADS.UnionFind
import collections
import itertools

from util.graphalgorithim.color import colorGraph

leafTypes = (float, int, bool)


class PoolInfo(object):
	def __init__(self, objects):
		self.objects        = objects
		self.coloring       = None
		self.uniqueCount    = 0
		self.nonuniqueCount = 0
		self.preexisting    = False
		self.allocated      = False


class PoolAnalysis(object):
	def __init__(self, compiler, dataflow, analysis):
		self.compiler = compiler
		self.analysis = analysis
		self.dataflow = dataflow

		self.uf = PADS.UnionFind.UnionFind()

	def findInterference(self, group):
		interference = {}
		for obj in group:
			interference[obj] = set()

		if len(group) > 1:
			# n^2... ugly?
			for a, b in itertools.combinations(group, 2):
				maskA = self.analysis.objectExistanceMask[a]
				maskB = self.analysis.objectExistanceMask[b]
				intersect = self.analysis.bool.and_(maskA, maskB)

				if intersect is not self.analysis.bool.false:
					interference[a].add(b)
					interference[b].add(a)

		return interference

	def colorGroup(self, group):
		interference = self.findInterference(group)
		coloring, grouping, numColors = colorGraph(interference)
		return coloring, grouping


	def processGroup(self, group):
		info = PoolInfo(group)

		info.types = set([obj.xtype.obj.pythonType() for obj, index in group])
		info.polymorphic = len(info.types) > 1
		info.immutable   = all([t in leafTypes for t in info.types])
		assert not info.polymorphic or not info.immutable, group

		if info.immutable:
			return info


		info.coloring, grouping = self.colorGroup(group)
		for subgroup in grouping:
			unique = False
			nonunique = False
			for key in subgroup:
				if self.analysis.isUniqueObject(*key):
					unique = True
				else:
					nonunique = True

				if key in self.analysis.objectPreexisting:
					info.preexisting = True
				else:
					info.allocated   = True

			if unique:    info.uniqueCount += 1
			if nonunique: info.nonuniqueCount += 1

		# These assumptions make synthesis easier.
		#assert nonuniqueCount == 0, group # Temporary until loops are added.
		assert (info.uniqueCount == 0) ^ (info.nonuniqueCount == 0), group
		assert info.preexisting ^ info.allocated, group

		print group
		print info.types
		print info.uniqueCount, info.nonuniqueCount, info.preexisting, info.allocated
		print

		return info

	def process(self):
		# TODO a none reference will cause problems with the union... special case it?
		# Constants also cause problems?
		for (node, index), values in self.analysis._values.iteritems():
			flat = self.analysis.set.flatten(values)
			if flat:
				self.uf.union(*flat)

		# Invert the union find.
		index = collections.defaultdict(set)
		for ref in self.uf:
			# Predicates are scattered amoung the values.
			if isinstance(ref, tuple):
				index[self.uf[ref]].add(ref)

		lut = {}
		for group in index.itervalues():
			info = self.processGroup(group)
			for obj in info.objects:
				lut[obj] = info

		return lut


def process(compiler, dataflow, analysis):
	pa = PoolAnalysis(compiler, dataflow, analysis)
	return pa.process()
