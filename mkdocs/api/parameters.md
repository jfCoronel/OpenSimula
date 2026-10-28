# Parameters

Projects and components keep their parameters in a [Parameter_container](#opensimula.Parameter_container.Parameter_container).
Every parameter is read and changed through its `value`:

```python
space = pro.component("space_1")
space.parameter("volume").value = 129.6
```

::: opensimula.Parameter_container.Parameter_container

## Parameter types

::: opensimula.Parameters.Parameter

::: opensimula.Parameters.Parameter_boolean
    options:
      members: false

::: opensimula.Parameters.Parameter_boolean_list
    options:
      members: false

::: opensimula.Parameters.Parameter_string
    options:
      members: false

::: opensimula.Parameters.Parameter_string_list
    options:
      members: false

::: opensimula.Parameters.Parameter_int
    options:
      members: false

::: opensimula.Parameters.Parameter_int_list
    options:
      members: false

::: opensimula.Parameters.Parameter_float
    options:
      members: false

::: opensimula.Parameters.Parameter_float_list
    options:
      members: false

::: opensimula.Parameters.Parameter_options
    options:
      members: false

::: opensimula.Parameters.Parameter_options_list
    options:
      members: false

::: opensimula.Parameters.Parameter_component
    options:
      members: [component]

::: opensimula.Parameters.Parameter_component_list
    options:
      members: [component]

::: opensimula.Parameters.Parameter_variable
    options:
      members: [variable]

::: opensimula.Parameters.Parameter_variable_list
    options:
      members: [variable]

::: opensimula.Parameters.Parameter_math_exp
    options:
      members: [evaluate]

::: opensimula.Parameters.Parameter_math_exp_list
    options:
      members: [evaluate]
