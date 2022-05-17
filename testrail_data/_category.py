import time
from typing import Optional
import functools
from testrail_api._category import Runs as TR_Runs, _MetaCategory
from testrail_api._category import Plans as TR_Plans
from testrail_api._category import Results as TR_Results
from testrail_api._category import Milestones as TR_Milestone
from testrail_api._category import Cases as TR_Cases
from testrail_api._category import Tests as TR_Tests
from testrail_api._category import CaseFields as TR_CaseFields
from testrail_api._category import Sections as TR_Sections
from testrail_api._category import Template as TR_Template
from testrail_api._category import CaseTypes as TR_CaseType
from testrail_api._category import Priorities as TR_Priorities
from testrail_api._category import Suites as TR_Suites
from testrail_api._category import Statuses as TR_Statuses
from requests.exceptions import ConnectionError
from pandas import DataFrame
import pandas as pd

page_size = 250
retry_total = 5
retry_sleep = 2


def auto_offset(f):
    """
    A decorator to work with pagination and connection error retry.

    :param f:
    :return:
    """
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        offset = 0
        if kwargs.get('offset'):
            assert False, 'offset has been auto managed'

        def auto_reset_connection(*_args, **_kwargs):
            trial = retry_total
            while trial > 0:
                try:
                    return f(*_args, **_kwargs)
                except ConnectionError:
                    trial -= 1
                    if trial == 0:
                        raise
                    time.sleep(retry_sleep)
                    continue

        df = auto_reset_connection(*args, **kwargs, offset=offset)
        data_size = df.shape[0]
        frames = [df]
        while data_size == page_size:
            offset += page_size
            df2 = auto_reset_connection(*args, **kwargs, offset=offset)
            data_size = df2.shape[0]
            frames.append(df2)
        return pd.concat(frames, sort=False)

    return wrap


class Metas(_MetaCategory):

    def fill_custom_fields(self, project_id: int, df: DataFrame, warning=False):
        """
        A helper to resolve metadata fill up for custom-columns.
        Unmatched columns is assigned with `UNKNOWN <config_id>`.

        :param project_id:
            The ID of the project
        :param df:
            Dataframe contains custom-columns
        :param warning:
            False to turn off warning for unmatched columns, True is otherwise.

        :return:
        """
        lookup_case_field = CaseFields(self._session).get_configs()

        def fill(x, column):
            try:
                def list_type(y):
                    y = [i for i in y if i != 0]
                    labels = [lookup_custom_field[project_id][i] for i in y]
                    return ','.join(labels)

                lookup_custom_field = lookup_case_field[column]
                if not x or project_id not in lookup_custom_field:
                    return ''
                elif isinstance(x, str) and isinstance(eval(x), list):
                    return list_type(eval(x))
                elif isinstance(x, list):
                    return list_type(x)
                elif isinstance(x, float) or str(x).isnumeric():
                    if str(x) == 'nan':
                        return ''
                    x = int(x)
                    return lookup_custom_field[project_id][x]
                return lookup_custom_field[project_id][x]
            except KeyError:
                if warning:
                    print(column, x, type(x))
                return f'UNKNOWN {x}'

        for col in [c for c in df.columns if 'custom_' in c]:
            df[col] = df[col].apply(fill, column=col)

    def fill_id_fields(self, project_id: int, suite_id: int, df: DataFrame):
        """
        A helper to resolve metadata fill up for Ids columns
        :param project_id:
            The ID of the project
        :param suite_id:
            The ID of the test suite (optional if the project is operating in
            single suite mode)
        :param df:
            Dataframe contains custom-columns
        :return:
        """

        def lookup_wrapper(key, lookup: dict):
            try:
                return lookup[key]
            except KeyError:
                return f"UNKNOWN {key}"

        if 'section_id' in df.columns:
            lookup_section = Sections(self._session).get_sections_lookup(project_id, suite_id)
            df['section_name'] = df['section_id'].apply(lookup_wrapper, lookup=lookup_section)
        if 'template_id' in df.columns:
            lookup_template = Template(self._session).get_template_lookup(project_id)
            df['template_name'] = df['template_id'].apply(lookup_wrapper, lookup=lookup_template)
        if 'type_id' in df.columns:
            lookup_case_type = CaseTypes(self._session).get_case_types_lookup()
            df['type_name'] = df['type_id'].apply(lookup_wrapper, lookup=lookup_case_type)
        if 'priority_id' in df.columns:
            lookup_priority = Priorities(self._session).get_priorities_lookup()
            df['priority_name'] = df['priority_id'].apply(lookup_wrapper, lookup=lookup_priority)
        if 'suite_id' in df.columns:
            lookup_suite = Suites(self._session).get_suites_lookup(project_id)
            df['suite_name'] = df['suite_id'].apply(lookup_wrapper, lookup=lookup_suite)


class Runs(TR_Runs):
    def get_runs_by_milestone(
            self,
            *milestone_ids: int,
            project_id: int
    ) -> DataFrame:
        """
        Returns a list of run on an existing milestones,
        including those runs in sub-milestones and plans.

        :param milestone_ids:
        :param project_id:
            The ID of the project
        :return: DataFrame
        """
        def get_runs(*mile_ids):
            dataframes = []
            for mid in mile_ids:
                # Get all run
                df_run1 = self.to_dataframe(project_id=project_id, milestone_id=mid)
                if df_run1.shape[0] > 0:
                    dataframes.append(df_run1)
                # Get all plan
                plans = Plans(self._session).get_plans(project_id=project_id, milestone_id=mid)
                plan_ids = [plan['id'] for plan in plans]
                df_run2 = self.dataframe_from_plan(*plan_ids)
                if df_run2.shape[0] > 0:
                    dataframes.append(df_run2)
            return dataframes

        dfs = get_runs(milestone_ids)
        milestone = Milestones(self._session)
        df_milestone = milestone.sub_milestones_to_dataframe(*milestone_ids).filter(['id'])
        dfs.extend(get_runs(*df_milestone['id'].to_list()))
        return pd.concat(dfs).reset_index(drop=False)

    def get_runs_by_plan(self, *plan_ids: int) -> list:
        """
        Returns a list of run on an existing test plan.

        param plan_ids:
            The ID or IDs of the test plan
        :return: response
        """
        entries = [Plans(self._session).get_plan(plan_id)['entries'] for plan_id in plan_ids]
        return [x3 for x0 in entries for x1 in x0 for x3 in x1['runs']]

    @auto_offset
    def to_dataframe(self, project_id: int, **kwargs) -> DataFrame:
        """
        Returns a List of test runs for a project as DataFrame. Only returns those test runs that
        are not part of a test plan (please see get_plans/get_plan for this)

        :param project_id: int
            The ID of the project
        :param kwargs: filters
            :key created_after: int/datetime
                Only return test runs created after this date (as UNIX timestamp).
            :key created_before: int/datetime
                Only return test runs created before this date (as UNIX timestamp).
            :key created_by: List[int] or comma-separated string
                A comma-separated list of creators (user IDs) to filter by.
            :key is_completed: int/bool
                1/True to return completed test runs only.
                0/False to return active test runs only.
            :key limit/offset: int
                Limit the result to :limit test runs. Use :offset to skip records.
            :key milestone_id: List[int] or comma-separated string
                A comma-separated list of milestone IDs to filter by.
            :key refs_filter: str
                A single Reference ID (e.g. TR-a, 4291, etc.)
            :key suite_id: List[int] or comma-separated string
                A comma-separated list of test suite IDs to filter by.
        :return: DataFrame
        """
        return DataFrame(self.get_runs(project_id, **kwargs))

    def dataframe_from_plan(self, *plan_ids: int) -> DataFrame:
        """
        Returns a list of run on an existing test plan as Dataframe

        :param plan_ids:
            The ID or IDs of the test plan
        :return: response
        """
        return pd.DataFrame(self.get_runs_by_plan(*plan_ids))


class Plans(TR_Plans):

    @auto_offset
    def to_dataframe(self, project_id: int, **kwargs) -> DataFrame:
        """
        Returns a list of test plans for a project in DataFrame

        This method will return all entries in the response array.
        To retrieve additional entries, you can make additional requests
        using the offset filter described in the Request filters section below.

        :param project_id:
            The ID of the project
        :param kwargs: filters
            :key created_after: int/datetime
                Only return test plans created after this date (as UNIX timestamp).
            :key created_before: int/datetime
                Only return test plans created before this date (as UNIX timestamp).
            :key created_by: List[int] or comma-separated string
                A comma-separated list of creators (user IDs) to filter by.
            :key is_completed: int/bool
                1/True to return completed test plans only.
                0/False to return active test plans only.
            :key limit/offset: int
                Limit the result to :limit test plans. Use :offset to skip records.
            :key milestone_id: List[int] or comma-separated string
                A comma-separated list of milestone IDs to filter by.
        :return: response
        """
        return DataFrame(self.get_plans(project_id, **kwargs))


class Cases(TR_Cases):

    def to_dataframe(self, project_id: int, suite_id: int, with_meta=False, **kwargs):
        """
        Returns a list of test cases for a project or specific test suite in DataFrame
        (if the project has multiple suites enabled).

        :param project_id:
            The ID of the project
        :param suite_id: int
            The ID of the test suite (optional if the project is operating in
            single suite mode)
        :param with_meta: boolean
            ID's field will be filled up with new columns
        :param kwargs:
            :key created_after: int/datetime
                Only return test cases created after this date (as UNIX timestamp).
            :key created_before: int/datetime
                Only return test cases created before this date (as UNIX timestamp).
            :key created_by: List[int] or comma-separated string
                A comma-separated list of creators (user IDs) to filter by.
            :key filter: str
                Only return cases with matching filter string in the case title
            :key limit: int
                The number of test cases the response should return
                (The response size is 250 by default) (requires TestRail 6.7 or later)
            :key milestone_id: List[int] or comma-separated string
                A comma-separated list of milestone IDs to filter by (not available
                if the milestone field is disabled for the project).
            :key offset: int
                Where to start counting the tests cases from (the offset)
                (requires TestRail 6.7 or later)
            :key priority_id: List[int] or comma-separated string
                A comma-separated list of priority IDs to filter by.
            :key refs: str
                A single Reference ID (e.g. TR-1, 4291, etc.)
                (requires TestRail 6.5.2 or later)
            :key section_id: int
                The ID of a test case section
            :key template_id: List[int] or comma-separated string
                A comma-separated list of template IDs to filter by
                (requires TestRail 5.2 or later)
            :key type_id: List[int] or comma-separated string
                A comma-separated list of case type IDs to filter by.
            :key updated_after: int/datetime
                Only return test cases updated after this date (as UNIX timestamp).
            :key updated_before: int/datetime
                Only return test cases updated before this date (as UNIX timestamp).
            :key updated_by: List[int] or comma-separated string
                A comma-separated list of user IDs who updated test cases to filter by.
        :return: DataFrame
        """
        df = DataFrame(self.get_cases(project_id, suite_id=suite_id, **kwargs))
        if with_meta:
            meta = Metas(self._session)
            meta.fill_id_fields(project_id, suite_id, df)
            meta.fill_custom_fields(project_id, df)
        return df


class Tests(TR_Tests):
    def to_dataframe(self, *run_ids: int, with_meta=False, **kwargs) -> Optional[DataFrame]:
        """
        Returns single or multiple test run.

        :param run_ids:
             The ID or IDs of the test run(s)
        :param with_meta:
            True to fill up template_id, type_id, priority_id with their respective name
        :param kwargs:
        :return: DataFrame

        Examples
        --------
        #> run_ids = [2,3,4]
        #> df = api.tests.to_dataframe(*run_ids, with_meta=True)

        OR
        #> df = api.tests.to_dataframe(2,3,4, with_meta=True)
        """
        dfs = []
        for run_id in run_ids:
            df = DataFrame(self.get_tests(run_id, **kwargs))
            run = Runs(self._session).get_run(run_id)
            project_id = run['project_id']
            if with_meta:
                meta = Metas(self._session)
                meta.fill_id_fields(project_id, 0, df)
                meta.fill_custom_fields(project_id, df)
            dfs.append(df)
        return pd.concat(dfs).reset_index(drop=True) if dfs else None


class Milestones(TR_Milestone):
    def get_sub_milestones(self, *milestone_ids) -> list:
        """
        Returns sub milestones of a milestone if any.

        :param milestone_ids:
            The ID or IDs of the milestone
        :return: response
        """
        subs = [self.get_milestone(mid)['milestones'] for mid in milestone_ids]
        return [sub0 for sub in subs for sub0 in sub]

    def sub_milestones_to_dataframe(self, *milestone_ids: int) -> DataFrame:
        """
        Returns sub milestones of a milestone if any in a DataFrame.

        :param milestone_ids:
            The ID or IDs of the milestone
        :return: response
        """
        return DataFrame(self.get_sub_milestones(*milestone_ids))


class Sections(TR_Sections):
    def to_dataframe(self, project_id: int, suite_id: int, **kwargs) -> DataFrame:
        """
         Returns a list of sections for a project and test suite in DataFrame

        :param project_id:
            The ID of the project
        :param suite_id:
            The ID of the test suite
        :param kwargs:
            :key offset: int
                Where to start counting the sections from (the offset)
                (requires TestRail 6.7 or later)
        :return:
        """
        return DataFrame(self.get_sections(project_id=project_id, suite_id=suite_id, **kwargs))

    def get_sections_lookup(self, project_id: int, suite_id: int) -> dict:
        """
         Returns a lookup map for each sections as follow:

         {
            <SECTION_ID>: <SECTION_NAME>
            ...
         }

        :param project_id:
            The ID of the project
        :param suite_id:
            The ID of the test suite
        :return:
        """
        df = self.to_dataframe(project_id, suite_id)
        return dict(zip(df['id'], df['name']))


class Template(TR_Template):
    def to_dataframe(self, project_id: int) -> DataFrame:
        """
        Returns a list of available templates (requires TestRail 5.2 or later) in DataFrame

        :param project_id:
            The ID of the project
        :return:
        """
        return pd.DataFrame(self.get_templates(project_id))

    def get_template_lookup(self, project_id: int) -> dict:
        """
        Returns a lookup map for each template as follow:

         {
            <TEMPLATE_ID>: <TEMPLATE_NAME>
            ...
         }
        :param project_id:
            The ID of the project
        :return:
        """
        df = self.to_dataframe(project_id)
        return dict(zip(df['id'], df['name']))


class CaseFields(TR_CaseFields):
    def get_configs(self) -> dict:
        """
        Return a map for case field with following structure:

        {
            {<SYSTEM_NAME>: {<PROJECT_ID>: {<TYPE_ID>: <VALUE>}}
        }

        :return:
        """
        df = DataFrame(self.get_case_fields()).filter(['system_name', 'configs'])

        def get_df_by_system_name(name: str):
            df_config = pd.DataFrame(df.query(f'system_name == "{name}"')['configs'].to_list()[0])
            df_context = pd.DataFrame(df_config['context'].to_list())
            df_option = pd.DataFrame(df_config['options'].to_list())
            df_merged = df_context.join(df_option)
            return df_merged

        def split_by_comma(i: str, index):
            if i:
                items = i.split(',')
                return int(items[index]) if items[index].isnumeric() else items[index]
            return 0

        lookup = {}
        for _, row_i in df.iterrows():
            system_name = row_i['system_name']
            options = {}
            lookup[system_name] = options
            for _, row_j in get_df_by_system_name(system_name).iterrows():
                if 'items' in row_j:
                    for pid in row_j['project_ids']:
                        options[pid] = {split_by_comma(r, 0): split_by_comma(r, 1)
                                        for r in row_j['items'].split('\n')}
                options.update({None: '', '': ''})

        return lookup


class CaseTypes(TR_CaseType):
    def to_dataframe(self) -> DataFrame:
        """
        Returns a list of available case types.

        The response includes an array of test case types.
        Each case type has a unique ID and a name.
        The is_default field is true for the default case type and false otherwise.

        :return: DataFrame
        """
        return DataFrame(self.get_case_types())

    def get_case_types_lookup(self) -> dict:
        """
        Return a dictionary which mapped with `id` and `name`
        :return:
        """
        df = self.to_dataframe()
        return dict(zip(df['id'], df['name']))


class Priorities(TR_Priorities):
    def to_dataframe(self) -> DataFrame:
        return DataFrame(self.get_priorities())

    def get_priorities_lookup(self) -> dict:
        df = self.to_dataframe()
        return dict(zip(df['id'], df['name']))


class Results(TR_Results):

    @auto_offset
    def dataframe_from_case(self, run_id: int, case_id: int, **kwargs) -> DataFrame:
        """
        Returns a list of test results for a test run and case combination in Dataframe

        :param run_id:
            The ID of the test run
        :param case_id:
            The ID of the test case
        :param kwargs:
            :key offset: int
                unsupported due to reserve for auto pagination feature
            :key limit: int
                unsupported due to reserve for auto pagination feature
            :key defects_filter: str
                A single Defect ID (e.g. TR-1, 4291, etc.)
            :key status_id: List[int] or comma-separated string
                A comma-separated list of status IDs to filter by.
        :return: DataFrame
        """
        return DataFrame(self.get_results_for_case(run_id, case_id, **kwargs))

    @auto_offset
    def dataframe_from_test(self, test_id: int, **kwargs) -> DataFrame:
        """
        Returns a list of test results for a test as DataFrame

        :param test_id:
            The ID of the test
        :param kwargs: filters
            :key defects_filter: str
                A single Defect ID (e.g. TR-1, 4291, etc.)
            :key status_id: List[int] or comma-separated string
                A comma-separated list of status IDs to filter by.
        :return: DataFrame
        """
        return DataFrame(self.get_results(test_id, **kwargs))

    @auto_offset
    def dataframe_from_run(self, run_id: int, **kwargs) -> DataFrame:
        """
        Returns a list of test results for a test run.
        This method will return up to all entries in the response array.

        :param run_id:
            The ID of the test run
        :param kwargs: filters
            :key created_after: int/datetime
                Only return test results created after this date.
            :key created_before: int/datetime
                Only return test results created before this date.
            :key created_by: List[int] or comma-separated string
                A comma-separated list of creators (user IDs) to filter by.
            :key defects_filter: str
                A single Defect ID (e.g. TR-1, 4291, etc.)
            :key status_id: List[int] or comma-separated string
                A comma-separated list of status IDs to filter by.
        :return: DataFrame
        """
        return DataFrame(self.get_results_for_run(run_id, **kwargs))

    def dataframe_from_runs(self, *run_ids: int, **kwargs) -> DataFrame:
        """
        Returns a list of test results for one or many test runs.
        This method will return up to all entries in the response array.

        :param run_ids:
            The ID or IDs of the test run(s)
        :param kwargs: filters
            :key created_after: int/datetime
                Only return test results created after this date.
            :key created_before: int/datetime
                Only return test results created before this date.
            :key created_by: List[int] or comma-separated string
                A comma-separated list of creators (user IDs) to filter by.
            :key defects_filter: str
                A single Defect ID (e.g. TR-1, 4291, etc.)
            :key status_id: List[int] or comma-separated string
                A comma-separated list of status IDs to filter by.
        :return: DataFrame
        """
        dfs = [self.dataframe_from_run(run_id, **kwargs) for run_id in run_ids]
        return pd.concat(dfs).reset_index(drop=True) if dfs else None

    def dataframe_from_milestone(self, project_id: int, *milestone_ids: int, **kwargs) -> DataFrame:
        """
        Returns a list of test results from milestone(s) which contains run(s).
        This method will return up to all entries in the response array.

        :param project_id:
            The ID of the project
        :param milestone_ids:
            The ID or IDs of the milestone(s)
        :param kwargs: filters
            :key created_after: int/datetime
                Only return test results created after this date.
            :key created_before: int/datetime
                Only return test results created before this date.
            :key created_by: List[int] or comma-separated string
                A comma-separated list of creators (user IDs) to filter by.
            :key defects_filter: str
                A single Defect ID (e.g. TR-1, 4291, etc.)
            :key status_id: List[int] or comma-separated string
                A comma-separated list of status IDs to filter by.
        :return:
        """
        results = []
        for milestone_id in milestone_ids:
            df_runs = Runs(self._session).to_dataframe(
                project_id=project_id, milestone_id=milestone_id)
            _ = [results.append(self.dataframe_from_run(run_id, **kwargs))
                 for run_id in df_runs['id'].to_list()]
        return pd.concat(results).reset_index(drop=True) if results else None


class Suites(TR_Suites):
    def to_dataframe(self, project_id: int) -> DataFrame:
        """
        Returns a list of test suites for a project in DataFrame.

        :param project_id:
            The ID of the project
        :return: DataFrame
        """
        return DataFrame(self.get_suites(project_id))

    def get_suites_lookup(self, project_id: int) -> dict:
        """
        A Suite dictionary lookup per project for suite_id to suite_name mapping.

        :param project_id:
            The ID of the project
        :return: dict

        Examples
        --------
        {
            1: 'suite_name1',
            2: 'suite_name2,
        }
        """
        df = self.to_dataframe(project_id)
        return dict(zip(df['id'], df['name']))


class Statuses(TR_Statuses):
    def to_dataframe(self) -> DataFrame:
        """
        Returns a list of available test statuses in DataFrame

        :return: DataFrame
        """
        return DataFrame(self.get_statuses())

    def get_statuses_lookup(self, column='name') -> dict:
        """
        A dictionary lookup for all statuses.

        :param column:
            Refer https://www.gurock.com/testrail/docs/api/reference/statuses/ for list of columns.
            Default is `name`, commonly switch with `label`.
        :return:
        """
        df = self.to_dataframe()
        return dict(zip(df['id'], df[column]))
