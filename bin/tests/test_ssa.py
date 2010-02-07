import unittest

from util.asttools.astpprint import pprint

from application import context

from decompiler.programextractor import Extractor

from analysis.cfg import transform, dump, ssa, expandphi, simplify, structuralanalysis

from language.python.simplecodegen import SimpleCodeGen

def split(a, b):
	c = a
	if a:
		d = b
	else:
		d = -b
	return c, d

def doubleSplit(s, t):
	a = 1

	if s:
		if t:
			a = 2
		else:
			a = 3
	return a

def loop(a, b):
	count = 0

	while a:
		a -= 1
		count += 1
		reduceC = count/2

		if b:
			break
	else:
		reduceC += 1

	return reduceC

def dloop():
	count = 0

	while True:
		if count%7:
			break
		count += 1

	return count

#def parallax(self, e, texCoord, nm, amount):
#		tse = self.tangentSpaceEye(e)
#
#		nSteps = 16
#		dir = tse.xy/(nSteps*tse.z*8.0)
#		stepDepth = 1.0/(nSteps)
#
#		depth = 1.0
#		diff0 = depth-nm.texture(texCoord).w
#		diff1 = diff0
#
#		offset = vec2(0.5)
#		backtrack = 0.5
#
#		if diff1 > 0.0:
#			while diff1 > 0.0:
#				texCoord += dir
#				offset += dir
#				depth -= stepDepth
#
#				diff0 = diff1
#				diff1 = depth-nm.texture(texCoord).w
#
#			backtrack = diff1/(diff0 - diff1)
#			offset +=  dir*backtrack
#
#		return texCoord, vec3(backtrack, -backtrack, 0.0)

def parallax(tse, td):
		stepDepth = 1.0/16.0
		depth = 1.0

		while depth > 0.0:
			depth -= stepDepth

		return depth

def psimp(a):
	if a > 0:
		while a > 0:
			a -= 1
	return a

class TestSSA(unittest.TestCase):
	def setUp(self):
		self.compiler = context.CompilerContext(None)
		self.compiler.extractor = Extractor(self.compiler)

	def decompile(self, func):
		return self.compiler.extractor.decompileFunction(func, ssa=False)

	def runFunction(self, func, trace=False):
		code = self.decompile(func)

		if trace:
			#pprint(code)
			SimpleCodeGen(None).process(code)


		g = transform.evaluate(self.compiler, code)


		ssa.evaluate(self.compiler, g)
		expandphi.evaluate(self.compiler, g)
		simplify.evaluate(self.compiler, g)



		structuralanalysis.evaluate(self.compiler, g)

		if trace:
			dump.evaluate(self.compiler, g)


		if trace:
			#pprint(code)
			SimpleCodeGen(None).process(code)

			#dump.evaluate(self.compiler, g)


	def testSplit(self):
		self.runFunction(split)

	def testDoubleSplit(self):
		self.runFunction(doubleSplit)

	def testLoop(self):
		self.runFunction(loop)

	def testDLoop(self):
		self.runFunction(dloop)

	def testParallax(self):
		self.runFunction(parallax)


	def testPSimp(self):
		self.runFunction(psimp)
