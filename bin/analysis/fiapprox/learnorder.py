from __future__ import absolute_import

from util.learning.decisiontree import buildTree, buildBaggedTree, buildNullClassifier

from analysis.bdddatalog.relationalIR.interpreter import OutOfTimeError

import collections
import copy
import random

class Trial(object):
	def __init__(self, domains, timing):
		self.position = {}
		for i in range(len(domains)):
			self.position[domains[i]] = i
		self.timing = timing

	def attribute(self, (d0, d1)):
		return cmp(self.position[d0], self.position[d1])

	def classification(self):
		return self.cls

def classify(trials, best, worst):
	return classifyEqualFrequency(trials)


def classifyEqualFrequency(trials):
	bins = len(trials)**0.5
	trials.sort(key=lambda t: t.timing)

	cutoff = int(len(trials)/bins)
	median = len(trials)//2+1
	assert median > cutoff
	
	for t in trials[:cutoff]:
		t.cls = True
		
	for t in trials[cutoff:]:
		t.cls = False

	#return bins, cutoff, trials[median].timing
	return bins, cutoff, trials[cutoff+1].timing*1.1

def runTrials(ce, best):
	domains = ce.builder.prgm.domains.keys()

	attributes = {}
	for i in range(len(domains)):
		for j in range(i+1, len(domains)):
			attributes[(domains[i], domains[j])] = (-1, 1)

	classes = (True, False)

	numIter = 10
	episodes = 40
	tree = buildNullClassifier(classes)
	trials = []

	absoluteBest = 1e9
	absoluteWorst = 0.0

	gbest = best
	limit = 1e9 # HACK
	for i in range(episodes):
		bias = 0.5 if i < episodes-2 else 1.0
		bestTime, worstTime, best = runTrial(ce, tree, trials, numIter, bias, best, limit)
		
		if bestTime < absoluteBest:
			gbest = best

		best = None # HACK only inject on the first iteration.

		absoluteBest = min(absoluteBest, bestTime)
		absoluteWorst = max(absoluteWorst, worstTime)

		bins, bestCount, limit = classify(trials, absoluteBest, absoluteWorst)

		print
		print "GBEST", gbest
		print "RANGE ", bestTime, worstTime
		print "GRANGE", absoluteBest, absoluteWorst
		print "BINS", bins, float(bestCount)/len(trials)
		print "LIMIT", limit

		tree = buildBaggedTree(trials, attributes, classes)

def generateOrdered(domains, porder, count, outp):
	after 	= collections.defaultdict(set)
	before 	= collections.defaultdict(set)


	
	for (l, r), order in porder:
		if order != -1:
			l, r = r, l

		after[l].add(r)
		before[r].add(l)

	# Generate possible starting points.
	inital = []
	initalConflicts = {}
	for d in domains:
		if not d in before:
			inital.append(d)
			initalConflicts[d] = 0
		else:
			initalConflicts[d] = len(before[d])

	assert inital
			
	for i in range(count):
		used = set()
		order = []
		current = set(inital)
		conflicts = copy.copy(initalConflicts)

		while len(order) < len(domains):
			assert current, porder
			choose = random.choice(tuple(current))
			current.remove(choose)
			used.add(choose)
			order.append(choose)

			for next in after[choose]:
				assert conflicts[next] > 0
				conflicts[next] -= 1
				if conflicts[next] == 0:
					current.add(next)
		outp.append(tuple(order))

def generateUncertain(domains, tree, count, bias):

	setSize = count*100

	possible = []

	if True:
		porders = []

		tree.enum([], porders)

		porders = [(attr, (bias-lut[True])**2) for attr, lut in porders]
		porders.sort(key=lambda e: e[1])

		porders = porders[:20]

		orders = []
		for porder in porders:
			generateOrdered(domains, porder[0], setSize/len(porders), orders)

		for d in orders:
			t = Trial(d, -1)
			p = tree.probability(t)[True]
			p = (bias-p)**2
			possible.append((d, p))
	else:
		for i in xrange(setSize):
			random.shuffle(domains)
			d = tuple(domains)
			t = Trial(d, -1)
			p = tree.probability(t)[True]
			p = (bias-p)**2
			
			possible.append((d, p))

	possible.sort(key=lambda e: e[1])

	best = [d for d, p in possible[:count]]

	print "Sutability:", possible[0][1], possible[9][1]

	return best

def runTrial(ce, tree, trials, count, bias, best, limit):

	domains = ce.builder.prgm.domains.keys()


	uncertain = generateUncertain(domains, tree, count, bias)

	if best:
		uncertain.append(best)

	bestTime = 1e9
	worstTime = 0
	best = None


	for domains in uncertain:
		# TODO don't entirely rebuild?
		prgm = ce.makeInterpreter(domains)
		prgm.interp.maximumTime = limit
		#prgm.interp.verbose = True

		try:
			time = prgm.execute()
		except OutOfTimeError, e:
			time = 1e9

		print '.',

		trials.append(Trial(tuple(domains), time))

		if time < bestTime:
			bestTime = time
			best = tuple(domains)

		if time > worstTime:
			worstTime = time

	return bestTime, worstTime, best
