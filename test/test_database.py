"""
Unit tests for database models
"""
from app.database import enter
from app.core.settings import AppSetting
from app.database import (init_database, db_context,
                          add_user,
                          find_user_by_username, find_user_by_email_host,
                          find_project_by_owner_name, find_project_by_name)
from app.database.models import DBBase, DBUser, DBProject

import unittest
import datetime


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
            # 删除用户
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
                project = DBProject(
                    name="Orphan Project",
                    content="Content",
                    owner_id="non-existent-uuid"
                )
                session.add(project)

if __name__ == "__main__":
    unittest.main()