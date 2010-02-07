from . import transform, ssa, expandphi, simplify, structuralanalysis


def evaluateCode(compiler, code):
	g = transform.evaluate(compiler, code)

	ssa.evaluate(compiler, g)
	expandphi.evaluate(compiler, g)
	simplify.evaluate(compiler, g)

	structuralanalysis.evaluate(compiler, g)

	return g.code
