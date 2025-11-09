"""
Unit tests for database models
"""
from app.database.models import DBBase, DBUser, DBProject

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

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
        cls.engine = create_engine("sqlite:///:memory:", echo=False)

        # SQLite 启用外键约束
        @event.listens_for(cls.engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        cls.SessionLocal = sessionmaker(bind=cls.engine)

    def setUp(self):
        """
        creat a session
        """
        # 创建所有表
        DBBase.metadata.create_all(self.engine)
        # 创建新的 session
        self.session: Session = self.SessionLocal()

    def tearDown(self):
        """
        close session and delete all tables.
        """
        self.session.close()
        # 删除所有表
        DBBase.metadata.drop_all(self.engine)

    # ========== User Model Tests ==========

    def test_create_user(self):
        user = DBUser(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_pw_123"
        )
        self.session.add(user)
        self.session.commit()

        # 验证
        self.assertIsNotNone(user.uuid)
        self.assertEqual(len(user.uuid), 36)  # UUID 字符串长度
        self.assertEqual(user.username, "testuser")
        self.assertTrue(user.is_active)  # 默认为 True
        self.assertIsInstance(user.created_at, datetime.datetime)

    def test_user_uuid_auto_generation(self):
        """测试 UUID 自动生成"""
        user1 = DBUser(username="user1", email="user1@test.com", hashed_password="pw1")
        user2 = DBUser(username="user2", email="user2@test.com", hashed_password="pw2")

        self.session.add_all([user1, user2])
        self.session.commit()

        # UUID 应该不同
        self.assertNotEqual(user1.uuid, user2.uuid)

    def test_user_unique_constraints(self):
        """测试用户唯一性约束"""
        user1 = DBUser(username="sameuser", email="email1@test.com", hashed_password="pw")
        self.session.add(user1)
        self.session.commit()

        # 尝试创建相同 username 的用户
        user2 = DBUser(username="sameuser", email="email2@test.com", hashed_password="pw")
        self.session.add(user2)

        with self.assertRaises(Exception):  # 会抛出 IntegrityError
            self.session.commit()

        self.session.rollback()

        # 尝试创建相同 email 的用户
        user3 = DBUser(username="diffuser", email="email1@test.com", hashed_password="pw")
        self.session.add(user3)

        with self.assertRaises(Exception):
            self.session.commit()

    def test_user_nullable_fields(self):
        """测试用户必填字段"""
        # 缺少 username 应该失败
        with self.assertRaises(Exception):
            user = DBUser(email="test@test.com", hashed_password="pw")
            self.session.add(user)
            self.session.commit()

    # ========== Project Model Tests ==========

    def test_create_project(self):
        """测试创建项目"""
        # 先创建用户
        user = DBUser(username="owner", email="owner@test.com", hashed_password="pw")
        self.session.add(user)
        self.session.commit()

        # 创建项目
        project = DBProject(
            name="Test Project",
            content="Project content here",
            description="A test project",
            owner_id=user.uuid
        )
        self.session.add(project)
        self.session.commit()

        # 验证
        self.assertIsNotNone(project.uuid)
        self.assertEqual(project.name, "Test Project")
        self.assertEqual(project.owner_id, user.uuid)
        self.assertIsInstance(project.created_at, datetime.datetime)

    def test_project_optional_description(self):
        """测试项目描述字段可选"""
        user = DBUser(username="owner", email="owner@test.com", hashed_password="pw")
        self.session.add(user)
        self.session.commit()

        project = DBProject(
            name="No Description Project",
            content="Content",
            owner_id=user.uuid
            # 不提供 description
        )
        self.session.add(project)
        self.session.commit()

        self.assertIsNone(project.description)

    # ========== Relationship Tests ==========

    def test_user_project_relationship(self):
        """测试用户和项目的关系"""
        user = DBUser(username="owner", email="owner@test.com", hashed_password="pw")
        self.session.add(user)
        self.session.commit()

        # 通过关系添加项目
        project1 = DBProject(name="Proj1", content="Content1", owner_id=user.uuid)
        project2 = DBProject(name="Proj2", content="Content2", owner_id=user.uuid)

        self.session.add_all([project1, project2])
        self.session.commit()

        # 刷新用户对象
        self.session.refresh(user)

        # 验证关系
        self.assertEqual(len(user.projects), 2)
        self.assertIn(project1, user.projects)
        self.assertIn(project2, user.projects)

    def test_project_owner_relationship(self):
        """测试从项目访问所有者"""
        # ✅ 修复：先 commit user，再创建 project
        user = DBUser(username="owner", email="owner@test.com", hashed_password="pw")
        self.session.add(user)
        self.session.commit()  # 先提交用户

        # 然后创建项目
        project = DBProject(name="Proj", content="Content", owner_id=user.uuid)
        self.session.add(project)
        self.session.commit()

        # 刷新项目对象
        self.session.refresh(project)

        # 验证反向关系
        self.assertEqual(project.owner.username, "owner")
        self.assertEqual(project.owner.uuid, user.uuid)

    def test_cascade_delete(self):
        """测试级联删除：删除用户时项目也被删除"""
        user = DBUser(username="owner", email="owner@test.com", hashed_password="pw")
        self.session.add(user)
        self.session.commit()

        project = DBProject(name="Proj", content="Content", owner_id=user.uuid)
        self.session.add(project)
        self.session.commit()

        project_uuid = project.uuid

        # 删除用户
        self.session.delete(user)
        self.session.commit()

        # 项目应该也被删除
        deleted_project = self.session.query(DBProject).filter_by(uuid=project_uuid).first()
        self.assertIsNone(deleted_project)

    def test_foreign_key_constraint(self):
        """测试外键约束"""
        # 尝试创建项目但指定不存在的 owner_id
        project = DBProject(
            name="Orphan Project",
            content="Content",
            owner_id="non-existent-uuid"
        )
        self.session.add(project)

        # ✅ 修复：现在 SQLite 会正确抛出外键错误
        from sqlalchemy.exc import IntegrityError
        with self.assertRaises(IntegrityError):
            self.session.commit()

    # ========== Query Tests ==========

    def test_query_user_by_username(self):
        """测试按用户名查询"""
        user = DBUser(username="findme", email="find@test.com", hashed_password="pw")
        self.session.add(user)
        self.session.commit()

        found_user = self.session.query(DBUser).filter_by(username="findme").first()
        self.assertIsNotNone(found_user)
        self.assertEqual(found_user.email, "find@test.com")

    def test_query_projects_by_user(self):
        """测试查询用户的所有项目"""
        user = DBUser(username="owner", email="owner@test.com", hashed_password="pw")
        self.session.add(user)
        self.session.commit()

        for i in range(3):
            project = DBProject(
                name=f"Project {i}",
                content=f"Content {i}",
                owner_id=user.uuid
            )
            self.session.add(project)
        self.session.commit()

        projects = self.session.query(DBProject).filter_by(owner_id=user.uuid).all()
        self.assertEqual(len(projects), 3)


if __name__ == "__main__":
    unittest.main()