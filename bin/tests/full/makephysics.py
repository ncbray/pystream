#@PydevCodeAnalysisIgnore

module('tests.full.physics')
output('../temp')
config(checkTypes=True)


import tests.full.physics as physics
import shader.vec as vec

attr(inst(vec.vec2), 'x', inst(float))
attr(inst(vec.vec2), 'y', inst(float))

attr(inst(vec.vec3), 'x', inst(float))
attr(inst(vec.vec3), 'y', inst(float))
attr(inst(vec.vec3), 'z', inst(float))

attr(inst(vec.vec4), 'x', inst(float))
attr(inst(vec.vec4), 'y', inst(float))
attr(inst(vec.vec4), 'z', inst(float))
attr(inst(vec.vec4), 'w', inst(float))

attr(inst(vec.mat4), 'm00', inst(float))
attr(inst(vec.mat4), 'm01', inst(float))
attr(inst(vec.mat4), 'm02', inst(float))
attr(inst(vec.mat4), 'm03', inst(float))
attr(inst(vec.mat4), 'm10', inst(float))
attr(inst(vec.mat4), 'm11', inst(float))
attr(inst(vec.mat4), 'm12', inst(float))
attr(inst(vec.mat4), 'm13', inst(float))
attr(inst(vec.mat4), 'm20', inst(float))
attr(inst(vec.mat4), 'm21', inst(float))
attr(inst(vec.mat4), 'm22', inst(float))
attr(inst(vec.mat4), 'm23', inst(float))
attr(inst(vec.mat4), 'm30', inst(float))
attr(inst(vec.mat4), 'm31', inst(float))
attr(inst(vec.mat4), 'm32', inst(float))
attr(inst(vec.mat4), 'm33', inst(float))


#vec3 = cls(vec.vec3)
#vec3.init(inst(float), inst(float), inst(float))
#vec3.attr('x', 'y', 'z')
#vec3.method('__add__', inst(vec.vec3))
#vec3.method('__mul__', inst(vec.vec3))
#vec3.method('normalize')

#func(physics.simpleUpdate, inst(float), inst(int))

### Declare the types of the shader attributes ###
# HACK should declare methods instead?

attr(inst(physics.Shader), 'objectToWorld', inst(vec.mat4))
attr(inst(physics.Shader), 'worldToCamera', inst(vec.mat4))
attr(inst(physics.Shader), 'projection', inst(vec.mat4))

attr(inst(physics.Shader), 'light', inst(physics.PointLight))


attr(inst(physics.Shader), 'ambient',  inst(physics.AmbientLight))
#attr(inst(physics.Shader), 'color',    inst(vec.vec3))
#attr(inst(physics.Shader), 'material',    inst(physics.Material))

#attr(inst(physics.Shader),          'material',  inst(physics.LambertMaterial))
#attr(inst(physics.LambertMaterial), 'color',     inst(vec.vec3))

#attr(inst(physics.Shader),          'material',  inst(physics.DummyMaterial))
#attr(inst(physics.DummyMaterial),   'color',     inst(vec.vec3))

attr(inst(physics.Shader),          'material',  inst(physics.PhongMaterial))
attr(inst(physics.PhongMaterial),   'color',     inst(vec.vec3))
attr(inst(physics.PhongMaterial),   'shinny',     inst(float))


attr(inst(physics.Material), 'color',    inst(vec.vec3))

attr(inst(physics.PointLight), 'position',    inst(vec.vec3))
attr(inst(physics.PointLight), 'color',       inst(vec.vec3))
attr(inst(physics.PointLight), 'attenuation', inst(vec.vec3))

attr(inst(physics.AmbientLight), 'direction',  inst(vec.vec3))
attr(inst(physics.AmbientLight), 'color0',     inst(vec.vec3))
attr(inst(physics.AmbientLight), 'color1',     inst(vec.vec3))


### Declare special paths for GLSL ###
# TODO move out of makefile?
from language.python.shaderprogram import VSContext, FSContext

glsl.output(attrslot(inst(VSContext), 'position'),   'gl_Position');
glsl.output(attrslot(inst(VSContext), 'point_size'), 'gl_PointSize');

# Fragment shader
for i in range(8):
	glsl.output(attrslot(inst(FSContext), 'colors').arrayslot(i), 'gl_FragData[%d]' % i);
glsl.output(attrslot(inst(FSContext), 'depth'), 'gl_FragDepth');

### Declare  the shader entrypoint ###

glsl.shader(physics.Shader, inst(vec.vec4), inst(vec.vec3))
