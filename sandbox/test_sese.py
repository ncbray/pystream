from __future__ import absolute_import
import unittest


from util.graphalgorithim.sese import findCycleEquivalences

def makeGraph(graph):
	if graph == 0:
		G = {'start':(1,), 1:(2, 9), 2:(3,), 3:(4,), 4:(5, 6), 5:(7,), 6:(7,),
		     7:(8,), 8:(2, 16), 9:(10,), 10:(11, 12), 11:(13,), 12:(13,), 13:(14,),
		     14:(12, 15), 15:(16,), 16:('end',), 'end':('start',)}

		head, tail = 1, 16

	elif graph == 1:
		G = {'start':('p',),'p':('xt','xf'),'xt':('a',),'xf':('a',),'a':('b',),
		     'b':('c',),'c':('x',),'x':('d', 'e'),'d':('f',), 'e':('f',),'f':('end',),'end':('start',)}

		head, tail = 'p', 'f'

	elif graph == 2:
		G = {'start':(1,),1:(2, 3), 2:(4,5), 3:(5,7), 4:(6,), 5:(6,), 6:(7,), 7:('end',), 'end':('start',)}
		head, tail = 1, 7

	elif graph == 3:
		G = {'start':(1,),1:(2,), 2:(3,), 3:('end',), 'end':('start',) }
		head, tail = 1, 3
	else:
		assert False, graph

	return G, head, tail

class TestSESE(unittest.TestCase):
	def testSESE0(self):
		G, head, tail = makeGraph(0)
		result = findCycleEquivalences(G, head, tail)
		self.assertEqual(result.entry, head)
		self.assertEqual(result.exit, tail)

		self.assertEqual(set(result.nodes), set((1, 16)))
		self.assertEqual(len(result.children), 4)
		for child in result.children:
			if child.entry == 2:
				self.assertEqual(child.exit, 8)
			elif child.entry == 9:
				self.assertEqual(child.exit, 9)
			elif child.entry == 10:
				self.assertEqual(child.exit, 14)
			elif child.entry == 15:
				self.assertEqual(child.exit, 15)
			else:
				self.fail()

	def testSESE1(self):
		G, head, tail = makeGraph(1)
		result = findCycleEquivalences(G, head, tail)
		self.assertEqual(result.entry, head)
		self.assertEqual(result.exit, tail)

	def testSESE2(self):
		G, head, tail = makeGraph(2)
		result = findCycleEquivalences(G, head, tail)
		self.assertEqual(result.entry, head)
		self.assertEqual(result.exit, tail)

		self.assertEqual(set(result.nodes), set((1, 2, 3, 5, 6, 7)))

		self.assertEqual(len(result.children), 1)
		child = result.children[0]
		self.assertEqual(child.entry, 4)
		self.assertEqual(child.exit, 4)

	def testSESE3(self):
		G, head, tail = makeGraph(3)
		result = findCycleEquivalences(G, head, tail)
		self.assertEqual(result.entry, head)
		self.assertEqual(result.exit, tail)
