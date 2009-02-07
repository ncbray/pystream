from __future__ import absolute_import

import programIR.python.ast as ast
import util

def simpleDescriptor(collector, name, argnames, rt, hasSelfParam=True):
	assert isinstance(name, str), name
	assert isinstance(argnames, (tuple, list)), argnames
	assert isinstance(rt, type), rt

	def simpleDescriptorBuilder():
		if hasSelfParam:
			selfp = ast.Local('internal_self')
		else:
			selfp = None

		args  = [ast.Local(argname) for argname in argnames]
		inst  = ast.Local('inst')
		retp  = ast.Local('internal_return')

		b = ast.Suite()
		t = collector.existing(rt)
		b.append(collector.allocate(t, inst)) # HACK no init?

		# Return the allocated object
		b.append(ast.Return(inst))

		code = ast.Code(name, selfp, args, list(argnames), None, None, retp, b)
		f = ast.Function(name, code)

		collector.descriptive(f)

		return f

	return simpleDescriptorBuilder

