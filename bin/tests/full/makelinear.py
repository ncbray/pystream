module('linear')
output('../temp')
config(checkTypes=True)

entryPoint('doDot')
entryPoint('doDotHalf', inst('float'), inst('float'), inst('float'))
entryPoint('doDotFull', inst('float'), inst('float'), inst('float'), inst('float'), inst('float'), inst('float'))

entryPoint('doOr', inst('bool'), const(7), const(11))
entryPoint('testAttrMerge', inst('bool'))


entryPoint('doStaticSwitch')
entryPoint('doDynamicSwitch', const(1))
entryPoint('doDynamicSwitch', const(0))
entryPoint('doDynamicSwitch', inst('int'))

entryPoint('doSwitchReturn', const(1))
entryPoint('doSwitchReturn', const(0))
entryPoint('doSwitchReturn', inst('int'))


entryPoint('twisted', inst('int'))
entryPoint('testBinTree')
entryPoint('vecAttrSwitch', inst('bool'))

entryPoint('doMultiSwitch', inst('bool'), inst('bool'))

entryPoint('testCall', inst('bool'))

entryPoint('selfCorrelation', inst('bool'))
entryPoint('groupCorrelation', inst('bool'))

entryPoint('methodMerge', inst('bool'))

entryPoint('assignMerge', inst('bool'))
