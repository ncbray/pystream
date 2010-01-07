from language.python import ast
from analysis.dataflowIR import graph
from analysis.dataflowIR import annotations

from translator import intrinsics

def makeCorrelatedAnnotation(dioa, data):
	return annotations.CorrelatedAnnotation(dioa.set.flatten(data), data)

def getName(subtree, root):
	name = 'bogus'

	if subtree.name:
		name = subtree.name
	elif isinstance(root, graph.LocalNode):
		for lcl in root.names:
			if lcl.name:
				name = lcl.name
				break
	return name

def createLocalNode(hyperblock, name, values):
	lcl  = ast.Local(name)
	node = graph.LocalNode(hyperblock, (lcl,))
	annotation = annotations.DataflowSlotAnnotation(values, True)
	node.annotation = annotation

	return node

def addOutput(g, subtree, original):
	if hasattr(original, 'annotation'):
		values = original.annotation.values
	else:
		values = original

	node = createLocalNode(g.hyperblock, getName(subtree, original), values)

	g.addLocalModify(node.names[0], node)

	return node

def allocateObj(dioa, dataflow, subtree, slot, obj):
	hyperblock = dataflow.entry.hyperblock
	predicate  = dataflow.entryPredicate
	objs       = slot.annotation.values.flat

	# Allocate
	assert len(objs) == 1

	obj      = tuple(objs)[0]
	cls      = ast.Existing(obj.xtype.obj.type)
	allocate = ast.Allocate(cls)
	g = graph.GenericOp(hyperblock, allocate)

	g.setPredicate(predicate)
	g.addLocalRead(cls, dataflow.getExisting(cls, obj))

	# TODO mask?
	setOpAnnotation(dioa, g, allocate=dioa.set.leaf((obj,)))

	return addOutput(g, subtree, slot)

def makeStoreOp(dataflow, hyperblock, predicate, exprNode, field, valueNode):
	name = ast.Existing(field.name)
	op = ast.Store(exprNode.names[0], field.type, name, valueNode.names[0])

	g = graph.GenericOp(hyperblock, op)
	g.setPredicate(predicate)
	g.addLocalRead(exprNode.names[0], exprNode)
	g.addLocalRead(name, dataflow.getExisting(name))
	g.addLocalRead(valueNode.names[0], valueNode)

	return g

def transformInputSubtree(compiler, dioa, dataflow, subtree, root):
	hyperblock = dataflow.entry.hyperblock
	predicate  = dataflow.entryPredicate
	objs = root.annotation.values.flat # HACK - what about correlation?

	assert len(objs) > 0
	obj = tuple(objs)[0]

	# HACK temporarily ignore correlated objects.
	if len(objs) > 1:
		exprNode = createLocalNode(hyperblock, getName(subtree, root), root.annotation.values)
		name = exprNode.names[0]
		dataflow.entry.addEntry(name, exprNode)
		subtree.impl = name
	else:
		assert len(objs) == 1
		if intrinsics.isIntrinsicObject(obj):
			exprNode = createLocalNode(hyperblock, getName(subtree, root), root.annotation.values)
			name = exprNode.names[0]
			dataflow.entry.addEntry(name, exprNode)
			subtree.impl = name

			# Prevent the fields of this object from being transformed
			return exprNode
		else:
			exprNode = allocateObj(dioa, dataflow, subtree, root, obj)

	lut = dataflow.entry.modifies

	# Recurse to each field of this node
	for field, child in subtree.fields.iteritems():
		# Field the field nodes for the field name
		fieldNodes = [lut[o.slots[field]] for o in objs if field in o.slots]

		fieldNode = fieldNodes[0] # HACK

		# HACK ignore correlated fields
		#if fieldNode.annotation.values.correlated.tree(): continue

		# Create the dataflow store
		valueNode = transformInputSubtree(compiler, dioa, dataflow, child, fieldNode)

		g = makeStoreOp(dataflow, hyperblock, predicate, exprNode, field, valueNode)

		for oldField in fieldNodes:
			# This op should produce a new version of the field
			newField = oldField.duplicate()
			g.addModify(newField.name, newField)

			# Reads from this field should come from the store instead
			oldField.canonical().redirect(newField)

		# TODO mask?
		setOpAnnotation(dioa, g, modify=dioa.set.leaf(fieldNodes))

	return exprNode

def setOpAnnotation(dioa, g, read=None, modify=None, allocate=None, mask=None):
	read     = makeCorrelatedAnnotation(dioa, dioa.set.empty if read is None else read)
	modify   = makeCorrelatedAnnotation(dioa, dioa.set.empty if modify is None else modify)
	allocate = makeCorrelatedAnnotation(dioa, dioa.set.empty if allocate is None else allocate)
	mask     = dioa.bool.true if mask is None else mask

	annotation = annotations.DataflowOpAnnotation(read, modify, allocate, mask)
	g.annotation = annotation


def transformInput(compiler, dioa, dataflow, contextIn, root):
	exprNode = transformInputSubtree(compiler, dioa, dataflow, contextIn, root)

	# We create a new local, so replace it.
	if root.isLocal(): root.canonical().redirect(exprNode)


def makeLoadOp(dataflow, hyperblock, predicate, root, field):
	if isinstance(root, graph.LocalNode):
		expr = root.names[0]
	else:
		assert isinstance(root, graph.ExistingNode)
		expr = root.name

	# Create the dataflow load
	name = ast.Existing(field.name)
	nameref = field.name # HACK incorrect
	op   = ast.Load(expr, field.type, name)

	g = graph.GenericOp(hyperblock, op)
	g.setPredicate(predicate)
	g.addLocalRead(expr, root)
	g.addLocalRead(name, dataflow.getExisting(name, nameref))

	return g

def transformOutputSubtree(compiler, dioa, dataflow, subtree, root):
	hyperblock = dataflow.exit.hyperblock
	predicate = dataflow.exit.predicate

	for field, child in subtree.fields.iteritems():
		# Intrinsic fields will be transfered by copying the object they are attached to
		if intrinsics.isIntrinsicField(field): continue

		g = makeLoadOp(dataflow, hyperblock, predicate, root, field)

		reads = dioa.set.empty
		values = dioa.set.empty

		for obj, mask in subtree.objMasks.iteritems():
			slot = obj.knownField(field)
			node = dataflow.exit.reads[slot]

			g.addRead(slot, node)

			reads = dioa.set.union(reads, dioa.set.ite(mask, dioa.set.leaf((node,)), dioa.set.empty))

			fieldValues = node.annotation.values.correlated
			fieldValues = dioa.set.simplify(mask, fieldValues, dioa.set.empty)
			values = dioa.set.union(values, fieldValues)

		# TODO mask?
		setOpAnnotation(dioa, g, read=reads)

		outputNode = addOutput(g, child,  makeCorrelatedAnnotation(dioa, values))

		# Expose the local at the output.
		# HACK assumes the first name is the "canonical" name
		name = outputNode.names[0]
		dataflow.exit.addExit(name, outputNode)
		child.impl = name

		transformOutputSubtree(compiler, dioa, dataflow, child, outputNode)

def transformOutput(compiler, dioa, dataflow, contextOut, root):
	transformOutputSubtree(compiler, dioa, dataflow, contextOut, root)

def killNonintrinsicIO(compiler, dataflow):
	def callback(name, slot):
		if slot.isField():
			# Kill non-intrinsic fields.
			return intrinsics.isIntrinsicSlot(slot.name)
		elif slot.isLocal():
			# Kill locals that do not contain intrinsic types.
			intrinsicObj = any([intrinsics.isIntrinsicObject(obj) for obj in slot.annotation.values.flat])
			return intrinsicObj

	node = dataflow.exit.filterUses(callback)


# Used for culling the output of the fragment shader.
# Only the built-in outputs of the fragment shader are actually used.
def killUnusedOutputs(context):
	def callback(name, slot):
		if isinstance(name, ast.Local):
			if name not in context.trees.outputLUT:
				return False
			tree = context.trees.outputLUT[name]
			return tree.builtin or tree.link
		else:
			return True

	node = context.dataflow.exit
	node.filterUses(callback)
