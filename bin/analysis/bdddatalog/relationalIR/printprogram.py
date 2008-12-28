from __future__ import absolute_import

from util.visitor import StandardVisitor

class PrintProgram(StandardVisitor):
	def __init__(self, annotations={}):
		self.annotations = annotations

	def anno(self, node):
		if node in self.annotations:
			return " # "+str(self.annotations[node])
		else:
			return ''
	
	def visitLoad(self, node, indent):
		print indent+str(node)+self.anno(node)

	def visitStore(self, node, indent):		
		print indent+str(node)+self.anno(node)

	def visitRename(self, node, indent):		
		print indent+str(node)+self.anno(node)

	def visitProject(self, node, indent):		
		print indent+str(node)+self.anno(node)

	def visitRelProd(self, node, indent):		
		print indent+str(node)+self.anno(node)

	def visitUnion(self, node, indent):		
		print indent+str(node)+self.anno(node)

	def visitInvert(self, node, indent):		
		print indent+str(node)+self.anno(node)

	def visitJoin(self, node, indent):
		print indent+str(node)+self.anno(node)

	def visitInstructionBlock(self, node, indent):
		for op in node.instructions:
			self.visit(op, indent)

	def visitLoop(self, node, indent):
		print indent+"Loop" +self.anno(node)
		print indent+repr(node.read)
		print indent+repr(node.modify)
		indent += '\t'
		self.visit(node.block, indent)

	def visitExpression(self, node, indent):
		print indent+str(node.datalog)
		print indent+"Expression"+self.anno(node)
		print indent+"%s : %s" % (repr(node.read), repr(node.modify))
		indent += '\t'
		self.visit(node.block, indent)


	def visitProgram(self, node, indent):
		print "DOMAINS"
		for d in node.domains:
			print '\t'+str(d)

		print "RELATIONS"
		for r, n in node.relationNames.iteritems():
			print "\t%s - %s" % (str(r), str(n))

		print "CODE"
		self.visit(node.body, indent)
