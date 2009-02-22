from . astcollector import getOps

def codeOps(func):
	ops, lcls = getOps(code)
	return ops

def codeLocals(code):
	ops, lcls = getOps(code)
	return lcls

def codeOpsLocals(code):
	return getOps(code)