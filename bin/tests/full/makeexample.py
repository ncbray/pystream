#@PydevCodeAnalysisIgnore

module('example')
output('../temp')
config(checkTypes=True)

entryPoint('f')
entryPoint('add', const(1.0), const(2.0))
entryPoint('add', inst('int'), inst('int'))
entryPoint('call', inst('float'), inst('float'), inst('float'), inst('float'))
entryPoint('either', inst('int'), inst('int'))
entryPoint('inrange', inst('float'))

entryPoint('negate', inst('int'))
entryPoint('negateConst')

entryPoint('defaultArgs')
entryPoint('defaultArgs', inst('int'))
entryPoint('defaultArgs', inst('int'), inst('int'))

entryPoint('switch1', inst('float'))
entryPoint('switch2', inst('float'))

#entryPoint('factorial', inst('int'))
# TODO, prevent infinite recursion.
#entryPoint('factorial', const(10))
