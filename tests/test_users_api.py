import pytest
from httpx import AsyncClient

# (关键 1) 明确标记这个模块的所有测试都使用 asyncio
pytestmark = pytest.mark.asyncio


# (关键 2) 将测试函数改回 `async def`
async def test_user_lifecycle(client: AsyncClient):
    """
    测试一个完整的用户生命周期（使用异步的 AsyncClient）。
    """
    user_id = None
    user_email = "testuser@example.com"
    headers = {"X-User-ID": "test-runner", "Content-Type": "application/json"}

    # --- 1. 创建用户 ---
    create_payload = {
        "name": "Test User",
        "email": user_email,
        "password": "a_strong_password"
    }
    # (关键 3) 在所有客户端调用前加上 `await`
    response = await client.post(
        "/users/actions",
        headers=headers,
        json={"action": "create", "payload": create_payload}
    )
    assert response.status_code == 200, f"创建失败: {response.text}"
    response_data = response.json()["data"]
    assert response_data["email"] == user_email
    assert "id" in response_data
    user_id = response_data["id"]
    print(f"\n用户创建成功, ID: {user_id}")

    # --- 2. 创建重复用户 ---
    response_dup = await client.post(
        "/users/actions",
        headers=headers,
        json={"action": "create", "payload": create_payload}
    )
    assert response_dup.status_code == 409, "重复创建检查失败"
    assert response_dup.json()["error"]["code"] == "DUPLICATE_RESOURCE"
    print("重复创建测试通过")

    # --- 3. 根据ID读取用户 ---
    response_get = await client.post(
        "/users/actions",
        headers=headers,
        json={"action": "get_by_id", "payload": {"id": user_id}}
    )
    assert response_get.status_code == 200
    assert response_get.json()["data"]["name"] == "Test User"
    print("读取用户测试通过")

    # --- 4. 更新用户 ---
    update_payload = {"id": user_id, "update_data": {"name": "Updated Test User"}}
    response_update = await client.post(
        "/users/actions",
        headers=headers,
        json={"action": "update", "payload": update_payload}
    )
    assert response_update.status_code == 200
    assert response_update.json()["data"]["name"] == "Updated Test User"
    print("更新用户测试通过")

    # --- 5. 删除用户 ---
    response_delete = await client.post(
        "/users/actions",
        headers=headers,
        json={"action": "delete", "payload": {"id": user_id}}
    )
    assert response_delete.status_code == 200
    assert "Successfully deleted" in response_delete.json()["data"]["message"]
    print("删除用户测试通过")

    # --- 6. 再次读取已删除的用户 ---
    response_get_deleted = await client.post(
        "/users/actions",
        headers=headers,
        json={"action": "get_by_id", "payload": {"id": user_id}}
    )
    assert response_get_deleted.status_code == 404, "删除后应返回404"
    assert response_get_deleted.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    print("读取已删除用户测试通过")