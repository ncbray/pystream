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

class Domain(object):
	__slots__ = 'name', 'values'
	def __init__(self, name, values):
		self.name = name
		self.values = set(values)

	def __repr__(self):
		return "Domain(%s)" % self.name

class ClassifierLeaf(object):
	def __init__(self, value):
		self.value = value

	def best(self, var, value):
		return self.value # HACK, should be zero outside known domain?

	def maximum(self):
		return self.value

	def specialize(self, var, value):
		return self

	def evaluate(self, solution):
		return self.value

class ClassifierNode(object):
	def __init__(self, domain, tree):
		self.domain = domain
		self.tree = tree

	def best(self, var, value):
		if var == self.domain:
			if value in self.tree:
				return self.tree[value].maximum()
			else:
				return 0.0
		else:
			# Keep looking for best?
			best = 0.0
			for v in self.tree.itervalues():
				best = max(best, v.best(var, value))
			return best

	def maximum(self):
		best = 0.0
		for v in self.tree.itervalues():
			best = max(best, v.maximum())
		return best

	def specialize(self, var, value):
		if self.domain == var:
			return self.tree[value]
		else:
			newtree = {}
			for k, v in self.tree.iteritems():
				newtree[k] = v.specialize(var, value)
			return ClassifierNode(self.domain, newtree)

	def evaluate(self, solution):
		assert self.domain in solution
		value = solution[self.domain]

		if value in self.tree:
			return self.tree[value].evaluate(solution)
		else:
			return 0.0



def classifier(domains, tree):
	if domains:
		var = domains[0]
		rest = domains[1:]

		newtree = {}
		for k, v in tree.iteritems():
			newtree[k] = classifier(rest, v)

		for value in var.values:
			if not value in newtree:
				newtree[value] = ClassifierLeaf(0.0)

		return ClassifierNode(var, newtree)
	else:
		assert isinstance(tree, float)
		return ClassifierLeaf(tree)

class FuzzyConstraint(object):
	def __init__(self, classifier):
		self.classifier = classifier
		self.stack = []

	def difficulty(self, var):
		d = 0.0
		for v in var.values:
			d += self.classifier.best(var, v)
		return d

	def best(self, var, value):
		return self.classifier.best(var, value)

	def specialize(self, var, value):
		return FuzzyConstraint(self.classifier.specialize(var, value))

	def evaluate(self, solution):
		return self.classifier.evaluate(solution)

def constraint(domains, tree):
	return FuzzyConstraint(classifier(domains, tree))


def cost(diffs, N):
	return sum(diffs)/N
	#return min(diffs)


class FCSPSolver(object):
	def __init__(self):
		f = Domain('f', ('S', 'C'))
		t = Domain('t', ('D', 'B', 'G'))
		s = Domain('s', ('L', 'W'))

		c1 = constraint((f, t), {'S':{'D':1.0, 'B':0.4, 'G':0.2}, 'C':{'G':0.8,'B':0.5}})
		c2 = constraint((f, s), {'S':{'L':1.0, 'W':0.7}, 'C':{'W':1.0,'L':0.1}})
		c3 = constraint((t, s), {'D':{'W':1.0, 'L':0.7}, 'B':{'W':1.0, 'L':0.4}, 'G':{'L':1.0, 'W':0.6},})


		self.domains = set([f, t, s])
		self.constraints = (c1, c2, c3)


		self.bestScore = 0.0
		self.solution = {}
		self.score = 0.0

	def cost(self, var, value):
		return cost([c.best(var, value) for c in self.constraints], len(self.constraints))


	def findMostDifficult(self):
		if len(self.domains) == 1:
			return tuple(self.domains)[0]

		worstDiff = 1e20
		worst = None
		for d in self.domains:
			diff = [c.difficulty(d) for c in self.constraints]
			diff = filter(lambda i: i>0.0, diff)
			diff = cost(diff, len(self.constraints))
			print d.name, diff

			if diff < worstDiff:
				worst = d
				worstDiff = diff
		print

		return worst

	def findBest(self, var):
		scores = []

		for value in var.values:
			# Generate an optimistic cost.
			cc = self.cost(var, value)
			scores.append((value, cc))
			print value, cc

		# Check highest scores first.
		scores.sort(key=lambda e: e[1], reverse=True)

		return scores


	def execute(self):
		if self.domains:
			var = self.findMostDifficult()


			assert var in self.domains
			self.domains.remove(var)


			self.solution[var] = None

			for value, score in self.findBest(var):
				# Bound the exploration.
				if score <= self.bestScore:
					break

				print "Choose", var.name, value

				self.solution[var] = value
				self.score = score


				old = self.constraints
				self.constraints = [c.specialize(var, value) for c in self.constraints]
				self.execute()
				self.constraints = old

			del self.solution[var]
			self.domains.add(var)

		else:
			print self.solution, self.score
			if self.score > self.bestScore:
				self.bestScore = self.score


##	def spam(self):
##		if self.domains:
##			var = list(self.domains)[0]
##
##			self.domains.remove(var)
##
##			for value in var.values:
##				self.solution[var] = value
##				self.spam()
##
##
##			del self.solution[var]
##			self.domains.add(var)
##		else:
##			print self.solution
##			print cost([c.evaluate(self.solution) for c in self.constraints], len(self.constraints))
##			print


s = FCSPSolver()
#s.spam()
s.execute()
