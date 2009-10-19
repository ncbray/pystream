#@PydevCodeAnalysisIgnore

module('confusion')
output('../temp')
config(checkTypes=True)

entryPoint('beConfused', inst('bool'))
entryPoint('beConfusedSite', inst('bool'))
entryPoint('beConfusedConst', inst('int'))

entryPoint('confuseMethods', inst('int'), inst('int'), inst('int'), inst('int'), inst('int'), inst('int'))
