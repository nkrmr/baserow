import pytest


@pytest.mark.django_db
@pytest.mark.parametrize("view_type", ["kanban", "calendar"])
def test_new_fields_are_hidden_by_default_in_premium_views_if_public(
    view_type, premium_data_fixture
):
    user = premium_data_fixture.create_user()
    table = premium_data_fixture.create_database_table(user=user)
    premium_data_fixture.create_text_field(table=table)

    # NOTE: every time we create a kanban or a calendar, a single select field
    # or a date field is created respectively
    create_view_func = getattr(premium_data_fixture, f"create_{view_type}_view")
    public_view = create_view_func(table=table, public=True, create_options=False)

    options = public_view.get_field_options()
    assert len(options) == 0

    options = public_view.get_field_options(create_if_missing=True)
    assert len(options) == 2
    assert options[0].hidden is True
    assert options[1].hidden is True

    private_view = create_view_func(table=table, create_options=False)

    options = private_view.get_field_options()
    assert len(options) == 0
    options = private_view.get_field_options(create_if_missing=True)
    assert len(options) == 3
    assert options[0].hidden is False
    assert options[1].hidden is False
    assert options[2].hidden is False


@pytest.mark.django_db
@pytest.mark.parametrize("view_type", ["kanban", "calendar"])
def test_new_fields_are_hidden_by_default_in_premium_views_if_other_fields_are_hidden(
    view_type, premium_data_fixture
):
    user = premium_data_fixture.create_user()
    table = premium_data_fixture.create_database_table(user=user)
    premium_data_fixture.create_text_field(table=table)

    create_view_func = getattr(premium_data_fixture, f"create_{view_type}_view")
    view = create_view_func(table=table, create_options=False)

    options = view.get_field_options(create_if_missing=True)
    assert len(options) == 2
    assert options[0].hidden is False
    assert options[1].hidden is False

    # If we create another field now, the new field will be visible
    premium_data_fixture.create_text_field(table=table)
    options = view.get_field_options(create_if_missing=True)
    assert len(options) == 3
    assert options[0].hidden is False
    assert options[1].hidden is False
    assert options[2].hidden is False

    # If we hide a field, a new field will be hidden by default
    options[0].hidden = True
    options[0].save()

    premium_data_fixture.create_text_field(table=table)
    options = view.get_field_options(create_if_missing=True)
    assert len(options) == 4
    assert options[0].hidden is True
    assert options[1].hidden is False
    assert options[2].hidden is False
    assert options[3].hidden is True
