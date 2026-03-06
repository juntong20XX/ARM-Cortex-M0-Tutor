"""
Unit tests for database models
"""
from app.database import enter
from app.core.settings import AppSetting
from app.database import (init_database, db_context,
                          add_user,
                          find_user_by_username, find_user_by_email_host,
                          find_project_by_owner_name, find_project_by_name,
                          add_user_group, find_user_group_by_name, find_user_group_by_uuid,
                          find_all_user_groups, update_user_group, delete_user_group,
                          add_user_to_user_group, remove_user_from_user_group,
                          get_user_managed_user_groups, get_user_group_users, find_users_by_user_group,
                          add_managed_user_to_user_group, remove_managed_user_from_user_group, get_user_group_managed_users,
                          add_managed_user_group_to_user_group, remove_managed_user_group_from_user_group, get_user_group_managed_groups,
                          DEFAULT_GROUP_EVERYONE, DEFAULT_GROUP_ADMINISTRATOR,
                          )
from app.database.models import DBBase, DBUser, DBProject

import unittest
import datetime
from uuid import uuid4


class TestDatabaseModels(unittest.TestCase):
    """Test cases for User and Project models"""

    @classmethod
    def setUpClass(cls):
        """
        setup SessionLocal
        """
        # 使用内存数据库进行测试
        init_database(AppSetting(database_url="sqlite:///:memory:", secret_key="secret_key"))

    def setUp(self):
        """
        creat a session
        """
        # 删除所有表
        DBBase.metadata.drop_all(enter._engine)
        # 创建所有表
        DBBase.metadata.create_all(enter._engine)

    # ========== User Model Tests ==========

    def test_create_user(self):

        with db_context() as session:
            # user = DBUser(
            #     username="testuser",
            #     email="test@example.com"
            # )
            # session.add(user)
            add_user(session, username="testuser", email="test@example.com",
                     username_password=("tt", "123321"))


        with db_context() as session:
            # 从数据库中通过唯一标识符（如 username）把用户找出来
            retrieved_user = session.query(DBUser).filter_by(username="testuser").first()

            # 验证
            # 对查询出的对象进行断言
            self.assertIsNotNone(retrieved_user)  # 首先确保对象被找到了
            self.assertIsNotNone(retrieved_user.uuid)
            self.assertEqual(len(retrieved_user.uuid), 36)
            self.assertEqual(retrieved_user.username, "testuser")
            self.assertTrue(retrieved_user.is_active)
            self.assertIsInstance(retrieved_user.created_at, datetime.datetime)

    def test_user_uuid_auto_generation(self):
        """测试 UUID 自动生成"""

        with db_context() as session:
            user1 = DBUser(username="user1", email="user1@test.com")
            user2 = DBUser(username="user2", email="user2@test.com")
            session.add_all([user1, user2])

        with db_context() as session:
            # UUID 应该不同
            users = find_user_by_email_host(session, 'test.com')
            self.assertNotEqual(users[0].uuid, users[1].uuid)

    def test_user_unique_constraints(self):
        """测试用户唯一性约束"""
        with db_context() as session:
            user1 = DBUser(username="sameuser", email="email1@test.com")
            session.add(user1)

        with self.assertRaises(Exception):  # 会抛出 IntegrityError
            with db_context() as session:
                # 尝试创建相同 username 的用户
                user2 = DBUser(username="sameuser", email="email2@test.com")
                session.add(user2)

        # 尝试创建相同 email 的用户
        with self.assertRaises(Exception):
            with db_context() as session:
                user3 = DBUser(username="diffuser", email="email1@test.com")
                session.add(user3)

    def test_user_nullable_fields(self):
        """测试用户必填字段"""
        # 缺少 username 应该失败
        with self.assertRaises(Exception):
            user = DBUser(email="test@test.com")
            with db_context() as session:
                session.add(user)

    # ========== Project Model Tests ==========

    def test_create_project(self):
        """测试创建项目"""
        # 先创建用户
        with db_context() as session:
            user = DBUser(username="owner", email="owner@test.com")
            session.add(user)

        # 创建项目
        with db_context() as session:
            user = find_user_by_username(session, "owner")[0]
            project = DBProject(
                name="Test Project",
                content="Project content here",
                description="A test project",
                owner_id=user.uuid
            )
            session.add(project)

        # 验证
        with db_context() as session:
            user = find_user_by_username(session, "owner")[0]
            project = find_project_by_name(session, "Test Project")[0]
            self.assertIsNotNone(project.uuid)
            self.assertEqual(project.name, "Test Project")
            self.assertEqual(project.owner_id, user.uuid)
            self.assertIsInstance(project.created_at, datetime.datetime)

    def test_project_optional_description(self):
        """测试项目描述字段可选"""
        user = DBUser(username="owner", email="owner@test.com")
        with db_context() as session:
            session.add(user)

            session.commit()
            session.refresh(user)

            project = DBProject(
                name="No Description Project",
                content="Content",
                owner_id=user.uuid
                # 不提供 description
            )
            session.add(project)

        with db_context() as session:
            project = find_project_by_name(session, "No Description Project")[0]
            self.assertIsNone(project.description)

    # ========== Relationship Tests ==========

    def test_user_project_relationship(self):
        """测试用户和项目的关系"""
        with db_context() as session:
            # 创建用户
            user = DBUser(username="owner", email="owner@test.com")
            session.add(user)
            session.commit()

            # 通过关系添加项目
            project1 = DBProject(name="Proj1", content="Content1", owner_id=user.uuid)
            project2 = DBProject(name="Proj2", content="Content2", owner_id=user.uuid)

            session.add_all([project1, project2])

            # 刷新用户对象
            session.refresh(user)

            # 验证关系
        with db_context() as session:
            user = find_user_by_username(session, "owner")[0]
            project1, project2 = find_project_by_owner_name(session, "owner")

            self.assertEqual(len(user.projects), 2)
            self.assertIn(project1, user.projects)
            self.assertIn(project2, user.projects)

    def test_project_owner_relationship(self):
        """测试从项目访问所有者"""
        # 先 commit user，再创建 project
        with db_context() as session:
            user = DBUser(username="owner", email="owner@test.com")
            session.add(user)
            # 先提交用户
            session.commit()
            # 然后创建项目
            project = DBProject(name="Proj", content="Content", owner_id=user.uuid)
            session.add(project)

        with db_context() as session:
            project = find_project_by_name(session, "Proj")[0]
            user = find_user_by_username(session, "owner")[0]
            # 验证反向关系
            self.assertEqual(project.owner.username, "owner")
            self.assertEqual(project.owner.uuid, user.uuid)

    def test_cascade_delete(self):
        """测试级联删除：删除用户时项目也被删除"""
        with db_context() as session:
            user = DBUser(username="owner", email="owner@test.com")
            session.add(user)
            session.commit()
            session.refresh(user)

            project = DBProject(name="Proj", content="Content", owner_id=user.uuid)
            session.add(project)
            session.commit()
            session.refresh(project)

            project_uuid = project.uuid

        with db_context() as session:
            user = find_user_by_username(session, "owner")[0]
            # 删除用户前先移除与用户组的关联（避免 FK 约束）
            user.user_groups.clear()
            session.delete(user)

        with db_context() as session:
            # 项目应该也被删除
            deleted_project = session.query(DBProject).filter_by(uuid=project_uuid).first()
            # 验证
            self.assertIsNone(deleted_project)

    def test_foreign_key_constraint(self):
        """测试外键约束"""
        from sqlalchemy.exc import IntegrityError
        with self.assertRaises(IntegrityError):
            with db_context() as session:
                # 尝试创建项目但指定不存在的 owner_id
                project = DBProject(name="Proj", content="Content", owner_id="non-existent-uuid")
                session.add(project)


class TestGroupManagement(unittest.TestCase):
    """Test cases for group management features"""

    @classmethod
    def setUpClass(cls):
        """setup SessionLocal"""
        init_database(AppSetting(database_url="sqlite:///:memory:", secret_key="secret_key"))

    def setUp(self):
        """create a session"""
        DBBase.metadata.drop_all(enter._engine)
        DBBase.metadata.create_all(enter._engine)

        # 创建基本数据
        with db_context() as session:
            # 创建用户
            add_user(session, username="user1", email="user1@test.com")
            add_user(session, username="user2", email="user2@test.com")
        with db_context() as session:
            # 创建项目
            user1 = find_user_by_username(session, "user1")[0]
            user2 = find_user_by_username(session, "user2")[0]
            self.user1_uuid = user1.uuid
            self.user2_uuid = user2.uuid
            self.project1_uuid = str(uuid4())
            self.project2_uuid = str(uuid4())
            project1 = DBProject(name="Project1", content="Content1", owner_id=user1.uuid, uuid=self.project1_uuid)
            project2 = DBProject(name="Project2", content="Content2", owner_id=user2.uuid, uuid=self.project2_uuid)
            session.add_all([project1, project2])
        with db_context() as session:
            # 创建用户组
            add_user_group(session, name="admins", description="Admin Group")
            add_user_group(session, name="developers", description="Developers Group")
            add_user_group(session, name="users", description="Users Group")


    # ========== Group Managed Users Tests ==========

    def test_add_managed_user_to_group(self):
        """测试向用户组中添加可管理的用户"""
        with db_context() as session:
            add_managed_user_to_user_group(session, "admins", self.user1_uuid)

        with db_context() as session:
            managed_users = get_user_group_managed_users(session, "admins")
            self.assertEqual(len(managed_users), 1)
            self.assertEqual(managed_users[0].username, "user1")

    def test_add_managed_user_to_nonexistent_group_raises_error(self):
        """测试向不存在的用户组添加可管理用户会引发错误"""
        with self.assertRaises(KeyError):
            with db_context() as session:
                add_managed_user_to_user_group(session, "nonexistent_group", self.user1_uuid)

    def test_add_nonexistent_user_to_group_raises_error(self):
        """测试向用户组中添加不存在的用户会引发错误"""
        with self.assertRaises(KeyError):
            with db_context() as session:
                add_managed_user_to_user_group(session, "admins", "nonexistent-uuid")

    def test_add_managed_user_twice_raises_error(self):
        """测试重复添加可管理用户会引发错误"""
        with db_context() as session:
            add_managed_user_to_user_group(session, "admins", self.user1_uuid)

        with self.assertRaises(ValueError):
            with db_context() as session:
                add_managed_user_to_user_group(session, "admins", self.user1_uuid)

    def test_remove_managed_user_from_group(self):
        """测试从用户组中移除可管理的用户"""
        with db_context() as session:
            add_managed_user_to_user_group(session, "admins", self.user1_uuid)

        with db_context() as session:
            remove_managed_user_from_user_group(session, "admins", self.user1_uuid)

        with db_context() as session:
            managed_users = get_user_group_managed_users(session, "admins")
            self.assertEqual(len(managed_users), 0)

    def test_remove_managed_user_from_nonexistent_group_raises_error(self):
        """测试从不存在的用户组移除可管理用户会引发错误"""
        with self.assertRaises(KeyError):
            with db_context() as session:
                remove_managed_user_from_user_group(session, "nonexistent_group", self.user1_uuid)

    def test_remove_nonexistent_managed_user_raises_error(self):
        """测试移除不被管理的用户会引发错误"""
        with self.assertRaises(ValueError):
            with db_context() as session:
                remove_managed_user_from_user_group(session, "admins", self.user1_uuid)

    def test_get_group_managed_users(self):
        """测试获取用户组可管理的所有用户"""
        with db_context() as session:
            add_managed_user_to_user_group(session, "admins", self.user1_uuid)
            add_managed_user_to_user_group(session, "admins", self.user2_uuid)

        with db_context() as session:
            managed_users = get_user_group_managed_users(session, "admins")
            self.assertEqual(len(managed_users), 2)
            usernames = [u.username for u in managed_users]
            self.assertIn("user1", usernames)
            self.assertIn("user2", usernames)

    # ========== User Group Managed Groups Tests ==========

    def test_add_managed_user_group_to_user_group(self):
        """测试向用户组中添加可管理的用户组"""
        with db_context() as session:
            add_managed_user_group_to_user_group(session, "admins", "developers")

        with db_context() as session:
            managed_groups = get_user_group_managed_groups(session, "admins")
            self.assertEqual(len(managed_groups), 1)
            self.assertEqual(managed_groups[0].name, "developers")

    def test_add_managed_group_to_itself_raises_error(self):
        """测试一个组不能管理自己"""
        with self.assertRaises(ValueError):
            with db_context() as session:
                add_managed_user_group_to_user_group(session, "admins", "admins")

    def test_add_managed_group_circular_dependency_raises_error(self):
        """测试添加可管理组时循环依赖会引发错误"""
        with db_context() as session:
            add_managed_user_group_to_user_group(session, "admins", "developers")

        with self.assertRaises(ValueError):
            with db_context() as session:
                add_managed_user_group_to_user_group(session, "developers", "admins")

    def test_remove_managed_user_group_from_user_group(self):
        """测试从组中移除可管理的组"""
        with db_context() as session:
            add_managed_user_group_to_user_group(session, "admins", "developers")

        with db_context() as session:
            remove_managed_user_group_from_user_group(session, "admins", "developers")

        with db_context() as session:
            managed_groups = get_user_group_managed_groups(session, "admins")
            self.assertEqual(len(managed_groups), 0)

    def test_get_user_group_managed_groups(self):
        """测试获取组可管理的所有组"""
        with db_context() as session:
            add_managed_user_group_to_user_group(session, "admins", "developers")
            add_managed_user_group_to_user_group(session, "admins", "users")

        with db_context() as session:
            managed_groups = get_user_group_managed_groups(session, "admins")
            self.assertEqual(len(managed_groups), 2)
            group_names = [g.name for g in managed_groups]
            self.assertIn("developers", group_names)
            self.assertIn("users", group_names)


class TestGroupModels(unittest.TestCase):
    """Test cases for Group models and user-group relationships"""

    @classmethod
    def setUpClass(cls):
        """setup SessionLocal"""
        init_database(AppSetting(database_url="sqlite:///:memory:", secret_key="secret_key"))

    def setUp(self):
        """creat a session"""
        DBBase.metadata.drop_all(enter._engine)
        DBBase.metadata.create_all(enter._engine)

    # ========== Group Model Tests ==========

    def test_create_group(self):
        """测试创建用户组"""
        with db_context() as session:
            ug = add_user_group(session, name="admin", description="管理员组")

        with db_context() as session:
            groups = find_user_group_by_name(session, "admin")
            self.assertEqual(len(groups), 1)
            self.assertEqual(groups[0].name, "admin")
            self.assertEqual(groups[0].description, "管理员组")
            self.assertIsNotNone(groups[0].uuid)
            self.assertEqual(len(groups[0].uuid), 36)

    def test_create_group_with_uuid(self):
        """测试使用指定 UUID 创建用户组"""
        custom_uuid = "12345678-1234-1234-1234-123456789012"
        with db_context() as session:
            group = add_user_group(session, name="developers", uuid=custom_uuid)

        with db_context() as session:
            groups = find_user_group_by_uuid(session, custom_uuid)
            self.assertEqual(len(groups), 1)
            self.assertEqual(groups[0].uuid, custom_uuid)

    def test_create_duplicate_group_raises_error(self):
        """测试创建重复组名会抛出错误"""
        with db_context() as session:
            add_user_group(session, name="admin")

        with self.assertRaises(ValueError):
            with db_context() as session:
                add_user_group(session, name="admin")

    def test_find_all_groups(self):
        """测试获取所有用户组"""
        with db_context() as session:
            add_user_group(session, name="admin")
            add_user_group(session, name="users")
            add_user_group(session, name="developers")

        with db_context() as session:
            groups = find_all_user_groups(session)
            self.assertEqual(len(groups), 5)  # everyone + administrator + admin + users + developers
            group_names = [g.name for g in groups]
            self.assertIn(DEFAULT_GROUP_EVERYONE, group_names)
            self.assertIn(DEFAULT_GROUP_ADMINISTRATOR, group_names)
            self.assertIn("admin", group_names)
            self.assertIn("users", group_names)
            self.assertIn("developers", group_names)

    def test_update_group(self):
        """测试更新用户组"""
        with db_context() as session:
            add_user_group(session, name="old_name", description="旧描述")

        with db_context() as session:
            updated = update_user_group(session, name="old_name", 
                                   new_name="new_name", description="新描述")
            self.assertEqual(updated.name, "new_name")
            self.assertEqual(updated.description, "新描述")

        with db_context() as session:
            groups = find_user_group_by_name(session, "new_name")
            self.assertEqual(len(groups), 1)
            self.assertEqual(groups[0].description, "新描述")

    def test_update_group_duplicate_name_raises_error(self):
        """测试更新组名为已存在的组名会抛出错误"""
        with db_context() as session:
            add_user_group(session, name="group1")
            add_user_group(session, name="group2")

        with self.assertRaises(ValueError):
            with db_context() as session:
                update_user_group(session, name="group1", new_name="group2")

    def test_update_nonexistent_group_raises_error(self):
        """测试更新不存在的组会抛出错误"""
        with self.assertRaises(KeyError):
            with db_context() as session:
                update_user_group(session, name="nonexistent")

    def test_delete_group(self):
        """测试删除用户组"""
        with db_context() as session:
            add_user_group(session, name="to_delete")

        with db_context() as session:
            result = delete_user_group(session, name="to_delete")
            self.assertTrue(result)

        with db_context() as session:
            groups = find_user_group_by_name(session, "to_delete")
            self.assertEqual(len(groups), 0)

    def test_delete_nonexistent_group_raises_error(self):
        """测试删除不存在的组会抛出错误"""
        with self.assertRaises(KeyError):
            with db_context() as session:
                delete_user_group(session, name="nonexistent")

    def test_delete_system_group_raises_error(self):
        """测试删除系统组 everyone/administrator 会抛出错误"""
        for group_name in (DEFAULT_GROUP_EVERYONE, DEFAULT_GROUP_ADMINISTRATOR):
            with self.subTest(group=group_name):
                with self.assertRaises(ValueError) as ctx:
                    with db_context() as session:
                        delete_user_group(session, name=group_name)
                self.assertIn(group_name, str(ctx.exception))

    # ========== User-Group Relationship Tests ==========

    def test_add_user_to_group(self):
        """测试将用户添加到组"""
        with db_context() as session:
            user = DBUser(username="testuser", email="test@example.com")
            session.add(user)
            add_user_group(session, name="admin")

        with db_context() as session:
            user = find_user_by_username(session, "testuser")[0]
            add_user_to_user_group(session, user.uuid, "admin")

        with db_context() as session:
            user = find_user_by_username(session, "testuser")[0]
            # 首个用户自动加入 everyone + administrator，再加 admin
            self.assertGreaterEqual(len(user.user_groups), 3)
            group_names = [g.name for g in user.user_groups]
            self.assertIn(DEFAULT_GROUP_EVERYONE, group_names)
            self.assertIn(DEFAULT_GROUP_ADMINISTRATOR, group_names)
            self.assertIn("admin", group_names)

    def test_add_user_to_multiple_groups(self):
        """测试将用户添加到多个组"""
        with db_context() as session:
            user = DBUser(username="testuser", email="test@example.com")
            session.add(user)
            add_user_group(session, name="admin")
            add_user_group(session, name="developers")
            add_user_group(session, name="users")

        with db_context() as session:
            user = find_user_by_username(session, "testuser")[0]
            add_user_to_user_group(session, user.uuid, "admin")
            add_user_to_user_group(session, user.uuid, "developers")
            add_user_to_user_group(session, user.uuid, "users")

        with db_context() as session:
            user = find_user_by_username(session, "testuser")[0]
            # 首个用户有 everyone + administrator，再加 admin + developers + users
            self.assertGreaterEqual(len(user.user_groups), 5)
            group_names = [g.name for g in user.user_groups]
            self.assertIn("admin", group_names)
            self.assertIn("developers", group_names)
            self.assertIn("users", group_names)

    def test_add_user_to_same_group_twice_raises_error(self):
        """测试重复添加用户到同一组会抛出错误"""
        with db_context() as session:
            user = DBUser(username="testuser", email="test@example.com")
            session.add(user)
            add_user_group(session, name="admin")

        with db_context() as session:
            user = find_user_by_username(session, "testuser")[0]
            add_user_to_user_group(session, user.uuid, "admin")

        with self.assertRaises(ValueError):
            with db_context() as session:
                user = find_user_by_username(session, "testuser")[0]
                add_user_to_user_group(session, user.uuid, "admin")

    def test_remove_user_from_group(self):
        """测试从组中移除用户"""
        with db_context() as session:
            user = DBUser(username="testuser", email="test@example.com")
            session.add(user)
            add_user_group(session, name="admin")

        with db_context() as session:
            user = find_user_by_username(session, "testuser")[0]
            add_user_to_user_group(session, user.uuid, "admin")

        with db_context() as session:
            user = find_user_by_username(session, "testuser")[0]
            remove_user_from_user_group(session, user.uuid, "admin")

        with db_context() as session:
            user = find_user_by_username(session, "testuser")[0]
            # 移除 admin 后仍保留 everyone + administrator（不可移除）
            self.assertGreaterEqual(len(user.user_groups), 2)
            group_names = [g.name for g in user.user_groups]
            self.assertIn(DEFAULT_GROUP_EVERYONE, group_names)
            self.assertIn(DEFAULT_GROUP_ADMINISTRATOR, group_names)

    def test_remove_user_from_everyone_raises_error(self):
        """测试从 everyone 组移除用户会抛出错误"""
        with db_context() as session:
            user = DBUser(username="testuser", email="test@example.com")
            session.add(user)

        with self.assertRaises(ValueError) as ctx:
            with db_context() as session:
                user = find_user_by_username(session, "testuser")[0]
                remove_user_from_user_group(session, user.uuid, DEFAULT_GROUP_EVERYONE)
        self.assertIn("everyone", str(ctx.exception))

    def test_remove_user_not_in_group_raises_error(self):
        """测试移除不在组中的用户会抛出错误"""
        with db_context() as session:
            user = DBUser(username="testuser", email="test@example.com")
            session.add(user)
            add_user_group(session, name="admin")

        with self.assertRaises(ValueError):
            with db_context() as session:
                user = find_user_by_username(session, "testuser")[0]
                remove_user_from_user_group(session, user.uuid, "admin")

    def test_get_user_groups(self):
        """测试获取用户所属的所有组"""
        with db_context() as session:
            user = DBUser(username="testuser", email="test@example.com")
            session.add(user)
            add_user_group(session, name="admin")
            add_user_group(session, name="developers")

        with db_context() as session:
            user = find_user_by_username(session, "testuser")[0]
            add_user_to_user_group(session, user.uuid, "admin")
            add_user_to_user_group(session, user.uuid, "developers")

        with db_context() as session:
            user = find_user_by_username(session, "testuser")[0]
            groups = get_user_managed_user_groups(session, user.uuid)
            # everyone + administrator + admin + developers
            self.assertGreaterEqual(len(groups), 4)
            group_names = [g.name for g in groups]
            self.assertIn("admin", group_names)
            self.assertIn("developers", group_names)

    def test_get_group_users(self):
        """测试获取组中的所有用户"""
        with db_context() as session:
            user1 = DBUser(username="user1", email="user1@example.com")
            user2 = DBUser(username="user2", email="user2@example.com")
            session.add_all([user1, user2])
            add_user_group(session, name="admin")

        with db_context() as session:
            user1 = find_user_by_username(session, "user1")[0]
            user2 = find_user_by_username(session, "user2")[0]
            add_user_to_user_group(session, user1.uuid, "admin")
            add_user_to_user_group(session, user2.uuid, "admin")

        with db_context() as session:
            users = get_user_group_users(session, "admin")
            self.assertEqual(len(users), 2)
            usernames = [u.username for u in users]
            self.assertIn("user1", usernames)
            self.assertIn("user2", usernames)

    def test_find_users_by_group(self):
        """测试通过组名查找用户"""
        with db_context() as session:
            user1 = DBUser(username="admin_user", email="admin@example.com")
            user2 = DBUser(username="dev_user", email="dev@example.com")
            session.add_all([user1, user2])
            add_user_group(session, name="admin")
            add_user_group(session, name="developers")

        with db_context() as session:
            user1 = find_user_by_username(session, "admin_user")[0]
            user2 = find_user_by_username(session, "dev_user")[0]
            add_user_to_user_group(session, user1.uuid, "admin")
            add_user_to_user_group(session, user2.uuid, "developers")

        with db_context() as session:
            admin_users = find_users_by_user_group(session, "admin")
            self.assertEqual(len(admin_users), 1)
            self.assertEqual(admin_users[0].username, "admin_user")

            dev_users = find_users_by_user_group(session, "developers")
            self.assertEqual(len(dev_users), 1)
            self.assertEqual(dev_users[0].username, "dev_user")

    def test_add_user_with_groups(self):
        """测试创建用户时直接分配组"""
        with db_context() as session:
            add_user_group(session, name="admin")
            add_user_group(session, name="users")

        with db_context() as session:
            user = add_user(session, 
                           username="newuser", 
                           email="new@example.com",
                           groups=["admin", "users"])

        with db_context() as session:
            user = find_user_by_username(session, "newuser")[0]
            # 首个用户有 everyone + administrator + admin + users
            self.assertGreaterEqual(len(user.user_groups), 4)
            group_names = [g.name for g in user.user_groups]
            self.assertIn("admin", group_names)
            self.assertIn("users", group_names)

    def test_add_user_with_nonexistent_group_raises_error(self):
        """测试创建用户时指定不存在的组会抛出错误"""
        with self.assertRaises(KeyError):
            with db_context() as session:
                add_user(session,
                        username="newuser",
                        email="new@example.com",
                        groups=["nonexistent_group"])

    def test_group_bidirectional_relationship(self):
        """测试组与用户的双向关系"""
        with db_context() as session:
            user = DBUser(username="testuser", email="test@example.com")
            session.add(user)
            ug = add_user_group(session, name="admin")

        with db_context() as session:
            user = find_user_by_username(session, "testuser")[0]
            add_user_to_user_group(session, user.uuid, "admin")

        with db_context() as session:
            # 从用户端检查
            user = find_user_by_username(session, "testuser")[0]
            self.assertGreaterEqual(len(user.user_groups), 3)
            group_names = [g.name for g in user.user_groups]
            self.assertIn("admin", group_names)

            # 从组端检查
            group = find_user_group_by_name(session, "admin")[0]
            self.assertEqual(len(group.users), 1)
            self.assertEqual(group.users[0].username, "testuser")


if __name__ == "__main__":
    unittest.main()