## Component List for various utilities

### Calculator

Component to perform calculations with the variables of other components.

#### Parameters

- **input_variables** [_variable_list_, default = []]: List of variables from other components used in this component. They can appear in the expressions of the “output_expressions” parameter.
- **output_variables** [_string_list_, default = []]: List of output variable names.
- **output_units** [_string_list_, default = []]: List of output variable units.
- **output_expressions** [_math_exp_list_, default = []]: List of output variable mathematical expressions.

#### Variables
The component will generate a variable for each of the input variables specified in "input_variables" and "output_variables" using the mathematical expressions for the calculation in each time step.

**Example:**
<pre><code class="python">
...

calc = osm.new_component("Calculator","unit_change")
param = {
    "input_variables": ["T = met.temperature", "w = met.abs_humidity"],
    "output_variables": ["T_F","W_kg"],
    "output_units": ["ºF","kg/kg a.s."],
    "output_expressions": ["T * 9/5 + 32", "w / 1000"]
}
calc.set_parameters(param)
</code></pre>

Four variables will be created with names: T, w, T_F and W_kg, two from input_variables and two from output_variables.
