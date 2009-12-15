from functools import wraps

def conditional(cond, func):
	if cond:
		return func
	else:
		def passthroughTemp(func):
			return func
		return passthroughTemp		


# Decorator that starts a debugger if an exception is thrown
def debugOnFailiure(func):
	@wraps(func)
	def debugOnFailiureDecorator(*args, **kargs):
		try:
			return func(*args, **kargs)
		except:
			import traceback
			traceback.print_exc()

			try:
				import pdb
				pdb.post_mortem()
			except Exception, e:
				print "Cannot start debugger: " + str(e)

			raise
	return debugOnFailiureDecorator


def conditionalDebugOnFailiure(cond):
	return conditional(cond, debugOnFailiure)
