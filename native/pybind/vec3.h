#ifndef VEC3_H
#define VEC3_H

class vec3 
{
public:
	vec3()
	{
		//printf("vec3 created\n");
		zero();
	}

	/*
	vec3(const vec3 &other)
	{
		//printf("vec3 copied\n");
		*this = other;
	}
	*/

	~vec3()
	{
		x = -1.0f;
		y = -1.0f;
		z = -1.0f;
		//printf("vec3 destroyed %f %f %f\n", x, y, z);
	}

	vec3(float s) : x(s), y(s), z(s){}

	vec3(float x, float y, float z) : x(x), y(y), z(z){}

	void zero()
	{
		x = 0.0f;
		y = 0.0f;
		z = 0.0f;
	}

	void scale(float s)
	{
		x *= s;
		y *= s;
		z *= s;
	}

	float dot(vec3 &other) const
	{
		return x*other.x+y*other.y+z*other.z;
	}

	void operator+=(float s)
	{
		x += s;
		y += s;
		z += s;
	}

	void operator+=(const vec3 &other)
	{
		x += other.x;
		y += other.y;
		z += other.z;
	}

	float x, y, z;
};

vec3 operator*(const vec3 &a, const vec3 &b);

vec3 operator*(const vec3 &a, float b);

vec3 operator*(float a, const vec3 &b);



struct vec3_wrapper : PyObject {
public:
	//PyObject_HEAD;
	vec3 *obj;

	vec3_wrapper() {
		printf("Wrapper new");
	}

	~vec3_wrapper() {
		printf("Wrapper del");
	}
};

#endif