from .. import intrinsics

class IOTreeObj(object):
	def __init__(self, path, parent=None):
		self.parent   = parent
		self.path     = path
		self.objMasks = {}
		self.fields   = {}

	def getField(self, field):
		if not field in self.fields:
			slot = IOTreeObj(self.path + (field,), self)
			self.fields[field] = slot
		else:
			slot = self.fields[field]
		return slot
				
def handleObj(dioa, obj, lut, exist, mask, tobj):
	# Does this field actually exist?
	if mask is dioa.bool.false: return
	
	# Accumulate the mask
	oldmask = tobj.objMasks.get(obj, dioa.bool.false)
	objmask = dioa.bool.or_(oldmask, mask)
	tobj.objMasks[obj] = dioa.set.simplify(exist, objmask, dioa.set.empty)
	
	# Recurse into each of the object's fields
	fieldLUT = obj[0].slots
	index = obj[1]

	for name, field in fieldLUT.iteritems():
		# Don't ad intrinsic fields to the tree
		if intrinsics.isIntrinsicField(name): continue

		# Don't ad unused fields to the tree
		if field not in lut: continue
		
		# Handle the contents of the field.
		ctree = dioa.getValue(lut[field], index)
		handleCTree(dioa, ctree, lut, exist, mask, tobj.getField(name))

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

def printNode(tobj):
	print tobj.path
	print tobj.objMasks
	
	for field, next in tobj.fields.iteritems():
		printNode(next)

# Used for getting the context object.
def getSingleObject(dioa, lut, lcl):
	node = lut[lcl]
	ctree = dioa.getValue(node, 0)
	flat  = dioa.set.flatten(ctree)
	assert len(flat) == 1
	return flat.pop()

def evaluateContextObject(dioa, lut, exist, obj):
	tobj = IOTreeObj(('context',))
	mask = dioa.bool.true
	handleObj(dioa, obj, lut, exist, mask, tobj)

	if True:
		print
		print 'context'
		printNode(tobj)
		print	
	
	return tobj

def evaluateLocal(dioa, lut, exist, lcl):
	if lcl is None: return None
		
	node = lut[lcl]
	
	# The correlated tree
	ctree = dioa.getValue(node, 0)

	tobj = IOTreeObj((lcl,))

	handleCTree(dioa, ctree, lut, exist, dioa.bool.true, tobj)
	
	if True:
		print
		print lcl
		printNode(tobj)
		print
	
	return tobj
