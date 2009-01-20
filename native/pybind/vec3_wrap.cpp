#include "stdafx.h"
#include "pybind.h"

#include "vec3.h"

vec3 operator*(const vec3 &a, const vec3 &b) 
{
	return vec3(a.x*b.x, a.y*b.y, a.z*b.z);
}

vec3 operator*(const vec3 &a, float b) 
{
	return vec3(a.x*b, a.y*b, a.z*b);
}

vec3 operator*(float a, const vec3 &b) 
{
	return vec3(a*b.x, a*b.y, a*b.z);
}

static vec3_wrapper * vec3_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
static int vec3_init(vec3_wrapper * wrapper, PyObject *args, PyObject *kwds);
static void vec3_delete(vec3_wrapper * obj);


static PyObject * vec3_zero(vec3_wrapper * self);
static PyObject * vec3_dot(vec3_wrapper * self, PyObject *args);
static PyObject * vec3_operator_mul(PyObject *left, PyObject *right);
static PyObject * vec3_operator_iadd(PyObject *self, PyObject *arg);

static PyMethodDef vec3_methods[] = {
	{"zero",	(PyCFunction)vec3_zero,	METH_NOARGS, "Clear the vector"},
	{"dot",		(PyCFunction)vec3_dot,	METH_VARARGS, "Dot product"},
	{NULL}  /* Sentinel */
};

static PyObject * vec3_get_x(vec3_wrapper *self, void *closure)
{
	return PyFloat_FromDouble(self->obj->x);
}

static int vec3_set_x(vec3_wrapper *self, PyObject *value, void *closure)
{
	if (value == NULL) {
		PyErr_SetString(PyExc_TypeError, "Cannot delete attribute");
		return -1;
	}

	if (! PyFloat_Check(value)) {
		PyErr_SetString(PyExc_TypeError, "The last attribute value must be a float");
		return -1;
	}

	self->obj->x = (float)PyFloat_AsDouble(value);

	return 0;
}


static PyObject * vec3_get_y(vec3_wrapper *self, void *closure)
{
	return PyFloat_FromDouble(self->obj->y);
}

static int vec3_set_y(vec3_wrapper *self, PyObject *value, void *closure)
{
	if (value == NULL) {
		PyErr_SetString(PyExc_TypeError, "Cannot delete attribute");
		return -1;
	}

	if (! PyFloat_Check(value)) {
		PyErr_SetString(PyExc_TypeError, "The last attribute value must be a float");
		return -1;
	}

	self->obj->y = (float)PyFloat_AsDouble(value);

	return 0;
}


static PyObject * vec3_get_z(vec3_wrapper *self, void *closure)
{
	return PyFloat_FromDouble(self->obj->z);
}

static int vec3_set_z(vec3_wrapper *self, PyObject *value, void *closure)
{
	if (value == NULL) {
		PyErr_SetString(PyExc_TypeError, "Cannot delete attribute");
		return -1;
	}

	if (! PyFloat_Check(value)) {
		PyErr_SetString(PyExc_TypeError, "The last attribute value must be a float");
		return -1;
	}

	self->obj->z = (float)PyFloat_AsDouble(value);

	return 0;
}

//static PyMemberDef vec3_members[] = {}

static PyGetSetDef vec3_getset[] = {
	{"x", (getter)vec3_get_x, (setter)vec3_set_x, "", NULL},
	{"y", (getter)vec3_get_y, (setter)vec3_set_y, "", NULL},
	{"z", (getter)vec3_get_z, (setter)vec3_set_z, "", NULL},
	{NULL}  /* Sentinel */
};


static PyNumberMethods vec3_number = {
	0, /*nb_add*/
	0, /*nb_subtract*/
	vec3_operator_mul, /*nb_multiply*/
	0, /*nb_divide*/
	0, /*nb_remainder*/
	0, /*nb_divmod*/
	0, /*nb_power*/
	0, /*nb_negative*/
	0, /*nb_positive*/
	0, /*nb_absolute*/
	0, /*nb_nonzero*/
	0, /*nb_invert*/
	0, /*nb_lshift*/
	0, /*nb_rshift*/
	0, /*nb_and*/
	0, /*nb_xor*/
	0, /*nb_or*/
	0, /*nb_coerce*/
	0, /*nb_int*/
	0, /*nb_long*/
	0, /*nb_float*/
	0, /*nb_oct*/
	0, /*nb_hex*/

	/* Added in release 2.0 */
	vec3_operator_iadd, /*nb_inplace_add*/
	0, /*nb_inplace_subtract*/
	0, /*nb_inplace_multiply*/
	0, /*nb_inplace_divide*/
	0, /*nb_inplace_remainder*/
	0, /*nb_inplace_power*/
	0, /*nb_inplace_lshift*/
	0, /*nb_inplace_rshift*/
	0, /*nb_inplace_and*/
	0, /*nb_inplace_xor*/
	0, /*nb_inplace_or*/

	/* Added in release 2.2 */
	/* The following require the Py_TPFLAGS_HAVE_CLASS flag */
	0, /*nb_floor_divide*/
	0, /*nb_true_divide*/
	0, /*nb_inplace_floor_divide*/
	0, /*nb_inplace_true_divide*/
};

static PyTypeObject vec3_type = {
	PyObject_HEAD_INIT(NULL)
	0,							/*ob_size*/
	"pybind.vec3",				/*tp_name*/
	sizeof(vec3_wrapper),		/*tp_basicsize*/
	0,							/*tp_itemsize*/
	(destructor)vec3_delete,	/*tp_dealloc*/
	0,							/*tp_print*/
	0,							/*tp_getattr*/
	0,							/*tp_setattr*/
	0,							/*tp_compare*/
	0,							/*tp_repr*/
	&vec3_number,				/*tp_as_number*/
	0,							/*tp_as_sequence*/
	0,							/*tp_as_mapping*/
	0,							/*tp_hash */
	0,							/*tp_call*/
	0,							/*tp_str*/
	0,							/*tp_getattro*/
	0,							/*tp_setattro*/
	0,							/*tp_as_buffer*/
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_CHECKTYPES,		/*tp_flags*/
	"three dimensional vector",	/* tp_doc */
	0,							/* tp_traverse */
	0,							/* tp_clear */
	0,							/* tp_richcompare */
	0,							/* tp_weaklistoffset */
	0,							/* tp_iter */
	0,							/* tp_iternext */
	vec3_methods,				/* tp_methods */
	0,							/* tp_members */
	vec3_getset,				/* tp_getset */
	0,							/* tp_base */
	0,							/* tp_dict */
	0,							/* tp_descr_get */
	0,							/* tp_descr_set */
	0,							/* tp_dictoffset */
	(initproc)vec3_init,		/* tp_init */
	0,							/* tp_alloc */
	(newfunc)vec3_new,			/* tp_new */
};




static vec3_wrapper * vec3_make() {
	vec3_wrapper * const res = PyObject_New(vec3_wrapper, &vec3_type);
	res->obj = new vec3();
	return res;
}

static vec3_wrapper * vec3_make(const vec3 &obj) {
	vec3_wrapper * const res = PyObject_New(vec3_wrapper, &vec3_type);
	res->obj = new vec3(obj);
	return res;
}

void vec3_destroy(vec3_wrapper * wrapper)
{
	delete wrapper->obj;
	PyObject_Del(wrapper);
}

static vec3_wrapper * vec3_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
	printf("type new\n");
	return vec3_make();
}

static int vec3_init(vec3_wrapper * self, PyObject *args, PyObject *kwds) {
	printf("type init\n");

	static char *kwlist[] = {"x", "y", "z", NULL};

	PyObject *arg0 = 0;
	PyObject *arg1 = 0;
	PyObject *arg2 = 0;

	if(!PyArg_ParseTupleAndKeywords(args, kwds, "|OOO:vec3.__init__", kwlist, &arg0, &arg1, &arg2)) 
		return -1;

	if(!arg0)
	{

		*self->obj = vec3();
		return 0;
	}
 	else if(!arg1)
 	{
 		if(PyObject_TypeCheck(arg0, &PyFloat_Type))
 		{
 			*self->obj = vec3((float)PyFloat_AsDouble(arg0));
 			return 0;
 		}
 		else if (PyObject_TypeCheck(arg0, &vec3_type))
 		{
 			*self->obj = *static_cast<vec3_wrapper *>(arg0)->obj;
 			return 0;
 		}
		PyErr_SetString(PyExc_TypeError, "vec3.__init__() invalid types for arguments");
	}
 	else if(!arg2)
 	{
		PyErr_SetString(PyExc_TypeError, "vec3.__init__() can not take 2 arguments");
 	}
	else
 	{
 		if(PyObject_TypeCheck(arg0, &PyFloat_Type) && PyObject_TypeCheck(arg1, &PyFloat_Type) && PyObject_TypeCheck(arg2, &PyFloat_Type))
 		{
 			*self->obj = vec3((float)PyFloat_AsDouble(arg0), (float)PyFloat_AsDouble(arg1), (float)PyFloat_AsDouble(arg2));
 			return 0;
 		}
		PyErr_SetString(PyExc_TypeError, "vec3.__init__() invalid types for arguments");
	}

		
	return -1;
}


static void vec3_delete(vec3_wrapper * wrapper)
{
	printf("type del %x\n", (size_t)wrapper);
	vec3_destroy(wrapper);
}

static PyObject * vec3_zero(vec3_wrapper * self)
{
	self->obj->zero();
	Py_RETURN_NONE;
}

static PyObject * vec3_dot(vec3_wrapper * self, PyObject *args)
{
	// Extract arguments
	PyObject *arg0 = 0;
	if(!PyArg_ParseTuple(args, "O!:dot", &vec3_type, &arg0))
		return NULL;

	vec3_wrapper * const other = pybind_convertptr<vec3_wrapper>(arg0);

	// Call
	const float result = self->obj->dot(*(other->obj));

	// Return
	return PyFloat_FromDouble(result);
}

static PyObject * vec3_operator_mul(PyObject *left, PyObject *right)
{
	if(PyObject_TypeCheck(left, &vec3_type))
	{
		const vec3 & a = *(pybind_convertptr<vec3_wrapper>(left)->obj);

		if(PyObject_TypeCheck(right, &vec3_type))
		{
			const vec3 & b = *(pybind_convertptr<vec3_wrapper>(right)->obj);
			return vec3_make(a*b);
		}
		else if(PyFloat_Check(right))
		{
			const float b = (float)PyFloat_AsDouble(right);
			return vec3_make(a*b);
		}
	}
	else if(PyObject_TypeCheck(left, &PyFloat_Type))
	{
		const float a = (float)PyFloat_AsDouble(left);

		if(PyObject_TypeCheck(right, &vec3_type))
		{
			const vec3 & b = *(pybind_convertptr<vec3_wrapper>(right)->obj);
			return vec3_make(a*b);
		}
	}

	Py_RETURN_NOTIMPLEMENTED;
}

static PyObject * vec3_operator_iadd(PyObject *self, PyObject *arg)
{

	vec3 & a = *(pybind_convertptr<vec3_wrapper>(self)->obj);

	if(PyObject_TypeCheck(arg, &vec3_type))
	{
		const vec3 & b = *(pybind_convertptr<vec3_wrapper>(arg)->obj);
		a += b;
		
		Py_INCREF(self);
		return self;
	}
	else if(PyObject_TypeCheck(arg, &PyFloat_Type))
	{
		const float b = (float)PyFloat_AsDouble(arg);
		a += b;

		Py_INCREF(self);
		return self;
	}

	Py_RETURN_NOTIMPLEMENTED;
}

void vec3_init()
{
	//vec3_type.tp_new = PyType_GenericNew;
}

void vec3_attach(PyObject * m)
{
	vec3_init();

	if (PyType_Ready(&vec3_type) < 0)
		return; // TODO error?

	Py_INCREF(&vec3_type);
	PyModule_AddObject(m, "vec3", (PyObject *)&vec3_type);
}


