class trace(object):
	"""A context manager that prints a traceback if an exception is raised.  Useful for debugging."""
	__slots__ = 'data'
	def __init__(self, data):
		self.data = data

	def __enter__(self):
		pass

	def __exit__(self, type, value, tb):
		if type is not None:
			print "<TRACE> %r" % (self.data,)
