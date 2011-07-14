# Copyright 2011 Nicholas Bray
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from util.typedispatch import *
from language.chameleon import ast, cfg

from . dfs import CFGDFS

from . import simplify

def memoizeMethod(getter):
	def memodecorator(func):
		def memowrap(self, *args):
			cache = getter(self)
			if args not in cache:
				result = func(self, *args)
				cache[args] = result
			else:
				result = cache[args]
			return result
		return memowrap
	return memodecorator

class ASTCloner(TypeDispatcher):
	def __init__(self, origin):
		self.origin = origin
		self.cache = {}

	def adjustOrigin(self, node):
		origin = node.annotation.origin
		if origin is None:
			origin = [None]
		node.rewriteAnnotation(origin=self.origin + origin)
		return node

	@dispatch(str, type(None))
	def visitLeaf(self, node):
		return node

	@dispatch(ast.Local)
	@memoizeMethod(lambda self: self.cache)
	def visitLocal(self, node):
		result = ast.Local(self(node.type), node.name)
		result.annotation = node.annotation
		return self.adjustOrigin(result)

	@dispatch(ast.Existing)
	def visitExisting(self, node):
		return node.clone()

	@dispatch(ast.Assign, ast.Discard, ast.AugmentedAssign,
			  ast.Special, ast.BinaryOp, ast.Call, ast.Phi)
	def visitOK(self, node):
		return self.adjustOrigin(node.rewriteChildren(self))

class CFGClonerPre(TypeDispatcher):
	def __init__(self, astcloner):
		self.astcloner = astcloner
		self.cache = {}

	@dispatch(cfg.Entry, cfg.Exit, cfg.Yield)
	def visitEntry(self, node):
		return type(node)()

	@dispatch(cfg.Merge)
	def visitMerge(self, node):
		merge = cfg.Merge()

		merge.phi = [self.astcloner(phi) for phi in node.phi]

		return merge

	@dispatch(cfg.Switch)
	def visitSwitch(self, node):
		return cfg.Switch(self.astcloner(node.condition))

	@dispatch(cfg.Suite)
	def visitSuite(self, node):
		suite = cfg.Suite()
		for op in node.ops:
			suite.ops.append(self.astcloner(op))
		return suite

	def __call__(self, node):
		self.cache[node] = TypeDispatcher.__call__(self, node)


class CFGClonerPost(TypeDispatcher):

	@defaultdispatch
	def visitEntry(self, node):
		replace = self.cache[node]

		for name, next in node.next.iteritems():
			replace.clonedExit(name, self.cache[next])

		for prev, name in node.iterprev():
			replace.clonedPrev(self.cache[prev], name)


class CFGCloner(object):
	def __init__(self, origin):
		self.cloner = CFGDFS(CFGClonerPre(ASTCloner(origin)), CFGClonerPost())
		self.cloner.post.cache = self.cloner.pre.cache
		self.cfgCache   = self.cloner.pre.cache

		self.lcl = self.cloner.pre.astcloner

	def process(self, g):
		self.cloner.process(g.entryTerminal)

		newG = cfg.Code()

		# HACK create an empty behavior?
		newG.code = ast.BehaviorDecl(g.code.name+'_clone', [self.lcl(p) for p in g.code.params], g.code.returnType, ast.Suite([]))

		newG.returnParam = self.lcl(g.returnParam)

		newG.entryTerminal  = self.cfgCache[g.entryTerminal]
		newG.normalTerminal = self.cfgCache.get(g.normalTerminal, newG.normalTerminal)
		newG.failTerminal   = self.cfgCache.get(g.failTerminal, newG.failTerminal)
		newG.errorTerminal  = self.cfgCache.get(g.errorTerminal, newG.errorTerminal)

		return newG

class InlineTransform(TypeDispatcher):
	def __init__(self, compiler, g, lut):
		self.compiler = compiler
		self.g = g
		self.lut = lut

	@dispatch(cfg.Entry, cfg.Exit, cfg.Merge, cfg.Yield)
	def visitOK(self, node):
		pass

	@dispatch(cfg.Switch)
	def visitSwitch(self, node):
		pass

	@dispatch(cfg.Suite)
	def visitSuite(self, node):
		failTerminal  = cfg.Merge() if node.getExit('fail') else None
		errorTerminal = cfg.Merge() if node.getExit('error') else None

		def makeSuite():
			suite = cfg.Suite()
			suite.setExit('fail', failTerminal)
			suite.setExit('error', errorTerminal)
			return suite

		head = makeSuite()
		current = head

		inlined = False

		for op in node.ops:
			invokes = self.getInline(op)
			if invokes is not None:
				inlined = True

				call = op.expr

				cloner = CFGCloner(call.annotation.origin)
				cloned = cloner.process(invokes)

				print "\t", invokes.code.name

				# PREAMBLE, evaluate arguments
				for p, a in zip(cloned.code.params, call.arguments):
					current.ops.append(ast.Assign(p, a))

				# Connect into the cloned code
				current.transferExit('normal', cloned.entryTerminal, 'entry')
				current.simplify()

				cloned.failTerminal.redirectEntries(failTerminal)
				cloned.errorTerminal.redirectEntries(errorTerminal)

				# Connect the normal output
				if cloned.normalTerminal.prev:
					current = makeSuite()
					cloned.normalTerminal.redirectEntries(current)
				else:
					current = None
					break


				# POSTAMBLE transfer the return value
				if isinstance(op, ast.Assign):
					current.ops.append(ast.Assign(op.target, cloned.returnParam))
				elif isinstance(op, ast.AugmentedAssign):
					current.ops.append(ast.AugmentedAssign(op.target, op.op, cloned.returnParam))
			else:
				current.ops.append(op)


		if inlined:
			# Inlining was performed, commit changes
			node.redirectEntries(head)

			# Redirect the outputs
			if current:
				if node.getExit('normal'):
					current.transferExit('normal', node, 'normal')
				current.simplify()

			if node.getExit('fail'):
				failTerminal.transferExit('normal', node, 'fail')
				failTerminal.simplify()

			if node.getExit('error'):
				errorTerminal.transferExit('normal', node, 'error')
				errorTerminal.simplify()

	def getInline(self, stmt):
		if isinstance(stmt, (ast.Assign, ast.Discard, ast.AugmentedAssign)):
			expr = stmt.expr
			if isinstance(expr, ast.Call):
				expr = expr.expr
				if isinstance(expr, ast.Existing):
					if expr.object.data in self.lut:
						return self.lut[expr.object.data]

		return None

def evaluate(compiler, g, lut):
	transform = CFGDFS(post=InlineTransform(compiler, g, lut))
	transform.process(g.entryTerminal)
	simplify.evaluate(compiler, g)
