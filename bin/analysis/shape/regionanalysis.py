# Unions heap objects into memory regions
# Basically, if two different objects can ever be refered to with
# the same pointer, they are collapsed into the same region.
# Note: regions may have cyclic points-to relationchips.
# As such, this analysis is not sound for "region allocation."

# Also, if a reference is "optionally None" there will be problems.
# In general, imutable objects should not be fused?

import PADS.UnionFind

import collections

class Region(object):
	def __init__(self, objects):
		self.objects = frozenset(objects)

	def __contains__(self, obj):
		return obj in self.objects

class RegionAnalysis(object):
	def __init__(self, extractor, entryPoints, adb):
		self.extractor = extractor
		self.entryPoints = entryPoints
		self.adb = adb
		self.uf = PADS.UnionFind.UnionFind()

	def merge(self, references):
		if references:
			self.uf.union(*references)

	def process(self):
		db = self.adb.db

		functionSensitive = True
		heapSensitive = True
		
		# Local references
		for func in db.liveFunctions():
			info = db.functionInfo(func)
			for local, localInfo in info.localInfos.iteritems():
				if functionSensitive:
					for context, clInfo in localInfo.contexts.iteritems():
						self.merge(clInfo.references)
				else:
					self.merge(localInfo.merged.references)

		# Heap references
		for heap, heapInfo in db.heapInfos.iteritems():
			for (slottype, key), slotInfo in heapInfo.slotInfos.iteritems():				
				if heapSensitive:
					for context, cInfo in slotInfo.contexts.iteritems():
						self.merge(cInfo.references)
				else:
					self.merge(slotInfo.merged.references)


		return self.makeRegions()


	def makeRegions(self):
		reverseLUT = collections.defaultdict(set)

		# HACK
		for obj, parent in self.uf.parents.iteritems():
			reverseLUT[parent].add(obj)

		lut = {}
		for parent, children in reverseLUT.iteritems():
			region = Region(children)
			for child in children:
				lut[child] = region
			
			if len(children) > 1:
				for child in children:
					print child
				print

		return lut

import analysis.objectreadmodifyquery

def evaluate(extractor, entryPoints, adb):
	orm = analysis.objectreadmodifyquery.ObjectReadModifyQuery(adb.db)
	
	
	ra = RegionAnalysis(extractor, entryPoints, adb)
	return ra.process()
