import responses


def get_result(size=1):
    return [{'id': i, 'status_id': 2, 'test_id': 1} for i in range(0, size)]


@responses.activate
def test_dataframe_from_case_when_has_record(api, host):
    responses.add(
        responses.GET,
        '{}index.php?/api/v2/get_results_for_case/23/2567&limit=250&offset=0'.format(host),
        json=get_result(249), status=200)

    df = api.results.dataframe_from_case(23, 2567)

    assert len(responses.calls) == 1
    assert df['status_id'][0] == 2
    assert df.shape == (249, 3)


@responses.activate
def test_dataframe_from_case_when_has_no_record(api, host):
    responses.add(
        responses.GET,
        '{}index.php?/api/v2/get_results_for_case/23/2567&limit=250&offset=0'.format(host),
        json=[], status=200)

    df = api.results.dataframe_from_case(23, 2567)
    assert df.shape[0] == 0


@responses.activate
def test_dataframe_from_test_when_has_no_record(api, host):
    responses.add(
        responses.GET,
        '{}index.php?/api/v2/get_results/221&limit=250&offset=0'.format(host),
        json=[], status=200)

    df = api.results.dataframe_from_test(221)
    assert df.shape[0] == 0


@responses.activate
def test_dataframe_from_test_when_has_record(api, host):
    responses.add(
        responses.GET,
        '{}index.php?/api/v2/get_results/221&limit=250&offset=0'.format(host),
        json=get_result(250), status=200)

    responses.add(
        responses.GET,
        '{}index.php?/api/v2/get_results/221&limit=250&offset=250'.format(host),
        json=get_result(5), status=200)

    df = api.results.dataframe_from_test(221)

    assert len(responses.calls) == 2
    assert len(df['status_id'].unique()) == 1
    assert df.shape == (255, 3)


@responses.activate
def test_dataframe_from_run_when_has_record(api, host):
    responses.add(
        responses.GET,
        '{}index.php?/api/v2/get_results_for_run/12&limit=250&offset=0'.format(host),
        json=get_result(), status=200)

    df = api.results.dataframe_from_run(12)

    assert df['status_id'][0] == 2
    assert df.shape[0] == 1


@responses.activate
def test_dataframe_from_run_when_has_no_record(api, host):
    responses.add(
        responses.GET,
        '{}index.php?/api/v2/get_results_for_run/12&limit=250&offset=0'.format(host),
        json=[], status=200)

    df = api.results.dataframe_from_run(12)

    assert df.shape[0] == 0


@responses.activate
def test_dataframe_from_milestone_when_has_record(api, host):
    responses.add(
        responses.GET,
        '{}index.php?/api/v2/get_runs/9&milestone_id=1&offset=0'.format(host),
        json=[{'id': 1, 'name': 'My run', 'is_completed': 0}]
    )

    responses.add(
        responses.GET,
        '{}index.php?/api/v2/get_results_for_run/1&limit=250&offset=0'.format(host),
        json=get_result(), status=200
    )

    print(responses.calls)

    df = api.results.dataframe_from_milestone(9,1)

    assert df['status_id'][0] == 2
    assert df.shape[0] == 1