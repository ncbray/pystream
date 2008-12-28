from util import dot
import collections

from util.visitor import StandardVisitor

import os.path

import config

class FlowBlockDump(StandardVisitor):
	def process(self, name, root):
		self.processed = set()
		self.queue = collections.deque()
		self.regiongraph = {}		

		self.g = dot.Digraph(compound='true')

		self.enqueue(root)

		while self.queue:
			block = self.queue.popleft()
			self.walk(block)

		dot.createGraphic(self.g, os.path.join(config.outputDirectory, name))

	def makeNode(self, block, style):
		sg = self.getCluster(block)
		sg.node(block, **style)

	def makeEdge(self, a, b, style={}):

##		if a and b: # HACK
			assert a and b, (a, b)
			
			self.g.edge(a, b, **style)
			self.enqueue(b)
##		else:
##			print "WARNING: edge", a, b, "does not exist."

	def instructionStyle(self, label, marked):
		d = {'label':label, 'shape':'box'}

		if marked:
			d['color']='red'


		return d

	def flowStyle(self, label, marked):
		d = {'label':label}
		if marked:
			d['color']='red'

		return d

	def pointStyle(self, block):
		d = {'shape':'point'}

		if block.marked:
			d['color']='red'


		return d

	def labeledEdge(self, label):
		return {'label':label}

	def clusterEdge(self, cluster, label):
		return {'label':label, 'ltail':cluster.name}

	def visitFunction(self, block):
		self.makeNode(block, self.flowStyle('function', block.marked))
		self.enqueue(block.entry())

	def visitLoopRegion(self, block):
		self.makeNode(block, self.flowStyle('loop', block.marked))
		self.enqueue(block.entry())
		if block.normal: self.makeEdge(block, block.normal)
		self.makeEdge(block, block.exceptional, self.labeledEdge('break'))


	def visitFinallyRegion(self, block):
		self.makeNode(block, self.flowStyle('finally', block.marked))
		self.enqueue(block.entry())
		if block.normal: self.makeEdge(block, block.normal)
		self.makeEdge(block, block.exceptional, self.labeledEdge('finally'))

	def visitExceptRegion(self, block):
		self.makeNode(block, self.flowStyle('except', block.marked))
		self.enqueue(block.entry())
		if block.normal: self.makeEdge(block, block.normal)
		self.makeEdge(block, block.exceptional, self.labeledEdge('except'))

		
	def visitLinear(self, block):
		label = '\n'.join((inst.opcodeString() for inst in block.instructions))
		self.makeNode(block, self.instructionStyle(label, block.marked))
		self.makeEdge(block, block.next)

	def visitEndFinally(self, block):
		self.makeNode(block, self.instructionStyle('end finally', block.marked))
		if block.next: self.makeEdge(block, block.next)

	def visitSwitchRegion(self, block):
		self.makeNode(block, self.flowStyle(block.name, block.marked))
		self.enqueue(block.entry())
		if block.next: self.makeEdge(block, block.next)


	def visitLoopElse(self, block):
		self.makeNode(block, self.flowStyle(block.name, block.marked))
		self.enqueue(block.entry())
		if block.next: self.makeEdge(block, block.next)


	def visitTryFinally(self, block):
		self.makeNode(block, self.flowStyle(block.name, block.marked))
		self.enqueue(block.entry())
		if block.next: self.makeEdge(block, block.next)

	def visitTryExcept(self, block):
		self.makeNode(block, self.flowStyle(block.name, block.marked))
		self.enqueue(block.entry())
		if block.next: self.makeEdge(block, block.next)

	def visitSuiteRegion(self, block):
		self.makeNode(block, self.flowStyle(block.name, block.marked))
		self.enqueue(block.entry())
		if block.next: self.makeEdge(block, block.next)

	def visitForLoop(self, block):
		self.makeNode(block, self.flowStyle(block.name, block.marked))
		self.enqueue(block.entry())
		if block.next: self.makeEdge(block, block.next)

	def visitWhileLoop(self, block):
		self.makeNode(block, self.flowStyle(block.name, block.marked))
		self.enqueue(block.entry())
		if block.next: self.makeEdge(block, block.next)


	def visitNormalEntry(self, block):
		self.makeNode(block, self.pointStyle(block))
		if block.next: self.makeEdge(block, block.next)

	def visitNormalExit(self, block):
		self.makeNode(block, self.pointStyle(block))

	def visitExceptionalExit(self, block):
		if block.next: # No exceptional exit for functions?
			self.makeNode(block, self.instructionStyle('exceptional exit', block.marked))
			self.makeEdge(block, block.next)

	def visitMerge(self, block):
		self.makeNode(block, self.pointStyle(block))
		self.makeEdge(block, block.next)

	def visitReturn(self, block):
		self.makeNode(block, self.instructionStyle('return', block.marked))

	def visitBreak(self, block):
		self.makeNode(block, self.instructionStyle('break', block.marked))

	def visitContinue(self, block):
		self.makeNode(block, self.instructionStyle('continue', block.marked))


	def visitRaise(self, block):
		self.makeNode(block, self.instructionStyle('raise %d' % block.nargs, block.marked))


	def visitForIter(self, block):
		self.makeNode(block, self.flowStyle('for iter', block.marked))
		self.makeEdge(block, block.iter, self.labeledEdge('iter'))
		self.makeEdge(block, block.done, self.labeledEdge('done'))

	def visitSwitch(self, block):
		#self.enqueue(block.cond)
		self.makeNode(block, self.pointStyle(block))
		self.makeEdge(block, block.t, self.labeledEdge('t'))
		self.makeEdge(block, block.f, self.labeledEdge('f'))

	def visitShortCircutAnd(self, block):
		self.makeNode(block, self.pointStyle(block))

		for term in block.terms:
			self.makeEdge(block, term)
			self.enqueue(term)


	def visitShortCircutOr(self, block):
		self.makeNode(block, self.pointStyle(block))

		for term in block.terms:
			self.makeEdge(block, term)
			self.enqueue(term)

	def visitCheckStack(self, block):
		self.makeNode(block, self.pointStyle(block))

	def processBlock(self, block):
		label = ''

		ib = block.subgraph
		for i in ib.instructions:
			label += str(i)+'\n'

		self.makeNode(block, label)

		# Add edges
		if hasattr(block, 'exit'):
			exits = block.exit.getExits()
			for e in exits:
				self.makeEdge(block, e)

	def enqueue(self, block):
		if not block in self.processed:
			self.processed.add(block)
			self.queue.append(block)

	def getCluster(self, block):
		return self.getSubgraph(block.region)

	def getSubgraph(self, region):
		if not region:
			return self.g
		else:
			if not region in self.regiongraph:
				self.regiongraph[region] = None
				parent = self.getSubgraph(region.region)

				assert parent, ("Recursive regions?", region, region.region)

				attr = {'label':type(region).__name__ + " - " + hex(id(region))}

				if region.marked:
					attr['color'] = 'red'
				
				self.regiongraph[region] = parent.cluster(region, **attr)
			return self.regiongraph[region]
