import scriptsetup
scriptsetup.initPsyco()
scriptsetup.libraryDirectory("..//lib")

from util.graphalgorithim.sese import findCycleEquivilences

if __name__ == '__main__':

	graph = 0

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
	
	result = findCycleEquivilences(G, head, tail)
