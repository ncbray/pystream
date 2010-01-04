# A helper class that keeps track of the indentation level, etc.
class PythonOutput(object):
	__slots__ = 'out', 'indent', 'emitedStack'
	def __init__(self, out):
		self.out = out
		self.indent = 0
		self.emitedStack = [False]

	def emitStatement(self, stmt):
		self.out.write('\t'*self.indent)
		self.out.write(stmt)
		self.newline()
		self.emitedStack[-1] = True

	def emitComment(self, text):
		self.emitStatement('# '+str(text))

	def startBlock(self, stmt):
		self.emitStatement(stmt+':')
		self.indent += 1
		self.emitedStack.append(False)

	def endBlock(self):
		if not self.emitedStack[-1]:
			self.emitStatement('pass')
		self.emitedStack.pop()
		self.indent -= 1

	def newline(self):
		self.out.write('\n')
