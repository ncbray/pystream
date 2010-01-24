import os.path
from util.io.xmloutput import XMLOutput
from util.io.filesystem import ensureDirectoryExists
from util.graphalgorithim import dominator

from language.python import simplecodegen, ast
import cStringIO

class Dumper(object):
	def __init__(self, directory):
		self.directory = directory
		self.urls = {}
		self.uid  = 0
		ensureDirectoryExists(directory)

	def contextURL(self, context):
		url = self.urls.get(context)
		if url is None:
			url = os.path.join(self.directory, "f%6.6d.html" % self.uid)
			url = url.replace('\\', '/')
			self.uid += 1
			self.urls[context] = url
		return url

	def relLink(self, target, current):
		directory, _file = os.path.split(current)
		link = os.path.relpath(target, directory)
		link = link.replace('\\', '/')
		return link

	def groupInvokes(self, invokes, callback):
		grouped = {}
		for invoke in invokes.itervalues():
			key = callback(invoke)
			if key not in grouped:
				grouped[key] = [invoke]
			else:
				grouped[key].append(invoke)
		return grouped

	def _displayContext(self, context, o):
		o << context.signature.code
		o.tag('br')
		with o.scope('b'):
			o << "self:"
		o << " "
		o << context.signature.selfparam
		o.tag('br')
		for i, param in enumerate(context.signature.params):
			with o.scope('b'):
				o << "param %d:" % i
			o << " "
			o << param
			o.tag('br')
		for i, param in enumerate(context.signature.vparams):
			with o.scope('b'):
				o << "vparam %d:" % i
			o << " "
			o << param
			o.tag('br')


	def displayContext(self, context, o, link=True):
		if link:
			with o.scope('a', href=self.relLink(self.contextURL(context), o.url)):
				self._displayContext(context, o)
		else:
			self._displayContext(context, o)

	def header(self, text, o):
		with o.scope('h3'):
			o << text
		o.endl()

	def code(self, context, o):
		code = context.signature.code
		if code and code.isStandardCode():
			self.header("Code", o)
			sio = cStringIO.StringIO()
			simplecodegen.SimpleCodeGen(sio).process(code)
			with o.scope('pre'):
				o << sio.getvalue()


	def invokesIn(self, context, o):
		self.header("Invoke In", o)

		grouped = self.groupInvokes(context.invokeIn, lambda invoke: invoke.src)
		for src, invokes in grouped.iteritems():
			with o.scope('p'):
				self.displayContext(src, o)
			for invoke in invokes:
				with o.scope('p'):
					o << invoke.op
				self.constraints(invoke.constraints, o)

			o.endl()

	def invokesOut(self, context, o):
		self.header("Invoke Out", o)

		grouped = self.groupInvokes(context.invokeOut, lambda invoke: invoke.op)
		for op, invokes in grouped.iteritems():
			with o.scope('p'):
				o << op
				o.tag('br')
				for invoke in invokes:
					self.displayContext(invoke.dst, o)
					o.tag('br')
			o.endl()

	def locals(self, context, o):
		self.header("Locals", o)
		for slot in context.locals.itervalues():
			with o.scope('p'):
				o << slot
				if slot.null: o << " (null)"
				o.endl()

				with o.scope('ul'):
					for value in slot.values:
						with o.scope('li'):
							o << value
			o.endl()

	def objects(self, context, o):
		self.header("Objects", o)
		region = context.region

		for obj in region.objects.itervalues():
			with o.scope('p'):
				o << obj.name
				o.endl()

				with o.scope('ul'):
					for slot in obj.fields.itervalues():
						with o.scope('li'):
							o << slot
							if slot.null: o << " (null)"
							with o.scope('ul'):
								for value in slot.values:
									with o.scope('li'):
										o << value
							o.endl()
						o.endl()
			o.endl()

	def dumpTree(self, node, tree, o):
		if node not in tree: return

		with o.scope('ul'):
			for child in tree[node]:
				with o.scope('li'):
					self.displayContext(child, o, link=True)
					self.dumpTree(child, tree, o)

	def index(self, contexts, root):
		def forward(context):
			return set([invoke.dst for invoke in context.invokeOut.itervalues()])

		idoms = dominator.findIDoms([root], forward)
		tree = dominator.treeFromIDoms(idoms)

		url = os.path.join(self.directory, 'index.html')
		o = XMLOutput(open(url, 'w'))
		o.url = url

		self.dumpTree(None, tree, o)

	def constraints(self, constraints, o):
		with o.scope('p'):
			with o.scope('b'):
				o << "%d constraints" % len(constraints)
			o.tag('br')
			for c in constraints:
				o << c
				o.tag('br')

	def dumpContext(self, context):
		url = self.contextURL(context)
		o = XMLOutput(open(url, 'w'))
		o.url = url

		with o.scope('html'):
			with o.scope('head'):
				with o.scope('title'):
					o << context.signature.code
					o << ' - '
					o << id(context)
			with o.scope('body'):
				with o.scope('p'):
					o << '['
					with o.scope('a', href='index.html'):
						o << "Index"
					o << ']'
				o.endl()
				with o.scope('p'):
					self.displayContext(context, o, link=False)

				self.code(context, o)
				self.invokesIn(context, o)
				self.invokesOut(context, o)
				self.locals(context, o)
				self.objects(context, o)

				self.constraints(context.constraints, o)
