## Component List to define schedules

### Day_schedule

Component used for simple definition of daily variation of a value.

#### Parameters
- **time_steps** [_int-list_, unit = "s", default = [3600], min = 1]: time steps where the values change. 
- **values** [_float-list_, default = [0,10]]: Values for the time steps defined in the previous parameter. It must always contain one more element than the parameter "time_steps".
- **interpolation** [_option_, default = "STEP", options = ["STEP","LINEAR"]]: Procedure used to obtain the values at each of the simulation instants. "STEP": The value changes in the form of a step. "LINEAR": The value changes linearly between the values defined in the schedule. 

**Example:**
<pre><code class="python">
...

day = pro.new_component("Day_schedule","day")
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

### Week_schedule

Component used for simple definition of week variation of a value. It uses to Day_schedule components

#### Parameters
- **days-schedules** [_component-list_, default = ["not_defined"], component type = Day_schedule]: Day_schedule used for the different days of the week. It can contain one value (it will be the one used for all days) or seven values, the Day_schedules for Monday, Tuesday, Wednesday, Thursday, Friday, Saturday and Sunday.


**Example:**
<pre><code class="python">
...

week = pro.new_component("Week_schedule","week")
param = {
    "days_schedules": ["working_day","working_day","working_day","working_day","working_day","holiday_day","holiday_day"]
}
week.set_parameters(param)
</code></pre>

The Day_schedule called "working_day" will be used from Monday to Friday, "holiday_day" will be used on Saturday an Sunday.

### Year_schedule

Component used for simple definition of year variation of a value. It uses to Week_schedule components

#### Parameters
- **periods** [_string-list_, default = ["01/06"]]: Ends of the different periods. Each of them must be in "dd:mm" format. 
The begining of the first period is "01/01" and the end of the last period "31/12"
- **weeks_schedules** [_component-list_, default = ["not_defined","not_defined]]: Week_schedule to be used in the different periods. It must always contain one more element than the parameter "periods".

**Example:**
<pre><code class="python">
...

year = pro.new_component("Year_schedule","year")
param = {
    "periods": ["31/07","31/08"],
    "weeks_schedules": ["working_week","holiday_week","working_week"]
}
year.set_parameters(param)
</code></pre>

The Week_schedule called "holiday_week" will be used for August and "working_week" for the rest of the year.

#### Variables
- **values**: values obtained using year, weeks and days schedules for each of the simulation time steps.

If the project to be simulated has the daylight_saving parameter activated, summer time will be taken into account when obtaining the hourly values by shifting the values by one hour during the daylight saving period.

