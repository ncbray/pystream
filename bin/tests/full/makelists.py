#@PydevCodeAnalysisIgnore

module('lists')
output('../temp')
config(checkTypes=True)

entryPoint('listTest', inst('float'), inst('float'), inst('float'))
entryPoint('addConstList')
entryPoint('addHybridList', inst('int'))
entryPoint('swap', inst('int'), inst('int'))

entryPoint('unpackConstCompound')
entryPoint('unpackCompound', inst('int'), inst('int'), inst('int'), inst('int'))

entryPoint('index')
