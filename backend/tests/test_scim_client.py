import pytest
import respx
from httpx import Response
from app.gateway.identity.scim.client import SCIMClient


@pytest.fixture
def client():
    return SCIMClient(
        base_url="https://idp.example.com/scim/v2",
        bearer_token="tkn",
    )


@respx.mock
@pytest.mark.asyncio
async def test_list_users(client):
    respx.get("https://idp.example.com/scim/v2/Users").mock(
        return_value=Response(
            200,
            json={
                "totalResults": 2,
                "Resources": [
                    {"id": "u1", "userName": "alice", "emails": [{"value": "a@x"}]},
                    {"id": "u2", "userName": "bob", "emails": [{"value": "b@x"}]},
                ],
            },
        )
    )
    users = await client.list_users()
    assert len(users) == 2
    assert users[0].userName == "alice"


@respx.mock
@pytest.mark.asyncio
async def test_list_groups(client):
    respx.get("https://idp.example.com/scim/v2/Groups").mock(
        return_value=Response(
            200,
            json={
                "totalResults": 1,
                "Resources": [{"id": "g1", "displayName": "eng", "members": [{"value": "u1"}]}],
            },
        )
    )
    groups = await client.list_groups()
    assert len(groups) == 1
    assert groups[0].display_name == "eng"
    assert groups[0].members == ["u1"]


@respx.mock
@pytest.mark.asyncio
async def test_pagination(client):
    page1 = {
        "totalResults": 3,
        "itemsPerPage": 2,
        "startIndex": 1,
        "Resources": [{"id": "u1", "userName": "a"}, {"id": "u2", "userName": "b"}],
    }
    page2 = {
        "totalResults": 3,
        "itemsPerPage": 2,
        "startIndex": 3,
        "Resources": [{"id": "u3", "userName": "c"}],
    }
    respx.get("https://idp.example.com/scim/v2/Users").mock(
        side_effect=[
            Response(200, json=page1),
            Response(200, json=page2),
        ]
    )
    users = await client.list_users_paginated(count_per_page=2)
    assert len(users) == 3