# Testrail Data: a handy Testrail data analysis tool

## What is it?

This is a wrapper of [Testrail Api](https://github.com/tolstislon/testrail-api) with [pandas](https://github.com/pandas-dev/pandas) DataFrame extended. Especially when you are working on huge data-set, say years of results, this is a handly library. 

## Installation

`pip install testrail-data`

## Main Features

- Transform pulled data into DataFrame object, covering:
  - Case
  - Case Fields
  - Case Type
  - Milestone
  - Plan
  - Priority
  - Results
  - Run
  - Sections
  - Suite
  - Statuses
  - Template
  - Test
- Complete pull with auto-offset cabability to walk through all pages, avalaible to:
  - Run
  - Result
  - Plan
- Meta data filling option to all IDs in:
  - Case
  - Test
  - Result (in comming version)

### Example usage with DataFrame

```python
from testrail_data import TestRailAPI

api = TestRailAPI("https://example.testrail.com/", "example@mail.com", "password")

# if use environment variables
# TESTRAIL_URL=https://example.testrail.com/
# TESTRAIL_EMAIL=example@mail.com
# TESTRAIL_PASSWORD=password
# api = TestRailAPI()

# if you having a big project with more than 250 runs, 
# this method would help you too pull them down in single call.
df_run = api.runs.to_dataframe(project_id=1)
df_run.info()

# Pulling all Run by Plan
df_run = api.runs.dataframe_from_plan(plan_id=3)
```

### Example usage with Meta data

```python
# continue ...

df_case = api.cases.to_dataframe(project_id=1, suite_id=2, with_meta=True)
# Additional name-columns created base on 
# section_id, template_id, type_id, priority_id, suite_id
# all custom_columns are replaced with meta data.

```