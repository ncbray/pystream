from asttools.origin import originString

class TranslationError(Exception):
	def __init__(self, code, node, reason):
		self.code   = code
		self.node   = node
		self.reason = reason

		trace = '\n'.join([originString(origin) for origin in node.annotation.origin])

		Exception.__init__(self, "\n\n".join([reason, repr(code), trace, repr(node)]))

class TemporaryLimitation(TranslationError):
	pass
