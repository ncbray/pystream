from util.graphalgorithim import djtree

class ExclusionGraph(object):
	def __init__(self):
		self.exInfo = {}

	def getSwitch(self, node):
		info = self.exInfo.get(node)
		if info:
			switch = info.switch
		else:
			switch = None # No exInfo, no switch
		return switch

	def infoNames(self, info):
		if info is None:
			names = (None,)
		else:
			names = [(info.switch, element) for element in info.mask]
		return names

	def markSwitches(self, switch, partial, complete):
		for name in self.infoNames(switch.info):
			if name in complete:
				return False
			else:
				partial.add(name)

		# TODO kill redundant?
		if switch.idom is not None:
			return self.markSwitches(switch.idom, partial, complete)
		else:
			return True

	def markLeaf(self, info, partial, complete):
		for name in self.infoNames(info):
			if name in complete or name in partial:
				return False
			else:
				complete.add(name)
			return True

	def mutuallyExclusive(self, *args):
		if len(args) < 2: return True

		partial  = set()
		complete = set()

		for arg in args:
			info = self.exInfo.get(arg)

			if info is not None:
				if not self.markSwitches(info.switch, partial, complete):
					return False

			if not self.markLeaf(info, partial, complete):
				return False

		return True


class ExclusionSwitch(object):
	def __init__(self, idom, info, dj):
		assert idom is None or isinstance(idom, ExclusionSwitch), idom
		self.idom  = idom
		self.info  = info
		self.dj    = dj

	def __repr__(self):
		return "exswitch(%r)" % self.dj.node

	def completeMask(self, mask):
		return len(mask) >= len(self.lut)

	def dominates(self, other):
		current = other
		while other is not None:
			if self is current:
				return True
			current = other.idom

		return False

	def simplify(self):
		if self.info is not None:
			self.idom = self.info.switch
		else:
			self.idom = None

		if self.idom is None:
			self.info = None

class ExclusionInfo(object):
	def __init__(self, switch, dj):
		assert isinstance(switch, ExclusionSwitch), switch
		self.switch = switch
		self.dj     = dj
		self.mask   = set()

	def simplify(self):
		while self.switch and self.switch.completeMask(self.mask):
			info = self.switch.info
			if info is not None:
				self.switch = info.switch
				self.mask   = info.mask
			else:
				self.switch = None
				self.mask   = None

	def __repr__(self):
		return "exinfo(%r, %r)" % (self.switch, sorted(self.mask))


class ExclusionGraphBuilder(object):
	def __init__(self, forwardCallback, exclusionCallback):
		self.exgraph = ExclusionGraph()
		self.switches = {}
		self.exInfo   = self.exgraph.exInfo

		self.forwardCallback = forwardCallback
		self.exclusionCallback = exclusionCallback

	def isExclusionSwitch(self, dj):
		return dj in self.switches

	def identifyExclusionSwitch(self, dj):
		# Must be a potentially exclusive node
		if self.exclusionCallback(dj.node):
			# Must have multiple children
			children = set(self.forwardCallback(dj.node))
			if len(children) > 1:
				# It must dominate at least one of its children
				for d in dj.d:
					if d.node in children:
						return True
		return False

	def collectDJ(self, dj):
		isExclusion = self.identifyExclusionSwitch(dj)

		if self.currentSwitch is not None:
			info = ExclusionInfo(self.currentSwitch, dj)
			self.exInfo[dj.node] = info
		else:
			info = None

		if isExclusion:
			switch = ExclusionSwitch(self.currentSwitch, info, dj)
			self.switches[dj] = switch

			old = self.currentSwitch
			self.currentSwitch = switch

			for child in dj.d: self.collectDJ(child)

			self.currentSwitch = old
		else:
			for child in dj.d: self.collectDJ(child)

	def collect(self, dj):
		self.currentSwitch = None
		self.collectDJ(dj)

	def mark(self, dj, mask, isD=True):
		info = self.exInfo[dj.node]
		diff = mask-info.mask

		if diff:
			info.mask.update(diff)
			if not self.isExclusionSwitch(dj):
				for d in dj.d:
					self.mark(d, diff)

				for j in dj.j:
					if info.switch is self.exgraph.getSwitch(j.node):
						self.mark(j, diff, False)

	def childLUT(self, node):
		lut = {}
		for i, child in enumerate(self.forwardCallback(node)):
			lut[child] = set([i])
		return lut

	def analyize(self):
		for dj, switch in self.switches.iteritems():
			lut = self.childLUT(dj.node)
			switch.lut = lut

			for d in dj.d:
				if d.node in lut:
					self.mark(d, lut[d.node])

	def simplify(self, dj):
		if dj.node in self.exInfo:
			info = self.exInfo[dj.node]
			info.simplify()

			if info.switch is None:
				del self.exInfo[dj.node]

		for d in dj.d:
			self.simplify(d)

	def process(self, djs):
		for dj in djs:
			self.collect(dj)

		self.analyize()

		for dj in djs: self.simplify(dj)
		for switch in self.switches.itervalues(): switch.simplify()

	def dump(self, dj, level):
		indent = '    '*level

		info = self.exInfo[dj.node]

		print '%s%r' % (indent, dj.node)
		if info.switch:
			print '%s%r' % (indent, info.switch)
			print '%s%r' % (indent, info.mask)

		level += 1
		for d in dj.d:
			self.dump(d, level)

def build(roots, forwardCallback, exclusionCallback):
	djs = djtree.make(roots, forwardCallback)
	egb = ExclusionGraphBuilder(forwardCallback, exclusionCallback)
	egb.process(djs)
	return egb.exgraph
