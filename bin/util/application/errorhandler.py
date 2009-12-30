from . import compilerexceptions

from util.debug.blame import traceBlame

class ErrorScopeManager(object):
	__slots__ = 'handler'
	
	def __init__(self, handler):
		self.handler = handler

	def __enter__(self):
		self.handler._push()

	def __exit__(self, type, value, tb):
                self.handler._pop()

class ShowStatusManager(object):
	__slots__ = 'handler'
	
	def __init__(self, handler):
		self.handler = handler

	def __enter__(self):
                pass

	def __exit__(self, type, value, tb):
                self.handler.flush()

                if type is not None:
                        print
                        print "Compilation Aborted -", self.handler.statusString()
                else:
                        print
                        print "Compilation Successful -", self.handler.statusString()

                
                return type is compilerexceptions.CompilerAbort

class ErrorHandler(object):
	def __init__(self):
                self.stack = []
                
		self.errorCount  = 0
		self.warningCount = 0

                self.defered = True
                self.buffer = []

                self.showBlame = False

	def blame(self):
                if self.showBlame:
                        return traceBlame(3, 5)
                else:
                        return None

	def error(self, classification, message, trace):
                blame = self.blame()
                if self.defered:
                        self.buffer.append((classification, message, trace, blame))
                else:
                        self.displayError(classification, message, trace, blame)
		self.errorCount += 1

	def warn(self, classification, message, trace):
                blame = self.blame()
                if self.defered:
                        self.buffer.append((classification, message, trace, blame))
                else:
        		self.displayError(classification, message, trace, blame)
		self.warningCount += 1

	def displayError(self, classification, message, trace, blame):
		print
		print "%s: %s" % (classification, message)
		for origin in trace:
			if origin is None:
				print "<unknown origin>"
			else:
				print origin.originString()

		if blame:
        		print "BLAME"
                        for line in blame:
                		print line

        def statusString(self):
                return "%d errors, %d warnings" % (self.errorCount, self.warningCount)

	def finalize(self):
		if self.errorCount > 0:	
			raise compilerexceptions.CompilerAbort

        def flush(self):
                for cls, msg, trace, blame in self.buffer:
                        self.displayError(cls, msg, trace, blame)
                self.buffer = []

        def _push(self):
                self.stack.append((self.errorCount, self.warningCount))
                self.errorCount = 0
                self.warningCount = 0

        def _pop(self):
                errorCount, warningCount = self.stack.pop()
                self.errorCount   += errorCount
                self.warningCount += warningCount

        def scope(self):
                return ErrorScopeManager(self)

        def statusManager(self):
                return ShowStatusManager(self)
