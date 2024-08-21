from collections import defaultdict
from unittest.mock import MagicMock, patch

from django.urls import reverse

import pytest
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from baserow.api.exceptions import RequestBodyValidationException
from baserow.contrib.builder.domains.handler import DomainHandler
from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.table.exceptions import TableDoesNotExist
from baserow.contrib.database.table.handler import TableHandler
from baserow.core.app_auth_providers.models import AppAuthProvider
from baserow.core.user.exceptions import UserNotFound
from baserow.core.user_sources.exceptions import UserSourceImproperlyConfigured
from baserow.core.user_sources.handler import UserSourceHandler
from baserow.core.user_sources.registries import (
    DEFAULT_USER_ROLE_PREFIX,
    user_source_type_registry,
)
from baserow.core.utils import MirrorDict, Progress
from baserow_enterprise.integrations.local_baserow.models import LocalBaserowUserSource
from baserow_enterprise.integrations.local_baserow.user_source_types import (
    LocalBaserowUserSourceType,
)

from .helpers import populate_local_baserow_test_data


@pytest.fixture(autouse=True)
def enable_enterprise_for_all_tests_here(enable_enterprise):
    pass


@pytest.mark.django_db
def test_get_user_sources(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    application = data_fixture.create_builder_application(workspace=workspace)
    database = data_fixture.create_database_application(workspace=workspace)
    data_fixture.create_database_table(database=database)
    integration = data_fixture.create_local_baserow_integration(application=application)

    table, fields, rows = data_fixture.build_table(
        user=user,
        columns=[
            ("Email", "text"),
            ("Name", "text"),
            ("Role", "text"),
        ],
        rows=[
            ["test@baserow.io", "Test", ""],
        ],
    )

    email_field, name_field, role_field = fields

    local_baserow_user_source_type = user_source_type_registry.get("local_baserow")

    user_source1 = data_fixture.create_user_source(
        local_baserow_user_source_type.model_class,
        application=application,
        integration=integration,
        table=table,
        email_field=email_field,
        name_field=name_field,
        role_field=role_field,
    )

    user_source2 = data_fixture.create_user_source(
        local_baserow_user_source_type.model_class,
        application=application,
        integration=integration,
        table=table,
        email_field=email_field,
    )

    user_source3 = data_fixture.create_user_source(
        local_baserow_user_source_type.model_class,
        application=application,
        integration=integration,
        table=table,
    )

    url = reverse("api:user_sources:list", kwargs={"application_id": application.id})
    response = api_client.get(
        url,
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    response_json = response.json()
    assert response.status_code == HTTP_200_OK
    assert len(response_json) == 3
    assert response_json[0]["id"] == user_source1.id
    assert response_json[0]["type"] == "local_baserow"
    assert response_json[0]["integration_id"] == integration.id
    assert response_json[0]["table_id"] == table.id
    assert response_json[0]["email_field_id"] == email_field.id
    assert response_json[0]["name_field_id"] == name_field.id
    assert response_json[0]["role_field_id"] == role_field.id

    assert response_json[1]["id"] == user_source2.id
    assert response_json[1]["type"] == "local_baserow"
    assert response_json[1]["integration_id"] == integration.id
    assert response_json[1]["table_id"] == table.id
    assert response_json[1]["email_field_id"] == email_field.id
    assert response_json[1]["name_field_id"] is None
    assert response_json[1]["role_field_id"] is None

    assert response_json[2]["id"] == user_source3.id
    assert response_json[2]["type"] == "local_baserow"
    assert response_json[2]["integration_id"] == integration.id
    assert response_json[2]["table_id"] == table.id
    assert response_json[2]["email_field_id"] is None
    assert response_json[2]["name_field_id"] is None
    assert response_json[2]["role_field_id"] is None


@pytest.fixture(autouse=True)
def user_source_fixture(data_fixture):
    """A fixture to help test LocalBaserowUserSourceType."""

    user, _ = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    page = data_fixture.create_builder_page(user=user)
    application = data_fixture.create_builder_application(workspace=workspace)
    local_baserow_user_source_type = user_source_type_registry.get("local_baserow")

    user_source = data_fixture.create_user_source(
        local_baserow_user_source_type.model_class,
        application=application,
    )
    return user_source


@pytest.mark.django_db
def test_create_local_baserow_user_source(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    application = data_fixture.create_builder_application(workspace=workspace)
    database = data_fixture.create_database_application(workspace=workspace)

    integration = data_fixture.create_local_baserow_integration(application=application)

    table, fields, rows = data_fixture.build_table(
        user=user,
        database=database,
        columns=[
            ("Email", "text"),
            ("Name", "text"),
        ],
        rows=[
            ["test@baserow.io", "Test"],
        ],
    )

    email_field, name_field = fields

    url = reverse("api:user_sources:list", kwargs={"application_id": application.id})
    response = api_client.post(
        url,
        {
            "type": "local_baserow",
            "name": "test",
            "integration_id": integration.id,
            "table_id": table.id,
            "email_field_id": email_field.id,
            "name_field_id": name_field.id,
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    response_json = response.json()
    assert response.status_code == HTTP_200_OK
    assert response_json["type"] == "local_baserow"
    assert response_json["integration_id"] == integration.id
    assert response_json["table_id"] == table.id
    assert response_json["email_field_id"] == email_field.id
    assert response_json["name_field_id"] == name_field.id


@pytest.mark.django_db
def test_create_local_baserow_user_source_wrong_field_type(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    application = data_fixture.create_builder_application(workspace=workspace)
    database = data_fixture.create_database_application(workspace=workspace)

    integration = data_fixture.create_local_baserow_integration(application=application)

    table, fields, rows = data_fixture.build_table(
        user=user,
        database=database,
        columns=[
            ("Email", "rating"),
            ("Name", "url"),
            ("Email", "text"),
        ],
        rows=[
            [2, "Test", "test"],
        ],
    )

    email_field, name_field, another_email_field = fields

    url = reverse("api:user_sources:list", kwargs={"application_id": application.id})
    response = api_client.post(
        url,
        {
            "type": "local_baserow",
            "name": "test",
            "integration_id": integration.id,
            "table_id": table.id,
            "email_field_id": email_field.id,
            "name_field_id": name_field.id,
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    response_json = response.json()
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response_json["error"] == "ERROR_REQUEST_BODY_VALIDATION"
    assert response_json["detail"]["email_field_id"][0]["code"] == "invalid_field"

    response = api_client.post(
        url,
        {
            "type": "local_baserow",
            "name": "test",
            "integration_id": integration.id,
            "table_id": table.id,
            "email_field_id": another_email_field.id,
            "name_field_id": name_field.id,
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    response_json = response.json()
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response_json["error"] == "ERROR_REQUEST_BODY_VALIDATION"
    assert response_json["detail"]["name_field_id"][0]["code"] == "invalid_field"


@pytest.mark.django_db
def test_create_local_baserow_user_source_w_a_password_auth_source(
    api_client, data_fixture
):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    application = data_fixture.create_builder_application(workspace=workspace)
    database = data_fixture.create_database_application(workspace=workspace)

    integration = data_fixture.create_local_baserow_integration(application=application)

    table, fields, rows = data_fixture.build_table(
        user=user,
        database=database,
        columns=[
            ("Email", "text"),
            ("Name", "text"),
            ("Password", "password"),
            ("Role", "text"),
        ],
        rows=[
            ["test@baserow.io", "Test", "password", ""],
        ],
    )

    email_field, name_field, password_field, role_field = fields

    url = reverse("api:user_sources:list", kwargs={"application_id": application.id})
    response = api_client.post(
        url,
        {
            "type": "local_baserow",
            "name": "test",
            "integration_id": integration.id,
            "table_id": table.id,
            "email_field_id": email_field.id,
            "name_field_id": name_field.id,
            "role_field_id": role_field.id,
            "auth_providers": [
                {
                    "password_field_id": password_field.id,
                    "type": "local_baserow_password",
                },
            ],
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_200_OK


@pytest.mark.django_db
def test_create_local_baserow_user_source_w_two_password_auth_source(
    api_client, data_fixture
):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    application = data_fixture.create_builder_application(workspace=workspace)
    database = data_fixture.create_database_application(workspace=workspace)

    integration = data_fixture.create_local_baserow_integration(application=application)

    table, fields, rows = data_fixture.build_table(
        user=user,
        database=database,
        columns=[
            ("Email", "text"),
            ("Name", "text"),
        ],
        rows=[
            ["test@baserow.io", "Test"],
        ],
    )

    email_field, name_field = fields

    url = reverse("api:user_sources:list", kwargs={"application_id": application.id})
    response = api_client.post(
        url,
        {
            "type": "local_baserow",
            "name": "test",
            "integration_id": integration.id,
            "table_id": table.id,
            "email_field_id": email_field.id,
            "name_field_id": name_field.id,
            "auth_providers": [
                {
                    "type": "local_baserow_password",
                },
                {
                    "type": "local_baserow_password",
                },
            ],
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    response_json = response.json()
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_AUTH_PROVIDER_CANT_BE_CREATED"


@pytest.mark.django_db
def test_create_local_baserow_user_source_w_wrong_field_ids(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    application = data_fixture.create_builder_application(workspace=workspace)
    database = data_fixture.create_database_application(workspace=workspace)

    integration = data_fixture.create_local_baserow_integration(application=application)

    table, fields, rows = data_fixture.build_table(
        user=user,
        database=database,
        columns=[
            ("Email", "text"),
            ("Name", "text"),
        ],
        rows=[
            ["test@baserow.io", "Test"],
        ],
    )

    email_field, name_field = fields

    url = reverse("api:user_sources:list", kwargs={"application_id": application.id})
    response = api_client.post(
        url,
        {
            "type": "local_baserow",
            "name": "test",
            "integration_id": integration.id,
            "table_id": table.id,
            "email_field_id": 0,
            "name_field_id": name_field.id,
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    response_json = response.json()
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response_json["error"] == "ERROR_REQUEST_BODY_VALIDATION"
    assert response_json["detail"]["email_field_id"][0]["code"] == "invalid_field"

    response = api_client.post(
        url,
        {
            "type": "local_baserow",
            "name": "test",
            "integration_id": integration.id,
            "table_id": table.id,
            "email_field_id": email_field.id,
            "name_field_id": 0,
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    response_json = response.json()
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response_json["error"] == "ERROR_REQUEST_BODY_VALIDATION"
    assert response_json["detail"]["name_field_id"][0]["code"] == "invalid_field"

    FieldHandler().delete_field(user, email_field)

    response = api_client.post(
        url,
        {
            "type": "local_baserow",
            "name": "test",
            "integration_id": integration.id,
            "table_id": table.id,
            "email_field_id": email_field.id,
            "name_field_id": name_field.id,
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    response_json = response.json()
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_REQUEST_BODY_VALIDATION"
    assert response.json()["detail"]["email_field_id"][0]["code"] == "invalid_field"


@pytest.mark.django_db
def test_create_user_source_table_from_other_workspace(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    application = data_fixture.create_builder_application(workspace=workspace)
    database = data_fixture.create_database_application(workspace=workspace)

    integration = data_fixture.create_local_baserow_integration(
        application=application, user=user
    )

    table_from_other_workspace, fields, rows = data_fixture.build_table(
        user=user,
        columns=[
            ("Email", "text"),
            ("Name", "text"),
        ],
        rows=[
            ["test@baserow.io", "Test"],
        ],
    )

    url = reverse("api:user_sources:list", kwargs={"application_id": application.id})
    response = api_client.post(
        url,
        {
            "type": "local_baserow",
            "name": "test",
            "integration_id": integration.id,
            "table_id": table_from_other_workspace.id,
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_REQUEST_BODY_VALIDATION"
    assert response.json()["detail"]["table_id"][0]["code"] == "invalid_table"


@pytest.mark.django_db
def test_create_local_baserow_user_source_w_a_missing_table(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    application = data_fixture.create_builder_application(workspace=workspace)
    database = data_fixture.create_database_application(workspace=workspace)

    integration = data_fixture.create_local_baserow_integration(application=application)

    table, fields, rows = data_fixture.build_table(
        user=user,
        database=database,
        columns=[
            ("Email", "text"),
            ("Name", "text"),
        ],
        rows=[
            ["test@baserow.io", "Test"],
        ],
    )

    email_field, name_field = fields

    url = reverse("api:user_sources:list", kwargs={"application_id": application.id})
    response = api_client.post(
        url,
        {
            "type": "local_baserow",
            "name": "test",
            "integration_id": integration.id,
            "table_id": 0,
            "email_field_id": email_field.id,
            "name_field_id": name_field.id,
            "auth_providers": [
                {
                    "password_field_id": name_field.id,
                    "type": "local_baserow_password",
                },
            ],
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_REQUEST_BODY_VALIDATION"
    assert response.json()["detail"]["table_id"][0]["code"] == "invalid_table"


@pytest.mark.django_db
def test_create_user_source_field_from_other_table(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    application = data_fixture.create_builder_application(workspace=workspace)
    database = data_fixture.create_database_application(workspace=workspace)

    integration = data_fixture.create_local_baserow_integration(
        application=application, user=user
    )

    table_from_same_workspace1, fields, rows = data_fixture.build_table(
        user=user,
        database=database,
        columns=[
            ("Email", "text"),
            ("Name", "text"),
        ],
        rows=[
            ["test@baserow.io", "Test"],
        ],
    )

    table_from_same_workspace2, fields2, rows = data_fixture.build_table(
        user=user,
        database=database,
        columns=[
            ("Email", "text"),
            ("Name", "text"),
        ],
        rows=[
            ["test@baserow.io", "Test"],
        ],
    )

    email_field_other_table, name_field_other_table = fields2

    # Email field for another table
    url = reverse("api:user_sources:list", kwargs={"application_id": application.id})
    response = api_client.post(
        url,
        {
            "type": "local_baserow",
            "name": "test",
            "integration_id": integration.id,
            "table_id": table_from_same_workspace1.id,
            "email_field_id": email_field_other_table.id,
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_REQUEST_BODY_VALIDATION"
    assert response.json()["detail"]["email_field_id"][0]["code"] == "invalid_field"

    # name field from another table
    response = api_client.post(
        url,
        {
            "type": "local_baserow",
            "name": "test",
            "integration_id": integration.id,
            "table_id": table_from_same_workspace1.id,
            "name_field_id": name_field_other_table.id,
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_REQUEST_BODY_VALIDATION"
    assert response.json()["detail"]["name_field_id"][0]["code"] == "invalid_field"

    # email field without table
    response = api_client.post(
        url,
        {
            "type": "local_baserow",
            "name": "test",
            "integration_id": integration.id,
            "email_field_id": email_field_other_table.id,
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_REQUEST_BODY_VALIDATION"
    assert response.json()["detail"]["email_field_id"][0]["code"] == "missing_table"

    # name field without table
    response = api_client.post(
        url,
        {
            "type": "local_baserow",
            "name": "test",
            "integration_id": integration.id,
            "name_field_id": name_field_other_table.id,
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_REQUEST_BODY_VALIDATION"
    assert response.json()["detail"]["name_field_id"][0]["code"] == "missing_table"


@pytest.mark.django_db
def test_export_user_source(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    application = data_fixture.create_builder_application(workspace=workspace)
    database = data_fixture.create_database_application(workspace=workspace)

    integration = data_fixture.create_local_baserow_integration(
        application=application, user=user
    )

    table_from_same_workspace1, fields, rows = data_fixture.build_table(
        user=user,
        database=database,
        columns=[
            ("Email", "text"),
            ("Name", "text"),
        ],
        rows=[
            ["test@baserow.io", "Test"],
        ],
    )

    email_field, name_field = fields

    user_source = data_fixture.create_user_source_with_first_type(
        integration=integration,
        name="Test name",
        table=table_from_same_workspace1,
        email_field=email_field,
        name_field=name_field,
        uid="uid",
    )

    auth_provider = data_fixture.create_app_auth_provider_with_first_type(
        user_source=user_source
    )

    exported = UserSourceHandler().export_user_source(user_source)

    assert exported == {
        "email_field_id": email_field.id,
        "id": exported["id"],
        "integration_id": integration.id,
        "name": "Test name",
        "name_field_id": name_field.id,
        "order": "1.00000000000000000000",
        "role_field_id": None,
        "table_id": table_from_same_workspace1.id,
        "type": "local_baserow",
        "uid": "uid",
        "auth_providers": [
            {
                "id": auth_provider.id,
                "type": auth_provider.get_type().type,
                "domain": None,
                "enabled": True,
                "password_field_id": None,
            }
        ],
    }


@pytest.mark.django_db
def test_import_local_baserow_user_source(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    application = data_fixture.create_builder_application(workspace=workspace)
    database = data_fixture.create_database_application(workspace=workspace)

    integration = data_fixture.create_local_baserow_integration(
        application=application, user=user
    )

    table_from_same_workspace1, fields, rows = data_fixture.build_table(
        user=user,
        database=database,
        columns=[
            ("Email", "text"),
            ("Name", "text"),
        ],
        rows=[
            ["test@baserow.io", "Test"],
        ],
    )

    email_field, name_field = fields

    TO_IMPORT = {
        "email_field_id": 42,
        "id": 28,
        "integration_id": 42,
        "name": "Test name",
        "name_field_id": 43,
        "order": "1.00000000000000000000",
        "table_id": 42,
        "type": "local_baserow",
        "auth_providers": [
            {
                "id": 42,
                "type": "local_baserow_password",
                "domain": None,
                "enabled": True,
                "password_field_id": None,
            }
        ],
    }

    id_mapping = defaultdict(MirrorDict)
    id_mapping["integrations"] = {42: integration.id}
    id_mapping["database_tables"] = {42: table_from_same_workspace1.id}
    id_mapping["database_fields"] = {42: email_field.id, 43: name_field.id}

    imported_instance = UserSourceHandler().import_user_source(
        application, TO_IMPORT, id_mapping
    )

    assert imported_instance.table_id == table_from_same_workspace1.id
    assert imported_instance.email_field_id == email_field.id
    assert imported_instance.name_field_id == name_field.id


@pytest.mark.django_db
def test_create_local_baserow_user_source_w_auth_providers(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=user)
    application = data_fixture.create_builder_application(workspace=workspace)
    database = data_fixture.create_database_application(workspace=workspace)
    integration = data_fixture.create_local_baserow_integration(application=application)
    table, fields, rows = data_fixture.build_table(
        columns=[("Name", "text"), ("Password", "password")],
        rows=["Peter", "hunter2"],
        user=user,
        database=database,
    )
    password_field = table.field_set.get(name="Password")

    url = reverse("api:user_sources:list", kwargs={"application_id": application.id})
    response = api_client.post(
        url,
        {
            "type": "local_baserow",
            "name": "test",
            "table_id": table.id,
            "integration_id": integration.id,
            "auth_providers": [
                {
                    "type": "local_baserow_password",
                    "enabled": True,
                    "domain": "test1",
                    "password_field_id": password_field.id,
                }
            ],
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    response_json = response.json()
    assert response.status_code == HTTP_200_OK

    assert AppAuthProvider.objects.count() == 1
    first = AppAuthProvider.objects.first()

    assert response_json["auth_providers"] == [
        {
            "domain": "test1",
            "id": first.id,
            "password_field_id": password_field.id,
            "type": "local_baserow_password",
        },
    ]


@pytest.mark.django_db
def test_local_baserow_user_source_token_generation(
    data_fixture,
):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    application = data_fixture.create_builder_application(
        workspace=workspace, user=user
    )
    database = data_fixture.create_database_application(workspace=workspace)
    data_fixture.create_database_table(database=database)
    integration = data_fixture.create_local_baserow_integration(
        application=application, user=user
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
            ["test@baserow.io", "Test", "super not secret", ""],
        ],
    )

    email_field, name_field, password_field, role_field = fields

    local_baserow_user_source_type = user_source_type_registry.get("local_baserow")

    user_source = data_fixture.create_user_source(
        local_baserow_user_source_type.model_class,
        application=application,
        integration=integration,
        table=table,
        email_field=email_field,
        name_field=name_field,
        role_field=role_field,
    )

    user_source_type = user_source.get_type()

    user = rows[0]

    user = user_source_type.get_user(user_source, email="test@baserow.io")

    assert user.email == "test@baserow.io"
    assert user.id == rows[0].id


@pytest.mark.django_db
def test_public_dispatch_data_source_with_ab_user_using_user_source(
    api_client, data_fixture
):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    builder = data_fixture.create_builder_application(workspace=workspace, user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    data_fixture.create_database_table(database=database)
    integration = data_fixture.create_local_baserow_integration(
        application=builder, user=user
    )

    # Create the table to dispatch
    table, fields, rows = data_fixture.build_table(
        user=user,
        columns=[
            ("Name", "text"),
            ("My Color", "text"),
        ],
        rows=[
            ["BMW", "Blue"],
            ["Audi", "Orange"],
        ],
    )

    # Define the data source to dispatch
    page = data_fixture.create_builder_page(user=user, builder=builder)
    data_source = data_fixture.create_builder_local_baserow_get_row_data_source(
        user=user,
        page=page,
        integration=integration,
        table=table,
        row_id="2",
    )

    # Create the user table for the user_source
    user_table, user_fields, user_rows = data_fixture.build_table(
        user=user,
        columns=[
            ("Email", "text"),
            ("Name", "text"),
            ("Password", "text"),
            ("Role", "text"),
        ],
        rows=[
            ["test@baserow.io", "Test", "super not secret", ""],
        ],
    )
    email_field, name_field, password_field, role_field = user_fields

    # Create the user source and the auth provider
    user_source = data_fixture.create_user_source(
        user_source_type_registry.get("local_baserow").model_class,
        application=builder,
        integration=integration,
        table=user_table,
        email_field=email_field,
        name_field=name_field,
        role_field=role_field,
    )

    # Create a domain and publish the application
    domain1 = data_fixture.create_builder_custom_domain(builder=builder)
    progress = Progress(100)
    DomainHandler().publish(domain1, progress)
    domain1.refresh_from_db()

    user_source_type = user_source.get_type()

    user = user_rows[0]

    user_source_user = user_source_type.get_user(user_source, email="test@baserow.io")

    refresh_token = user_source_user.get_refresh_token()
    access_token = refresh_token.access_token

    published_page = domain1.published_to.page_set.first()
    published_data_source = published_page.datasource_set.first()

    url = reverse(
        "api:builder:data_source:dispatch",
        kwargs={"data_source_id": published_data_source.id},
    )

    response = api_client.post(
        url,
        {},
        format="json",
        HTTP_AUTHORIZATION_US=f"JWT {access_token}",
    )

    assert response.status_code == HTTP_200_OK
    assert response.json() == {
        "id": 2,
        "order": "1.00000000000000000000",
        fields[0].db_column: "Audi",
        fields[1].db_column: "Orange",
    }


@pytest.mark.django_db
def test_local_baserow_user_source_get_user(
    data_fixture,
):
    data = populate_local_baserow_test_data(data_fixture)

    user_source = data["user_source"]
    user_source_type = user_source.get_type()

    UserModel = data["user_table"].get_model()

    first_user = UserModel.objects.first()

    user = user_source_type.get_user(user_source, user_id=first_user.id)

    assert user.id == first_user.id
    assert user.username == getattr(first_user, user_source.name_field.db_column)
    assert user.email == getattr(first_user, user_source.email_field.db_column)

    user = user_source_type.get_user(
        user_source, email=getattr(first_user, user_source.email_field.db_column)
    )

    assert user.id == first_user.id
    assert user.username == getattr(first_user, user_source.name_field.db_column)
    assert user.email == getattr(first_user, user_source.email_field.db_column)


@pytest.mark.django_db
def test_local_baserow_user_source_get_user_not_configured(
    data_fixture,
):
    data = populate_local_baserow_test_data(data_fixture)

    user_source = data["user_source"]
    user_source_type = user_source.get_type()

    UserModel = data["user_table"].get_model()

    first_user = UserModel.objects.first()

    user_source.name_field = None
    user_source.save()

    with pytest.raises(UserNotFound):
        user_source_type.get_user(user_source, user_id=first_user.id)


@pytest.mark.django_db
def test_local_baserow_user_source_get_user_with_duplicate(
    data_fixture,
):
    data = populate_local_baserow_test_data(data_fixture)

    user_source = data["user_source"]
    user_source_type = user_source.get_type()

    UserModel = data["user_table"].get_model()

    first_user = UserModel.objects.first()

    # Let's create another user with same email and check that it's still working
    UserModel.objects.create(
        **{
            user_source.name_field.db_column: "a user name",
            user_source.email_field.db_column: getattr(
                first_user, user_source.email_field.db_column
            ),  # Ouch a duplicate!!!
        }
    )

    user = user_source_type.get_user(
        user_source, email=getattr(first_user, user_source.email_field.db_column)
    )
    assert user.id == first_user.id


@pytest.mark.django_db
def test_local_baserow_user_source_get_user_fails(
    data_fixture,
):
    data = populate_local_baserow_test_data(data_fixture)

    user_source = data["user_source"]
    user_source_type = user_source.get_type()

    with pytest.raises(UserNotFound):
        user_source_type.get_user(user_source, user_id=0)

    with pytest.raises(UserNotFound):
        user_source_type.get_user(user_source, email="missing@ema.il")


@pytest.mark.django_db
def test_local_baserow_user_source_authentication(
    data_fixture,
):
    data = populate_local_baserow_test_data(data_fixture)

    user_source = data["user_source"]
    user_source_type = user_source.get_type()

    user = user_source_type.authenticate(
        user_source, email="test@baserow.io", password="super not secret"
    )

    assert user.email == "test@baserow.io"
    assert user.username == "Test"

    user = user_source_type.authenticate(
        user_source, email="test2@baserow.io", password="super not secret"
    )

    assert user.email == "test2@baserow.io"
    assert user.username == "Test2"


@pytest.mark.django_db
def test_local_baserow_user_source_authentication_improperly_configured(
    data_fixture,
):
    data = populate_local_baserow_test_data(data_fixture)

    user_source = data["user_source"]
    user_source_type = user_source.get_type()

    email_field = user_source.email_field

    user_source.email_field = None
    user_source.save()

    with pytest.raises(UserSourceImproperlyConfigured):
        user_source_type.authenticate(
            user_source, email="test@baserow.io", password="super not secret"
        )

    user_source.email_field = email_field
    user_source.name_field = None
    user_source.save()

    with pytest.raises(UserSourceImproperlyConfigured):
        user_source_type.authenticate(
            user_source, email="test@baserow.io", password="super not secret"
        )


@pytest.mark.django_db
def test_local_baserow_user_source_authentication_missing_auth_provider(
    data_fixture,
):
    data = populate_local_baserow_test_data(data_fixture)

    user_source = data["user_source"]
    user_source_type = user_source.get_type()

    data["auth_provider"].delete()

    with pytest.raises(UserSourceImproperlyConfigured):
        user_source_type.authenticate(
            user_source, email="test@baserow.io", password="super not secret"
        )


@pytest.mark.django_db
def test_local_baserow_user_source_authentication_bad_creds(
    data_fixture,
):
    data = populate_local_baserow_test_data(data_fixture)

    user_source = data["user_source"]
    user_source_type = user_source.get_type()

    with pytest.raises(AuthenticationFailed):
        user_source_type.authenticate(
            user_source, email="test@baserow.io", password="bad password"
        )

    with pytest.raises(UserNotFound):
        user_source_type.authenticate(
            user_source, email="testt@baserow.io", password="super not secret"
        )

    with pytest.raises(AuthenticationFailed):
        user_source_type.authenticate(
            user_source, email="test4@baserow.io", password="super not secret"
        )


@pytest.mark.django_db
def test_local_baserow_user_source_authentication_list_users(
    data_fixture, disable_full_text_search
):
    data = populate_local_baserow_test_data(data_fixture)

    user_source = data["user_source"]
    user_source_type = user_source.get_type()

    first_user, second_user, third_user, fourth_user = (
        data["user_table"].get_model().objects.all()
    )

    result = user_source_type.list_users(user_source)

    assert len(result) == 4
    assert result[0].id == first_user.id
    assert result[1].id == second_user.id
    assert result[2].id == third_user.id
    assert result[3].id == fourth_user.id

    result = user_source_type.list_users(user_source, count=2)

    assert len(result) == 2

    result = user_source_type.list_users(user_source, search="test@")

    assert len(result) == 1


@pytest.mark.django_db
def test_local_baserow_user_source_authentication_list_users_not_configured(
    data_fixture,
):
    data = populate_local_baserow_test_data(data_fixture)

    user_source = data["user_source"]
    user_source_type = user_source.get_type()

    user_source.email_field = None
    user_source.save()

    result = user_source_type.list_users(user_source)

    assert len(result) == 0


def test_local_baserow_user_source_authentication_is_configured(
    data_fixture,
):
    user_source_type = LocalBaserowUserSourceType()
    # All configured fields.
    # fmt: off
    assert user_source_type.is_configured(LocalBaserowUserSource(
        email_field_id=1,
        name_field_id=2,
        table_id=3,
        role_field_id=4
    )) is True
    # Missing email field.
    # fmt: off
    assert user_source_type.is_configured(LocalBaserowUserSource(
        email_field_id=None,
        name_field_id=2,
        table_id=3,
        role_field_id=4,
    )) is False
    # Missing name field.
    # fmt: off
    assert user_source_type.is_configured(LocalBaserowUserSource(
        email_field_id=1,
        name_field_id=None,
        table_id=3,
        role_field_id=4,
    )) is False
    # Missing table field.
    # fmt: off
    assert user_source_type.is_configured(LocalBaserowUserSource(
        email_field_id=1,
        name_field_id=2,
        table_id=None,
        role_field_id=4,
    )) is False


@pytest.fixture(autouse=True)
def role_field_id_test_fixture(data_fixture):
    """Fixture to help test the role_field_id."""

    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    application = data_fixture.create_builder_application(workspace=workspace)
    integration = data_fixture.create_local_baserow_integration(application=application)
    local_baserow_user_source_type = user_source_type_registry.get("local_baserow")

    user_source = data_fixture.create_user_source(
        local_baserow_user_source_type.model_class,
        application=application,
        integration=integration,
    )

    return user, user_source, application, workspace, integration


@pytest.mark.django_db
def test_prepare_values_role_field_id_raises_if_no_table_to_check(data_fixture):
    """
    Test the prepare_values() method when the "role_field_id" is in values.

    Ensure an exception is raised if the table is missing.
    """

    data = populate_local_baserow_test_data(data_fixture)

    user_source = data["user_source"]
    user_source_type = LocalBaserowUserSourceType()

    with pytest.raises(RequestBodyValidationException) as e:
        user_source_type.prepare_values(
            {"role_field_id": 1},
            user_source,
        )

    assert "Please select a table before selecting this field" in str(e.value)


@pytest.mark.django_db
def test_prepare_values_role_field_id_raises_if_field_doesnt_exist(
    data_fixture,
    role_field_id_test_fixture,
):
    """
    Test the prepare_values() method when the "role_field_id" is in values.

    Ensure an exception is raised if the role_field is missing.
    """

    user, user_source, _, _, _ = role_field_id_test_fixture

    users_table = data_fixture.create_database_table(name="test_users")
    role_field = data_fixture.create_text_field(table=users_table, order=0, name="role")
    user_source.table = users_table
    user_source.role_field = role_field
    user_source.save()

    with pytest.raises(RequestBodyValidationException) as e:
        LocalBaserowUserSourceType().prepare_values(
            # Add 100 to the latest role_field, which should simulate a
            # non-existent ID.
            {"role_field_id": role_field.id + 100},
            user,
            user_source,
        )

    assert "The provided Id doesn't exist." in str(e.value)


@pytest.mark.django_db
def test_prepare_values_role_field_id_raises_if_field_id_mismatch(
    data_fixture,
    role_field_id_test_fixture,
):
    """
    Test the prepare_values() method when the "role_field_id" is in values.

    Ensure an exception is raised if the role field's table_id doesns't match
    the table's ID.
    """

    user, user_source, application, _, _ = role_field_id_test_fixture

    users_table = data_fixture.create_database_table(name="test_users")
    role_field = data_fixture.create_text_field(table=users_table, order=0, name="role")
    user_source.table = users_table
    user_source.role_field = role_field
    user_source.save()

    # Create a different table
    foo_table = data_fixture.create_database_table(name="foo")
    local_baserow_user_source_type = user_source_type_registry.get("local_baserow")
    user_source_2 = data_fixture.create_user_source(
        local_baserow_user_source_type.model_class,
        application=application,
    )
    user_source_2.table = foo_table
    user_source_2.save()

    with pytest.raises(RequestBodyValidationException) as e:
        LocalBaserowUserSourceType().prepare_values(
            {"role_field_id": role_field.id},
            user,
            user_source_2,
        )

    assert (
        f"The field with ID {role_field.id} is not related to the given table."
        in str(e.value)
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field_creator,",
    [
        "create_autonumber_field",
        "create_boolean_field",
        "create_created_by_field",
        "create_created_on_field",
        "create_date_field",
        "create_duration_field",
        "create_email_field",
        "create_file_field",
        "create_last_modified_by_field",
        "create_last_modified_field",
        "create_link_row_field",
        "create_long_text_field",
        "create_lookup_field",
        "create_multiple_collaborators_field",
        "create_multiple_select_field",
        "create_number_field",
        "create_password_field",
        "create_phone_number_field",
        "create_rating_field",
        "create_url_field",
        "create_uuid_field",
    ],
)
def test_prepare_values_role_field_id_raises_if_field_type_wrong(
    data_fixture,
    role_field_id_test_fixture,
    field_creator,
):
    """
    Test the prepare_values() method when the "role_field_id" is in values.

    Ensure an exception is raised if the role field's type is not allowed.
    """

    user, user_source, _, _, _ = role_field_id_test_fixture

    users_table = data_fixture.create_database_table(name="test_users")
    role_field = getattr(data_fixture, field_creator)(
        table=users_table, order=0, name="role"
    )
    user_source.table = users_table
    user_source.role_field = role_field
    user_source.save()

    with pytest.raises(RequestBodyValidationException) as e:
        LocalBaserowUserSourceType().prepare_values(
            {"role_field_id": role_field.id},
            user,
            user_source,
        )

    assert f"This field type can't be used as a role." in str(e.value)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field_creator,",
    [
        "create_formula_field",
        "create_single_select_field",
        "create_text_field",
    ],
)
def test_prepare_values_role_field_id_returns_values(
    data_fixture, role_field_id_test_fixture, field_creator
):
    """
    Test the prepare_values() method when the "role_field_id" is in values.

    Ensure that the expected values dict is returned for the valid field types.
    """

    user, user_source, _, _, _ = role_field_id_test_fixture

    users_table = data_fixture.create_database_table(name="test_users")
    role_field = getattr(data_fixture, field_creator)(
        table=users_table, order=0, name="role"
    )
    user_source.table = users_table
    user_source.role_field = role_field
    user_source.save()

    values = LocalBaserowUserSourceType().prepare_values(
        {"role_field_id": role_field.id},
        user,
        user_source,
    )

    field = FieldHandler().get_field(role_field.id)
    assert values["role_field"] == field
    assert "role_field_id" not in values


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field_creator,",
    [
        "create_formula_field",
        "create_single_select_field",
        "create_text_field",
    ],
)
def test_prepare_values_role_field_id_returns_empty_values_if_role_field_id_is_none(
    data_fixture, field_creator
):
    """
    Test the prepare_values() method when the "role_field_id" is in values.

    Ensure that the expected values dict is empty if the role_field_id is None.
    """

    user = data_fixture.create_user()

    values = LocalBaserowUserSourceType().prepare_values(
        {"role_field_id": None},
        user,
    )

    assert values["role_field"] is None
    assert "role_field_id" not in values


@pytest.mark.django_db
def test_prepare_values_sets_role_field_to_none(
    data_fixture,
    role_field_id_test_fixture,
):
    """
    Test the prepare_values() method when the "role_field_id" is
    missing in values.

    Ensure that role_field with a value of None is added to values.
    """

    user, user_source, _, workspace, integration = role_field_id_test_fixture

    database = data_fixture.create_database_application(workspace=workspace)
    users_table = data_fixture.create_database_table(
        name="test_users", database=database
    )
    other_table = data_fixture.create_database_table(
        name="test_other", database=database
    )

    role_field = data_fixture.create_text_field(table=users_table, order=0, name="role")
    user_source.table = users_table
    user_source.role_field = role_field
    user_source.save()

    values = LocalBaserowUserSourceType().prepare_values(
        {
            "table_id": other_table.id,
            "integration": integration,
        },
        user,
        user_source,
    )

    assert values["role_field"] is None


@pytest.mark.django_db
def test_get_user_role_returns_role_from_text_field(data_fixture):
    """
    Ensure the get_user_role() method returns a specific user role when
    the Role Field is of type TextFieldType.
    """

    role_name = "foo_role"
    data = populate_local_baserow_test_data(data_fixture, role_name=role_name)
    user_source = data["user_source"]

    UserModel = data["user_table"].get_model()
    first_user = UserModel.objects.first()

    user_role = LocalBaserowUserSourceType().get_user_role(
        first_user,
        user_source,
    )

    assert user_role == role_name


@pytest.mark.django_db
def test_get_user_role_returns_role_from_single_select_field(data_fixture):
    """
    Ensure the get_user_role() method returns a specific user role when
    the Role Field is of type SingleSelectFieldType.
    """

    role = "foo_role"
    data = populate_local_baserow_test_data(data_fixture)
    user_source = data["user_source"]

    role_field = data_fixture.create_single_select_field(
        table=user_source.table, name="role", order=0
    )
    option = data_fixture.create_select_option(field=role_field, value=role)

    user_source.role_field = role_field
    user_source.save()

    UserModel = data["user_table"].get_model()
    first_user = UserModel.objects.first()
    setattr(first_user, user_source.role_field.db_column, option)

    user_role = LocalBaserowUserSourceType().get_user_role(
        first_user,
        user_source,
    )

    assert user_role == role


@pytest.mark.django_db
def test_get_user_role_returns_empty_string_from_single_select_field(data_fixture):
    """
    Ensure the get_user_role() method returns an empty string, if the Role
    Field is of type SingleSelectFieldType, but there is no selection for
    the row.

    This might happen if a row is created in the Users table, but the Role
    Field is left blank.
    """

    data = populate_local_baserow_test_data(data_fixture)
    user_source = data["user_source"]

    role_field = data_fixture.create_single_select_field(
        table=user_source.table, name="role", order=0
    )

    # The role_field does not have any actual options, so any rows created
    # would have a null/None value for the Role.
    user_source.role_field = role_field
    user_source.save()

    UserModel = data["user_table"].get_model()
    first_user = UserModel.objects.first()
    user_role = LocalBaserowUserSourceType().get_user_role(
        first_user,
        user_source,
    )

    assert user_role == ""


@pytest.mark.django_db
def test_get_user_role_returns_default_role(data_fixture):
    """
    Ensure the get_user_role() method returns the default user role if
    the UserRole.role_field is None.
    """

    data = populate_local_baserow_test_data(data_fixture)
    user_source = data["user_source"]
    user_source.role_field = None
    user_source.save()

    UserModel = data["user_table"].get_model()
    first_user = UserModel.objects.first()

    user_role = LocalBaserowUserSourceType().get_user_role(
        first_user,
        user_source,
    )

    assert user_role == f"{DEFAULT_USER_ROLE_PREFIX}{user_source.id}"


@pytest.mark.django_db
def test_get_roles_returns_default_role_if_role_field_is_null(data_fixture):
    """
    Ensure get_roles() returns only the Default User Role if the role_field
    is null.
    """

    data = populate_local_baserow_test_data(data_fixture)
    user_source = data["user_source"]
    user_source.role_field = None
    user_source.save()

    roles = LocalBaserowUserSourceType().get_roles(user_source)

    assert roles == [f"{DEFAULT_USER_ROLE_PREFIX}{user_source.id}"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "roles,expected_roles",
    [
        (
            [],
            [],
        ),
        (
            [
                "foo_role",
            ],
            [
                "foo_role",
            ],
        ),
        # We expect the returned roles to be ordered
        (
            ["foo_role", "bar_role"],
            ["bar_role", "foo_role"],
        ),
    ],
)
def test_get_roles_returns_single_select_roles(data_fixture, roles, expected_roles):
    """
    Ensure get_roles() returns the expected list of roles, if the Role Type
    field is a Single Select Field.
    """

    data = populate_local_baserow_test_data(data_fixture)
    user_source = data["user_source"]

    role_field = data_fixture.create_single_select_field(
        table=user_source.table, name="role", order=0
    )
    for role in roles:
        data_fixture.create_select_option(field=role_field, value=role)

    user_source.role_field = role_field
    user_source.save()

    with patch.object(TableHandler, "get_table") as mock_handler:
        roles = LocalBaserowUserSourceType().get_roles(user_source)

    mock_handler.assert_not_called()
    assert roles == expected_roles


@pytest.mark.django_db
def test_get_roles_returns_empty_list_if_table_is_trashed(data_fixture):
    """Ensure get_roles() returns an empty list if Table is trashed."""

    data = populate_local_baserow_test_data(data_fixture)
    user_source = data["user_source"]
    role_field = data_fixture.create_text_field(
        table=user_source.table, order=0, name="role"
    )
    user_source.role_field = role_field
    user_source.save()

    with patch.object(
        TableHandler, "get_table", MagicMock(side_effect=TableDoesNotExist)
    ) as mock_handler:
        roles = LocalBaserowUserSourceType().get_roles(user_source)

    mock_handler.assert_called_once_with(user_source.table.id)
    assert roles == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_roles,expected_roles",
    [
        (
            ["foo_role"],
            ["foo_role"],
        ),
        (
            ["foo_role", "bar_role"],
            ["foo_role", "bar_role"],
        ),
        # Ensure empty strings are converted to the default No Role value
        (
            ["foo_role", ""],
            ["foo_role", ""],
        ),
        (
            ["", "foo_role", ""],
            ["foo_role", ""],
        ),
        # Ensure roles with leading/trailing white spaces are trimmed
        (
            ["  "],
            [""],
        ),
        (
            ["foo_role "],
            ["foo_role"],
        ),
        (
            [" foo_role", "bar_role ", " "],
            ["foo_role", "bar_role", ""],
        ),
    ],
)
def test_get_roles_returns_expected_roles(
    data_fixture, user_source_fixture, user_roles, expected_roles
):
    """Ensure get_roles() returns expected roles."""

    user_source = user_source_fixture

    # Create a roles field and add some rows
    users_table = data_fixture.create_database_table(name="test_users")
    role_field = data_fixture.create_text_field(
        table=users_table, order=0, name="role", text_default=""
    )
    user_source.table = users_table
    user_source.role_field = role_field
    user_source.save()

    # Add some roles
    model = users_table.get_model()
    for role in user_roles:
        model.objects.create(**{f"field_{role_field.id}": role})

    roles = LocalBaserowUserSourceType().get_roles(user_source)

    assert sorted(roles) == sorted(expected_roles)
