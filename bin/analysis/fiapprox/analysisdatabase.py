class BDDAnalysisDatabase(object):
	def __init__(self, prgm):
		self.prgm = prgm
		self.civp = self.prgm.outputs['varPoint'].forget('cv.c', 'ch.c')
		self.ciie = self.prgm.outputs['liveIE'].forget('cb.c', 'cf.c')

	def singleObject(self, local):
		heaps = self.civp.restrict(**{'cv':{'v':local}}).enumerateList()
		# of form: [((obj,),),....]

		if len(heaps) == 1:
			obj = heaps[0][0][0]
			if obj.isPreexisting():
				return obj
		return None

	def singleCall(self, b):
		calls = self.ciie.restrict(**{'cb':{'b':b}}).enumerateList()
		# of form: [((obj,),),....]

		if len(calls) == 1:
			func = calls[0][0][0]
			return func
		return None
