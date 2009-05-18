class PythonShader(object):
	def __init__(self, code):
		self.code     = code

		self.localToPath  = {}
		self.pathToLocal  = {}

		self.frequency = {}