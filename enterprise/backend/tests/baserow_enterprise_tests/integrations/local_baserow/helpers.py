from django.contrib.auth.hashers import make_password

from baserow.core.user_sources.registries import user_source_type_registry
from baserow_enterprise.integrations.local_baserow.models import (
    LocalBaserowPasswordAppAuthProvider,
)


def populate_local_baserow_test_data(data_fixture, role_name=""):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    builder = data_fixture.create_builder_application(user=user, workspace=workspace)
    published_builder = data_fixture.create_builder_application(workspace=None)
    domain = data_fixture.create_builder_custom_domain(
        builder=builder, published_to=published_builder
    )
    database = data_fixture.create_database_application(workspace=workspace)
    data_fixture.create_database_table(database=database)
    integration = data_fixture.create_local_baserow_integration(
        application=published_builder, user=user
    )

    table, fields, rows = data_fixture.build_table(
        user=user,
        columns=[
            ("Email", "text"),
            ("Name", "text"),
            ("Password", "text"),
            ("Role", "text"),
        ],
        rows=[
            ["test@baserow.io", "Test", make_password("super not secret"), role_name],
            ["test2@baserow.io", "Test2", make_password("super not secret"), role_name],
            ["test3@baserow.io", "Test3", make_password("super not secret"), role_name],
            ["test4@baserow.io", "Test4", None, role_name],
        ],
    )

    email_field, name_field, password_field, role_field = fields

    local_baserow_user_source_type = user_source_type_registry.get("local_baserow")

    user_source = data_fixture.create_user_source(
        local_baserow_user_source_type.model_class,
        application=published_builder,
        integration=integration,
        table=table,
        email_field=email_field,
        name_field=name_field,
        role_field=role_field,
    )

    app_auth_provider = data_fixture.create_app_auth_provider(
        LocalBaserowPasswordAppAuthProvider,
        user_source=user_source,
        password_field=password_field,
    )

    return {
        "user_source": user_source,
        "auth_provider": app_auth_provider,
        "domain": domain,
        "user_table": table,
    }
