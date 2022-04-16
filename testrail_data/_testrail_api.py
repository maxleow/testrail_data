from testrail_api import TestRailAPI as TRApi
from testrail_data._category import Runs, Plans, Results, Milestones


class TestRailAPI(TRApi):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def runs(self) -> Runs:
        return Runs(self)

    @property
    def plans(self) -> Plans:
        return Plans(self)

    @property
    def results(self) -> Results:
        return Results(self)

    @property
    def milestones(self) -> Milestones:
        return Milestones(self)