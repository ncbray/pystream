module('tests.full.physics')
output('../temp')
config(checkTypes=True)


import tests.full.physics as physics
import tests.full.vec as vec

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
#func(physics.harness, inst(vec.vec4), inst(vec.vec3))

attr(inst(physics.Shader), 'objectToWorld', inst(vec.mat4))
attr(inst(physics.Shader), 'worldToCamera', inst(vec.mat4))
attr(inst(physics.Shader), 'projection', inst(vec.mat4))

attr(inst(physics.Shader), 'lightPos', inst(vec.vec4))
attr(inst(physics.Shader), 'ambient',  inst(vec.vec3))
#attr(inst(physics.Shader), 'color',    inst(vec.vec3))
attr(inst(physics.Shader), 'material',    inst(physics.Material))
attr(inst(physics.Material), 'color',    inst(vec.vec3))


glsl.output(attrslot(inst(physics.VSOut), 'position'), 'gl_Position');
glsl.output(attrslot(inst(physics.VSOut), 'point_size'), 'gl_PointSize');


# Fragment shader
for i in range(8):
	glsl.output(attrslot(inst(physics.FSOut), 'colors').arrayslot(i), 'gl_FragData[%d]' % i);
glsl.output(attrslot(inst(physics.FSOut), 'depth'), 'gl_FragDepth');


shader = cls(physics.Shader)
#shader.shader(inst(vec.vec4), inst(vec.vec3))
shader.method('shadeVertex', inst(vec.vec4), inst(vec.vec3))
shader.method('shadeFragment', inst(vec.vec4), inst(vec.vec3))