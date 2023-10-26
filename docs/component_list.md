## Component List

### Common parameters
All the components include these three parameters:

- **name** [_string_]: Name of the component.
- **type** [_string_]: Type of the component.
- **description** [_string_]: Description of the component.


### Day_schedule

Component used to define in simplified form the daily variation of a value.

#### Parameters
- **time_steps** [_int-list_, unit = "s", default = [3600], min = 1]: time steps where the values change. 
- **values** [_float-list_, default = [0,10]]: Values for the time steps defined in the previous parameter. It must always contain one more element than the parameter "time_steps".
- **interpolation** [_option_, default = "STEP", options = ["STEP","LINEAR"]]: Procedure used to obtain the values at each of the simulation instants. "STEP": The value changes in the form of a step. "LINEAR": The value changes linearly between the values defined in the schedule. 

**Example:**
<pre><code class="python">
...

day = osm.components.Day_schedule("day",project)
param = {
    "time_steps": [7200,3600],
    "values": [10,20,15],
    "interpolation": "STEP"
}
day.set_parameters(param)
</code></pre>

The first three hours of the day (7200 s) the value is 10, the next hour (3600 s) 20, and from that instant to the end of the day 15.

![day_schedule_step](img/day_schedule_step.png) 

Using `"interpolation": "LINEAR"` this would be the result

![day_schedule_linear](img/day_schedule_linear.png) 


