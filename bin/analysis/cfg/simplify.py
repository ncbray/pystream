from . import killflow, optimize, gc

def evaluate(compiler, g):
	killflow.evaluate(compiler, g)
	optimize.evaluate(compiler, g)
	gc.evaluate(compiler, g)
