from language.python import ast
from analysis.dataflowIR import graph
from analysis.dataflowIR import annotations

from .. import intrinsics

def makeCorrelatedAnnotation(dioa, data):
	return annotations.CorrelatedAnnotation(dioa.set.flatten(data), data)


def transformSubtree(compiler, dioa, dataflow, subtree, root):
	for field, child in subtree.fields.iteritems():
		expr = root.names[0]
		
		name = ast.Existing(field.name)
		op = ast.Load(expr, field.type, name)
		
		hyperblock = dataflow.exit.hyperblock
		
		g = graph.GenericOp(hyperblock, op) 
		
		g.setPredicate(dataflow.exit.predicate)

		g.addLocalRead(expr, root)
		g.addLocalRead(name, dataflow.getExisting(name))
		
		values = dioa.set.empty
		
		reads = set()
		for obj, mask in subtree.objMasks.iteritems():
			slot = obj.knownField(field)
			node = dataflow.exit.reads[slot]
		
			g.addRead(slot, node)
		
			reads.add(node)
			
			
			fieldValues = node.annotation.values.correlated
			fieldValues = dioa.set.simplify(mask, fieldValues, dioa.set.empty)
			values = dioa.set.union(values, fieldValues) 
		
		read     = makeCorrelatedAnnotation(dioa, dioa.set.leaf(reads))
		modify   = makeCorrelatedAnnotation(dioa, dioa.set.empty)
		allocate = makeCorrelatedAnnotation(dioa, dioa.set.empty)
		mask     = dioa.bool.true # HACK

		annotation = annotations.DataflowOpAnnotation(read, modify, allocate, mask)
		g.annotation = annotation

		
		name = 'bogusOut' if child.builtin is None else child.builtin
		output = ast.Local(name)
		outputNode = graph.LocalNode(hyperblock, (output,))
		
		# Build local annotation
		values = makeCorrelatedAnnotation(dioa, values)
		annotation = annotations.DataflowSlotAnnotation(values, True)
		outputNode.annotation = annotation
		
		g.addLocalModify(output, outputNode)
		
		dataflow.exit.addExit(output, outputNode)
				
		print field, child
		transformSubtree(compiler, dioa, dataflow, child, outputNode)

def transformOutput(compiler, dioa, dataflow, contextOut, root):
	transformSubtree(compiler, dioa, dataflow, contextOut, root)

def killNonintrinsicIO(compiler, dataflow):
	node = dataflow.exit

	reads = {}
	for name, slot in node.reads.iteritems():
		if slot.isField():
			if not intrinsics.isIntrinsicSlot(slot.name):
				slot.removeUse(node)
				continue
		reads[name] = slot

	node.reads = reads
