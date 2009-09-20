from util.typedispatch import *
from language.glsl import ast as glsl

class MakeAssign(TypeDispatcher):
	@dispatch(type(None))
	def visitNone(self, dst, src):
		return glsl.Discard(src)
	
	@dispatch(glsl.Local)
	def visitLocal(self, dst, src):
		return glsl.Assign(src, dst)

	@dispatch(glsl.GetSubscript)
	def visitSetSubscript(self, dst, src):
		return glsl.SetSubscript(src, dst.expr, dst.subscript)
	
	@dispatch(glsl.GetAttr)
	def visitGetAttr(self, dst, src):
		return glsl.SetAttr(src, dst.expr, dst.name)

	@dispatch(glsl.Load)
	def visitLoad(self, dst, src):
		return glsl.Store(src, dst.expr, dst.name)

_makeAssign = MakeAssign()

def assign(src, dst):
	return _makeAssign(dst, src)