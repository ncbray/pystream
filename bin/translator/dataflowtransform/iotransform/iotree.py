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

from ... import intrinsics
from analysis.storegraph.canonicalobjects import FieldSlotName

class IOTreeObj(object):
	def __init__(self, path, impl, treetype, parent=None):
		self.parent   = parent
		self.path     = path
		self.treetype = treetype
		self.objMasks = {}
		self.fields   = {}

		self.builtin  = False
		self.name     = None
		self.impl     = impl

		self.link     = None

	def names(self):
		if self.isField():
			return self.getFieldSlots()
		elif self.impl:
			return (self.impl,)
		else:
			return ()

	def isField(self):
		return isinstance(self.impl, FieldSlotName)

	def getFieldSlots(self):
		assert self.parent
		slots = []
		for obj in self.parent.objMasks.iterkeys():
			if self.impl in obj.slots:
				slots.append(obj.slots[self.impl])
		return slots

	def getField(self, field):
		if not field in self.fields:
			slot = IOTreeObj(self.path + (field,), field, self.treetype, self)
			self.fields[field] = slot
		else:
			slot = self.fields[field]
		return slot

	def match(self, matcher):
		if isinstance(matcher, dict):
			for field, child in self.fields.iteritems():
				key = field.type, field.name

				if key in matcher:
					child.match(matcher[key])
		else:
			self.name = matcher
			self.builtin = True

	def buildImplementationLUT(self, lut):
		if not self.isField() and self.impl:
			assert self.impl not in lut, self.impl
			lut[self.impl] = self

		for child in self.fields.itervalues():
			child.buildImplementationLUT(lut)

	def makeLinks(self, other, uid):
		print "LINK", self.path, other.path

		self.link  = other
		other.link = self

		name = "vs2fs_%d" % uid
		uid += 1

		self.name  = name
		other.name = name

		for field, child in self.fields.iteritems():
			if field in other.fields:
				uid = child.makeLinks(other.fields[field], uid)

		return uid

	def unlink(self):
		if self.link:
			self.link.link = None
			self.link = None

	def localClone(self, parent):
		print "local clone", self.path

		result = IOTreeObj(self.path, self.impl, self.treetype, parent)
		result.name    = self.name
		result.builtin = self.builtin

		for k, v in self.objMasks.iteritems():
			result.objMasks[k] = v

		return result

	def clone(self, parent):
		result = self.localClone(parent)

		for field, child in self.fields.iteritems():
			result.fields[field] = child.clone(result)

		return result

	def merge(self, other, parent):
		result = self.localClone(parent)

		# Wierd: the trees will have entirely different sets of object names!
		for k, v in other.objMasks.iteritems():
			result.objMasks[k] = v

		fields = set()
		fields.update(self.fields.iterkeys())
		fields.update(other.fields.iterkeys())

		for field in fields:
			if field in self.fields and field in other.fields:
				child = self.fields[field].merge(other.fields[field], result)
			elif field in self.fields:
				child = self.fields[field].clone(result)
			else:
				child = other.fields[field].clone(result)

			result.fields[field] = child

		return result

	# Give the tree default names
	def nameTree(self, name, uid=0):
		if not self.name:
			nodename = "%s_%d"  % (name, uid)
			uid += 1

			self.name = nodename

		for child in self.fields.itervalues():
			uid = child.nameTree(name, uid)

		return uid

	# Give matching nodes the same name
	# Used so the corresponding uniforms of two shaders are named the same.
	def harmonize(self, other, name, uid=0):
		nodename = "%s_%d"  % (name, uid)
		uid += 1

		self.name  = nodename
		other.name = nodename

		# Recurse into matching children.
		for field, child in self.fields.iteritems():
			otherchild = other.fields.get(field)
			if otherchild is not None:
				print "HARMONIZE", field
				uid = child.harmonize(otherchild, name, uid)

		return uid

	def _dump(self):
		print self.path
		print self.objMasks

		for next in self.fields.itervalues():
			next._dump()


	def dump(self, name):
		print
		print name
		print self.treetype
		self._dump()
		print

def handleObj(dioa, obj, lut, exist, mask, tobj):
	# Does this field actually exist?
	if mask is dioa.bool.false: return

	# Accumulate the mask
	oldmask = tobj.objMasks.get(obj, dioa.bool.false)
	objmask = dioa.bool.or_(oldmask, mask)
	tobj.objMasks[obj] = dioa.set.simplify(exist, objmask, dioa.set.empty)

	# Recurse into each of the object's fields
	fieldLUT = obj.slots

	for name, field in fieldLUT.iteritems():
		# Don't ad intrinsic fields to the tree
		#if intrinsics.isIntrinsicField(name): continue

		# Don't ad unused fields to the tree
		if field not in lut: continue

		# Handle the contents of the field.
		ctree = lut[field].annotation.values.correlated

		child = tobj.getField(name)
		handleCTree(dioa, ctree, lut, exist, mask, child)


def handleCTree(dioa, ctree, lut, exist, mask, tobj):
	ctree = dioa.set.simplify(mask, ctree, dioa.set.empty)
	flat  = dioa.set.flatten(ctree)

	for obj in flat:
		# For each possible object, produce a correlated mask
		objleaf = dioa.set.leaf((obj,))
		omask = dioa.bool.in_(objleaf, ctree)
		omask = dioa.bool.and_(mask, omask)

		# Recurse
		handleObj(dioa, obj, lut, exist, omask, tobj)


# Used for getting the context object.
def getSingleObject(dioa, lut, lcl):
	node = lut[lcl]
	flat  = node.annotation.values.flat
	assert len(flat) == 1
	return tuple(flat)[0]


def evaluateContextObject(dioa, lut, exist, lcl, obj, treetype):
	tobj = IOTreeObj(('context',), lcl, treetype)

	mask = dioa.bool.true
	handleObj(dioa, obj, lut, exist, mask, tobj)

	if False: tobj.dump('context')

	return tobj


def evaluateLocal(dioa, lut, exist, lcl, treetype):
	assert lcl is not None, lcl

	# The local may be unused, but still a formal parameter
	if lcl.isDoNotCare() or lcl not in lut:
		return IOTreeObj((), None, treetype)

	node = lut[lcl]

	# The correlated tree
	ctree = node.annotation.values.correlated

	tobj = IOTreeObj((lcl,), lcl, treetype)

	handleCTree(dioa, ctree, lut, exist, dioa.bool.true, tobj)

	if False: tobj.dump(lcl)

	return tobj
