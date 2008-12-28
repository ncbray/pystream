from base import *


def dynamicScope(dyns):
	def dynamicScopeF(f):
		def dynamicScopeWrap(node):
			for d in dyns:
				d.push()
			try:
				return f(node)
			finally:
				for d in dyns:
					d.pop()
		return dynamicScopeWrap
	return dynamicScopeF


class DynamicFrame(object):
	def __init__(self):
		self.lut = {}

	def define(self, key, value):
		self.lut[key] = [value]

	def define(self, key, value):
		if not key in lut:
			self.lut[key] = [value]
		else:
			self.lut[key].append(value)

	def undef(self, key):
		self.lut[key] = []

	def bag(self, key):
		return self.lut.get(key, ())

	def lookup(self, key):
		bag = self.bag(key)
		if len(bag)==0: raise TransformFailiure
		return bag[-1]
