import math
import random
import collections

chisquared99 = [0.0, 0.000157, 0.0201, 0.115, 0.297, 0.554, 0.872, 1.239, 1.646, 2.088, 2.558]


class DecisionTreeNode(object):
	def __init__(self, attribute, lut):
		self.attribute = attribute
		self.lut = lut

	def dump(self, indent=''):
		print indent+str(self.attribute)
		for k, v in self.lut.iteritems():
			print indent+str(k)
			v.dump(indent+'\t')

	def classify(self, example):
		a = example.attribute(self.attribute)
		assert a in self.lut
		return self.lut[a].classify(example)

	def probability(self, example):
		a = example.attribute(self.attribute)
		assert a in self.lut
		return self.lut[a].probability(example)

	def enum(self, attr, l):
		for k, v in self.lut.iteritems():
			attr.append((self.attribute, k))
			v.enum(attr, l)
			attr.pop()

def mostProbable(lut):
	bestCls = None
	bestProb = -1.0
	for cls, prob in lut.iteritems():
		assert prob >= 0.0
		if prob > bestProb:
			bestCls = cls
			bestProb = prob
	return bestCls

class DecisionTreeLeaf(object):
	def __init__(self, lut):
		assert len(lut) > 0
		self.lut = lut
		self.mostLikely = mostProbable(lut)

	def dump(self, indent=''):
		for cls, prob in self.lut.iteritems():
			print '%s%s : %.2f' % (indent, str(cls), prob)

	def classify(self, example):
		return self.mostLikely

	def probability(self, example):
		return self.lut

	def enum(self, attr, l):
		l.append((tuple(attr), self.lut))

class BaggedClassifier(object):
	def __init__(self, bags):
		self.bags = bags

	def probability(self, example):
		scale = 1.0/len(self.bags)
		p = collections.defaultdict(lambda: 0.0)
		for bag in self.bags:
			newp = bag.probability(example)

			# Vote
			#p[mostProbable(newp)] += scale

			# Average
			for k, v in newp.iteritems():
				p[k] += v*scale

		return p

	def enum(self, attr, l):
		for bag in self.bags:
			bag.enum(attr, l)

def buildNullClassifier(classes):
	return makeLeaf({}, 0, classes)

def binByAttributes(partition, attributes):
	bins = {}
	for attr in attributes.iterkeys():
		bins[attr] = {}

		for trial in partition:
			value = trial.attribute(attr)

			if not value in bins[attr]:
				bins[attr][value] = set()
			bins[attr][value].add(trial)
	return bins

def countClassifications(partition):
	clsCount = {}

	for trial in partition:
		cls = trial.classification()
		if not cls in clsCount:
			clsCount[cls] = 1
		else:
			clsCount[cls] += 1

	return clsCount

def information(partition):
	clsCount = countClassifications(partition)

	totalCount = len(partition)
	info = 0.0

	for cls, count in clsCount.iteritems():
		ratio = float(count)/totalCount
		info -= ratio*math.log(ratio, 2)

	return info


def makeLeaf(Nk, N, classes):
	laplaceWeight = 1.0
	scale = 1.0/(N+len(classes)*laplaceWeight)

	lut = {}
	for cls in classes:
		count = Nk.get(cls, 0)
		# Calculate probability, with Laplace correction.
		lut[cls] = (count+laplaceWeight)*scale

	return DecisionTreeLeaf(lut)

def significance(clsCount, clsCount0, weight):
	norm = 0.0
	for cls in clsCount0.keys():
		expected = clsCount0[cls]*weight
		actual = clsCount.get(cls, 0)
		norm += ((actual-expected)**2)/expected

	return norm

def findBestAttribute(bins, attributes, clsCount0, size0, original):
	if original <= 0.0:
		return None

	bestAttribute = None
	bestGain = 0.0

	for i in attributes.iterkeys():
		bin = bins[i]

		chi2 = 0.0
		e = 0.0
		iv = 0.0
		for attr, subpartition in bin.iteritems():
			if subpartition:
				clsCount = countClassifications(subpartition)
				weight = float(len(subpartition))/size0

				# Calcuate out confidence that this attribute is significant.
				chi2 += significance(clsCount, clsCount0, weight)

				# Calculate the expected information after partitioning
				e += weight*information(subpartition)

				# Information value
				iv -= weight*math.log(weight, 2.0)

		# Pruning
		accept = chisquared99[len(bin)-1] < chi2

		#accept = True

		if accept:
			# Find the attribute with the best information gain.
			gain = (original - e)/max(iv, 0.0000001) # Gain ratio

			if gain > bestGain:
				bestGain = gain
				bestAttribute = i

	return bestAttribute

def buildTree(partition, attributes, classes):
	assert len(classes) >= 2

	bins = binByAttributes(partition, attributes)
	clsCount0 = countClassifications(partition)
	size0 = float(len(partition))


	original = information(partition)

	bestAttribute = findBestAttribute(bins, attributes, clsCount0, size0, original)

	default = makeLeaf(clsCount0, size0, classes)

	if bestAttribute != None:
		lut = {}
		# TODO undefined attribute?
		domain = attributes[bestAttribute]

		attrbin = bins[bestAttribute]
		for value in domain:
			if value in attrbin:
				bin = attrbin[value]
				lut[value] = buildTree(bin, attributes, classes)
			else:
				# If we don't have an example, use the default example.
				lut[value] = default
		return DecisionTreeNode(bestAttribute, lut)
	else:
		return default

def bootstrapSample(trials):
	return [random.choice(trials) for i in xrange(len(trials))]


def buildBaggedTree(partition, attributes, classes):
	numBags = 10

	bags = [buildTree(bootstrapSample(partition), attributes, classes) for i in range(numBags)]

	return BaggedClassifier(bags)


if __name__ == '__main__':
	class Trial(object):
		def __init__(self, data, c):
			self.data = data
			self.cls = c


		def classification(self):
			return self.cls

		def attribute(self, index):
			if index >= 0 and index < len(self.data):
				return self.data[index]
			else:
				return None
		def __repr__(self):
			return repr(self.data)


	trials = []

	trials.append(Trial(('sunny', 'hot', 'high', 'false'), 'n'))
	#trials.append(Trial(('overcast', 'hot', 'high', 'false'), 'n'))

	trials.append(Trial(('sunny', 'hot', 'high', 'true'), 'n'))

	trials.append(Trial(('overcast', 'hot', 'high', 'false'), 'p'))
	#trials.append(Trial(('overcast', 'hot', 'high', 'false'), 'n'))

	trials.append(Trial(('rain', 'mild', 'high', 'false'), 'p'))
	#trials.append(Trial(('rain', 'mild', 'high', 'true'), 'p'))


	trials.append(Trial(('rain', 'cool', 'normal', 'false'), 'p'))
	trials.append(Trial(('rain', 'cool', 'normal', 'true'), 'n'))
	trials.append(Trial(('overcast', 'cool', 'normal', 'true'), 'p'))

	trials.append(Trial(('sunny', 'mild', 'high', 'false'), 'n'))
	trials.append(Trial(('sunny', 'cool', 'normal', 'false'), 'p'))
	trials.append(Trial(('rain', 'mild', 'normal', 'false'), 'p'))
	trials.append(Trial(('sunny', 'mild', 'normal', 'true'), 'p'))
	trials.append(Trial(('overcast', 'mild', 'high', 'true'), 'p'))
	trials.append(Trial(('overcast', 'hot', 'normal', 'false'), 'p'))
	trials.append(Trial(('rain', 'mild', 'high', 'true'), 'n'))


	#attributes = range(4)

	attributes = {0:('sunny', 'overcast', 'rain'), 1:('hot', 'mild', 'cool'), 2:('high', 'normal'), 3:('true', 'false')}


	classes = ('n', 'p')

	tree = buildBaggedTree(trials, attributes, classes)

	for trial in trials:
		print trial
		print tree.probability(trial)[trial.classification()]
		print

	tree = buildTree(trials, attributes, classes)

	tree.dump()

	for trial in trials:
		assert tree.classify(trial) == trial.classification()
