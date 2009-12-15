import sys
import time
from util.io import formatting

class Scope(object):
	def __init__(self, parent, name):
		self.parent   = parent
		self.name     = name
		self.children = []

	def begin(self):
		self._start = time.clock()

	def end(self):
		self._end = time.clock()

	@property
	def elapsed(self):
		return self._end-self._start

	def path(self):
		if self.parent is None:
			return ()
		else:
			return self.parent.path()+(self.name,)

	def child(self, name):
		return Scope(self, name)


class ConsoleScopeManager(object):
	__slots__ = 'console', 'name'
	def __init__(self, console, name):
		self.console = console
		self.name = name

	def __enter__(self):
		self.console.begin(self.name)

	def __exit__(self, type, value, tb):
		self.console.end()

class Console(object):
	def __init__(self, out=None):
		if out is None:
			out = sys.stdout
		self.out = out

		self.root = Scope(None, 'root')
		self.current = self.root

		self.blameOutput  = False

	def path(self):
		return "[ %s ]" % " | ".join(self.current.path())

	def begin(self, name):
		scope = self.current.child(name)
		scope.begin()
		self.current = scope

		self.output("begin %s" % self.path(), 0)

	def end(self):
		self.current.end()
		self.output("end   %s %s" % (self.path(), formatting.elapsedTime(self.current.elapsed)), 0)
		self.current = self.current.parent

	def scope(self, name):
		return ConsoleScopeManager(self, name)

	def blame(self):
		caller = sys._getframe(2)
		globals = caller.f_globals
		lineno = caller.f_lineno

		#filename = globals.get('__file__')
		filename = caller.f_code.co_filename

		del caller # Destroy a circular reference

		return "%s:%d" % (filename, lineno)

	def output(self, s, tabs=1):
		if tabs:
			self.out.write('\t'*tabs)

		if self.blameOutput and tabs:
			self.out.write(self.blame()+" ")


		self.out.write(s)
		self.out.write('\n')
