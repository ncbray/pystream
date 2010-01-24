from language.python import ast

def buildTempLocal(analysis, objs):
	if objs is None:
		return None
	else:
		lcl = analysis.root.local(ast.Local('entry_point_arg'))
		objs = frozenset([analysis.objectName(xtype) for xtype in objs])
		lcl.updateValues(objs)
		return lcl

def buildEntryPoint(analysis, ep, epargs):
	selfarg = buildTempLocal(analysis, epargs.selfarg)

	args = []
	for arg in epargs.args:
		args.append(buildTempLocal(analysis, arg))

	varg = buildTempLocal(analysis, epargs.vargs)
	karg = buildTempLocal(analysis, epargs.kargs)

	analysis.root.dcall(ep, ep.code, selfarg, args, [], varg, karg, None)
