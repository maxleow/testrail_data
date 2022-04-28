import time
from testrail_api._category import Runs as TR_Runs
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
import requests
from requests.exceptions import ConnectionError
from pandas import DataFrame
import pandas as pd

page_size = 250
retry_total = 5
retry_sleep = 2


def auto_offset(f):
    def wrap(*args, **kwargs):
        offset = 0
        if kwargs.get('offset'):
            assert False, 'offset has been auto managed'
        df = f(*args, **kwargs, offset=offset)
        data_size = df.shape[0]
        frames = [df]
        while data_size == page_size:
            offset += page_size
            df2 = f(*args, **kwargs, offset=offset)
            data_size = df2.shape[0]
            frames.append(df2)
        return pd.concat(frames, sort=False)

    return wrap


def retry(f):
    """
    Handle requests.exceptions.ConnectionError by establishing new connection
    :return: wrapper function
    """
    def wrap(*args, **kwargs):
        trial = retry_total
        while trial > 0:
            try:
                return f(*args, **kwargs)
            except ConnectionError:
                sf = args[0]
                auth = sf.__session.auth
                verify = sf.__session.verify
                sf.__session = requests.Session()
                sf.__session.headers["User-Agent"] = sf._user_agent
                sf.__session.headers.update(kwargs.get("headers", {}))
                sf.__session.verify = verify
                sf.__session.auth = auth
                trial -= 1
                if trial == 0:
                    raise
                time.sleep(retry_sleep)
                continue

    return wrap


def fill_custom_fields(project_id: int, df: DataFrame, lookup_case_field: dict):
    def fill(x, column):
        try:
            lookup_custom_field = lookup_case_field[column]
            if not x or project_id not in lookup_custom_field:
                return ''
            elif isinstance(x, list):
                labels = [lookup_custom_field[project_id][i] for i in x]
                return ','.join(labels)
            elif isinstance(x, float) or str(x).isnumeric():
                if str(x) == 'nan':
                    return ''
                x = int(x)
                return lookup_custom_field[project_id][x]
            return lookup_custom_field[project_id][x]
        except KeyError:
            print(column, x, type(x))
            return f'UNKNOWN {x}'

    for col in [c for c in df.columns if 'custom_' in c]:
        df[col] = df[col].apply(fill, column=col)


class Runs(TR_Runs):

    @auto_offset
    def to_dataframe(self, project_id: int, **kwargs) -> DataFrame:
        return DataFrame(self.get_runs(project_id, **kwargs))

    def dataframe_from_plan(self, plan_id: int) -> DataFrame:
        plan = Plans(self._session).get_plan(plan_id)
        entries = plan['entries']
        runs = [run for entry in entries for run in entry['runs']]
        return pd.DataFrame(runs)


class Plans(TR_Plans):

    @auto_offset
    def to_dataframe(self, project_id: int, **kwargs) -> DataFrame:
        return DataFrame(self.get_plans(project_id, **kwargs))


class Cases(TR_Cases):
    def to_dataframe(self, project_id: int, suite_id: int, with_meta=False, **kwargs):
        df = DataFrame(self.get_cases(project_id, suite_id=suite_id, **kwargs))
        if with_meta:
            lookup_section = Sections(self._session).get_sections_lookup(project_id, suite_id)
            df['section_name'] = df['section_id'].apply(lambda x: lookup_section[x])

            lookup_template = Template(self._session).get_template_lookup(project_id)
            df['template_name'] = df['template_id'].apply(lambda x: lookup_template[x])

            lookup_case_type = CaseTypes(self._session).get_case_types_lookup()
            df['type_name'] = df['type_id'].apply(lambda x: lookup_case_type[x])

            lookup_priority = Priorities(self._session).get_priorities_lookup()
            df['priority_name'] = df['priority_id'].apply(lambda x: lookup_priority[x])

            lookup_suite = Suites(self._session).get_suites_lookup(project_id)
            df['suite_name'] = df['suite_id'].apply(lambda x: lookup_suite[x])

            lookup_case_field = CaseFields(self._session).get_configs()
            fill_custom_fields(project_id, df, lookup_case_field)

        return df


class Tests(TR_Tests):
    def to_dataframe(self, run_id: int, with_meta=False, **kwargs) -> DataFrame:
        df = DataFrame(self.get_tests(run_id, **kwargs))
        run = Runs(self._session).get_run(run_id)
        project_id = run['project_id']
        if with_meta:
            lookup_template = Template(self._session).get_template_lookup(project_id)
            df['template_name'] = df['template_id'].apply(lambda x: lookup_template[x])

            lookup_case_type = CaseTypes(self._session).get_case_types_lookup()
            df['type_name'] = df['type_id'].apply(lambda x: lookup_case_type[x])

            lookup_priority = Priorities(self._session).get_priorities_lookup()
            df['priority_name'] = df['priority_id'].apply(lambda x: lookup_priority[x])

            lookup_case_field = CaseFields(self._session).get_configs()
            fill_custom_fields(project_id, df, lookup_case_field)
        return df


class Milestones(TR_Milestone):

    def get_sub_milestones(self, milestone_id: int) -> dict:
        sub_mile = self.get_milestone(milestone_id)['milestones']
        for mile in sub_mile:
            sub_mile.extend(
                self.get_sub_milestones(mile['id'])
            )
        return sub_mile

    def sub_milestones_to_dataframe(self, milestone_id: int):
        return DataFrame(self.get_sub_milestones(milestone_id))


class Sections(TR_Sections):
    def to_dataframe(self, project_id: int, suite_id: int, **kwargs) -> DataFrame:
        return DataFrame(self.get_sections(project_id=project_id, suite_id=suite_id, **kwargs))

    def get_sections_lookup(self, project_id: int, suite_id: int) -> dict:
        df = self.to_dataframe(project_id, suite_id)
        return dict(zip(df['id'], df['name']))


class Template(TR_Template):
    def to_dataframe(self, project_id: int) -> DataFrame:
        return pd.DataFrame(self.get_templates(project_id))

    def get_template_lookup(self, project_id: int) -> dict:
        df = self.to_dataframe(project_id)
        return dict(zip(df['id'], df['name']))


class CaseFields(TR_CaseFields):
    def get_configs(self) -> dict:
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
        return DataFrame(self.get_case_types())

    def get_case_types_lookup(self) -> dict:
        df = self.to_dataframe()
        return dict(zip(df['id'], df['name']))


class Priorities(TR_Priorities):
    def to_dataframe(self) -> DataFrame:
        return DataFrame(self.get_priorities())

    def get_priorities_lookup(self) -> dict:
        df = self.to_dataframe()
        return dict(zip(df['id'], df['name']))


class Results(TR_Results):

    @retry
    def get_results_for_run(self, run_id: int, limit: int = 250, offset: int = 0, **kwargs):
        return super().get_results_for_run(run_id, limit, offset, **kwargs)

    @auto_offset
    def dataframe_from_case(self, run_id: int, case_id: int, **kwargs) -> DataFrame:
        return DataFrame(self.get_results_for_case(run_id, case_id, **kwargs))

    @auto_offset
    def dataframe_from_test(self, test_id: int, **kwargs) -> DataFrame:
        return DataFrame(self.get_results(test_id, **kwargs))

    @auto_offset
    def dataframe_from_run(self, run_id: int, **kwargs) -> DataFrame:
        print(run_id, kwargs)
        return DataFrame(self.get_results_for_run(run_id, **kwargs))

    def dataframe_from_milestone(self, project_id: int, milestone_id: int, **kwargs):
        df_runs = Runs(self._session).to_dataframe(
            project_id=project_id, milestone_id=milestone_id)
        print(df_runs)
        results = [self.dataframe_from_run(run_id, **kwargs) for run_id in df_runs['id'].to_list()]
        return pd.concat(results, sort=False)


class Suites(TR_Suites):
    def to_dataframe(self, project_id: int):
        return DataFrame(self.get_suites(project_id))

    def get_suites_lookup(self, project_id: int) -> dict:
        df = self.to_dataframe(project_id)
        return dict(zip(df['id'], df['name']))


class Statuses(TR_Statuses):
    def to_dataframe(self) -> DataFrame:
        return DataFrame(self.get_statuses())

    def get_statuses_lookup(self, column='name') -> dict:
        df = self.to_dataframe()
        return dict(zip(df['id'], df[column]))
