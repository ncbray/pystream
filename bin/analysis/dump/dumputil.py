from analysis.storegraph import storegraph

class LinkManager(object):
	def __init__(self):
		self.functionFile = {}
		self.objectFile = {}

		self.contextName = {}
		self.cid = 0

	def contextRef(self, context):
		if not context in self.contextName:
			self.contextName[context] = "c%d" % self.cid
			self.cid += 1
			assert context in self.contextName
		return self.contextName[context]

	def objectRef(self, obj):
		context = None
		xtype   = None

		if isinstance(obj, storegraph.ObjectNode):
			context = obj
			xtype   = obj.xtype
			obj     = xtype.obj

		if obj not in self.objectFile: return None

		fn = self.objectFile[obj]

		if context:
			cn = self.contextRef(context)
			fn = "%s#%s" % (fn, cn)

		return fn


	def codeRef(self, code, context):
		if code not in self.functionFile:
			return None

		link = self.functionFile[code]

		if context is not None:
			link = "%s#%s" % (link,  self.contextRef(context))

		return link


def codeShortName(code):
	if isinstance(code, str):
		name = func
		args = []
		vargs = None
		kargs = None
	elif code is None:
		name = 'external'
		args = []
		vargs = None
		kargs = None
	else:
		name = code.codeName()
		callee = code.codeParameters()

		args = [p if p is not None else '!' for p in callee.paramnames]
		vargs = None if callee.vparam is None else callee.vparam.name
		kargs = None if callee.kparam is None else callee.kparam.name

	if vargs is not None: args.append("*"+vargs)
	if kargs is not None: args.append("**"+kargs)

	return "%s(%s)" % (name, ", ".join(args))

def objectShortName(obj):
	if isinstance(obj, storegraph.ObjectNode):
		context = obj
		xtype   = obj.xtype
		obj     = xtype.obj
		return repr(xtype)

	return repr(obj)