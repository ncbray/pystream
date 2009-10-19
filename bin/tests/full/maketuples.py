#@PydevCodeAnalysisIgnore

module('tuples')
output('../temp')
config(checkTypes=True)

entryPoint('tupleTest', inst('float'), inst('float'), inst('float'))
entryPoint('addConstTuple')
entryPoint('addHybridTuple', inst('int'))
entryPoint('swap', inst('int'), inst('int'))

entryPoint('unpackConstCompound')
entryPoint('unpackCompound', inst('int'), inst('int'), inst('int'), inst('int'))

entryPoint('index')
entryPoint('indexNoFold')
entryPoint('indexInt', inst('int'))
