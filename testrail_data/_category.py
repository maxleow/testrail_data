from testrail_api._category import Runs as TR_Runs
from testrail_api._category import Plans as TR_Plans
from testrail_api._category import Results as TR_Results
from testrail_api._category import Milestones as TR_Milestone
from testrail_api._category import Cases as TR_Cases
from testrail_api._category import Tests as TR_Tests

from pandas import DataFrame
import pandas as pd

limit = 250


def auto_offset(limit_size):
    def walk(f):

        def wrap(*args, **kwargs):
            offset = 0
            if kwargs.get('offset'):
                assert False, 'offset has been auto managed'
            df = f(*args, **kwargs, offset=offset)
            data_size = df.shape[0]
            frames = [df]
            while data_size == limit_size:
                offset += limit_size
                df2 = f(*args, **kwargs, offset=offset)
                data_size = df2.shape[0]
                frames.append(df2)
            return pd.concat(frames, sort=False)

        return wrap

    return walk


class Runs(TR_Runs):

    @auto_offset(limit)
    def to_dataframe(self, project_id: int, **kwargs) -> DataFrame:
        return DataFrame(self.get_runs(project_id, **kwargs))

    def dataframe_from_plan(self, plan_id: int) -> DataFrame:
        plan = Plans(self._session).get_plan(plan_id)
        entries = plan['entries']
        runs = [run for entry in entries for run in entry['runs']]
        return pd.DataFrame(runs)


class Plans(TR_Plans):

    @auto_offset(limit)
    def to_dataframe(self, project_id: int, **kwargs) -> DataFrame:
        return DataFrame(self.get_plans(project_id, **kwargs))


class Cases(TR_Cases):
    pass


class Milestones(TR_Milestone):

    def get_sub_milestones(self, milestone_id: int):
        sub_mile = self.api.milestones.get_milestone(milestone_id)['milestones']
        for mile in sub_mile:
            sub_mile.extend(
                self.get_sub_milestones(mile['id'])
            )
        return sub_mile


class Results(TR_Results):

    @auto_offset(limit)
    def dataframe_from_case(self, run_id: int, case_id: int, **kwargs) -> DataFrame:
        return DataFrame(self.get_results_for_case(run_id, case_id, **kwargs))

    @auto_offset(limit)
    def dataframe_from_test(self, test_id: int, **kwargs) -> DataFrame:
        return DataFrame(self.get_results(test_id, **kwargs))

    @auto_offset(limit)
    def dataframe_from_run(self, run_id: int, **kwargs) -> DataFrame:
        print(run_id, kwargs)
        return DataFrame(self.get_results_for_run(run_id, **kwargs))

    def dataframe_from_milestone(self, project_id: int, milestone_id: int, **kwargs):
        df_runs = Runs(self._session).to_dataframe(
            project_id=project_id, milestone_id=milestone_id)
        print(df_runs)
        results = [self.dataframe_from_run(id, **kwargs) for id in df_runs['id'].to_list()]
        return pd.concat(results, sort=False)
