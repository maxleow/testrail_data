import responses


def get_plans(size):
    return [{'id': i, 'name': 'System test'} for i in range(0, size)]


@responses.activate
def test_to_dataframe(api, host):
    responses.add(
        responses.GET,
        '{}index.php?/api/v2/get_plan/5&offset=0'.format(host),
        json=get_plans(250)
    )

    responses.add(
        responses.GET,
        '{}index.php?/api/v2/get_plan/5&offset=250'.format(host),
        json=get_plans(250)
    )

    responses.add(
        responses.GET,
        '{}index.php?/api/v2/get_plan/5&offset=500'.format(host),
        json=get_plans(200)
    )

    df = api.plans.to_dataframe(5)

    assert len(responses.calls) == 3
    assert df.shape == (700, 2)