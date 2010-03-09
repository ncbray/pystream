class TemporaryLimitation(Exception):
	pass

class InternalError(Exception):
	pass

class CompilerAbort(Exception):
	pass


def abort(msg=None):
	raise CompilerAbort, msg
