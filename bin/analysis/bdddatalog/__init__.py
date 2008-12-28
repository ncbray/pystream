from . import datalogIR
from . import relationalIR

def makeProgramDescription(algorithim):
	ast = datalogIR.parseAlgorithim(algorithim)
	prgm = relationalIR.relationalFromDatalog(ast)
	return prgm
	
def makeInterpreter(prgm, bindings):
	assert isinstance(prgm, relationalIR.relationalast.Program), type(prgm)
	
	interp = relationalIR.interpreterFromRelational(prgm, bindings)
	return interp

def compileAlgorithim(algorithim, bindings):
	prgm = makeProgramDescription(algorithim)
	interp = makeInterpreter(prgm, bindings)
	return interp
