import pycudd

def reset():
	global m

	if True:
		m = pycudd.DdManager()
	else:
		nodes = 100000
		cache =  262144

		maxMemory = int(1e9)
		
		m = pycudd.DdManager(0, 0, nodes, cache, 0)

	m.SetDefault()

	m.AutodynDisable()
	#m.EnableGarbageCollection()

reset()

def intarray(data):
	p = pycudd.IntArray(len(data))
	for i in range(len(data)):
		p[i] = data[i]
	return p
