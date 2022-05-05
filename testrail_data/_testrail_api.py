import requests
from testrail_api import TestRailAPI as TRApi
from testrail_data._category import (
    Runs,
    Plans,
    Results,
    Milestones,
    Cases,
    CaseFields,
    Sections,
    Template,
    CaseTypes,
    Priorities,
    Suites,
    Statuses,
    Tests,
    Metas,
)


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
    def cases(self) -> Cases:
        return Cases(self)

    @property
    def milestones(self) -> Milestones:
        return Milestones(self)

    @property
    def case_fields(self) -> CaseFields:
        return CaseFields(self)

    @property
    def sections(self) -> Sections:
        return Sections(self)

    @property
    def templates(self) -> Template:
        return Template(self)

    @property
    def case_types(self) -> CaseTypes:
        return CaseTypes(self)

    @property
    def priorities(self) -> Priorities:
        return Priorities(self)

    @property
    def suites(self) -> Suites:
        return Suites(self)

    @property
    def statuses(self) -> Statuses:
        return Statuses(self)

    @property
    def tests(self) -> Tests:
        return Tests(self)

    @property
    def metas(self) -> Metas:
        return Metas(self)