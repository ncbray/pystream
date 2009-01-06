from __future__ import absolute_import

import util.calling
from . import transferfunctions

class Constraint(object):
	__slots__ = 'parent', 'inputPoint', 'outputPoint',
	
	def __init__(self, sys, inputPoint, outputPoint):
		self.inputPoint = inputPoint
		self.outputPoint = outputPoint
		sys.environment.addObserver(inputPoint, self)

	def update(self, sys, key):
		point, context, index = key
		
		secondary = sys.environment.secondary(*key)
		self.evaluate(sys, point, context, index, secondary)


class AssignmentConstraint(Constraint):
	__slots__ = 'sourceExpr', 'destinationExpr'

	def __init__(self, sys, inputPoint, outputPoint, sourceExpr, destinationExpr):
		Constraint.__init__(self, sys, inputPoint, outputPoint)

		assert sourceExpr.isExpression(), sourceExpr
		self.sourceExpr      = sourceExpr
		
		assert destinationExpr.isExpression(), destinationExpr
		self.destinationExpr = destinationExpr


	def evaluate(self, sys, point, context, configuration, secondary):
		transferfunctions.assignmentConstraint(sys, self.outputPoint, context, self.sourceExpr, self.destinationExpr, configuration, secondary.hits, secondary.misses)


class CopyConstraint(Constraint):
	__slots__ = ()

	def evaluate(self, sys, point, context, configuration, secondary):
		# Simply changes the program point.
		sys.environment.merge(sys, self.outputPoint, context, configuration, secondary)
