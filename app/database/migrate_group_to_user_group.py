"""
一次性迁移脚本：将 group 相关表重构为 user_group。

执行前请备份数据库。
适用于 SQLite；若使用其他数据库请根据其 DDL 调整或使用新库 create_all。

用法（在项目根目录）:
    python -m app.database.migrate_group_to_user_group
"""
from __future__ import annotations

import os
import sys

# 确保可导入 app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.settings import load_config


def run_sqlite_migration(conn):
    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        cursor = conn.cursor()

        # 1. 删除组-项目关联表
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='group_managed_projects_association'"
        )
        if cursor.fetchone():
            cursor.execute("DROP TABLE group_managed_projects_association")

        # 2. 重命名 groups -> user_groups
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='groups'")
        if cursor.fetchone():
            cursor.execute("ALTER TABLE groups RENAME TO user_groups")

        # 3. user_group_association: 旧表为 (user_id, group_id)，新表为 (user_id, user_group_id)
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_group_association'"
        )
        if cursor.fetchone():
            cursor.execute(
                """
                CREATE TABLE user_group_association_new (
                    user_id VARCHAR(36) NOT NULL,
                    user_group_id VARCHAR(36) NOT NULL,
                    PRIMARY KEY (user_id, user_group_id),
                    FOREIGN KEY (user_id) REFERENCES users(uuid),
                    FOREIGN KEY (user_group_id) REFERENCES user_groups(uuid)
                )
                """
            )
            cursor.execute(
                "INSERT INTO user_group_association_new (user_id, user_group_id) SELECT user_id, group_id FROM user_group_association"
            )
            cursor.execute("DROP TABLE user_group_association")
            cursor.execute("ALTER TABLE user_group_association_new RENAME TO user_group_association")

        # 4. group_managed_users_association -> user_group_managed_users_association
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='group_managed_users_association'"
        )
        if cursor.fetchone():
            cursor.execute(
                """
                CREATE TABLE user_group_managed_users_association (
                    user_group_id VARCHAR(36) NOT NULL,
                    user_id VARCHAR(36) NOT NULL,
                    PRIMARY KEY (user_group_id, user_id),
                    FOREIGN KEY (user_group_id) REFERENCES user_groups(uuid),
                    FOREIGN KEY (user_id) REFERENCES users(uuid)
                )
                """
            )
            cursor.execute(
                """
                INSERT INTO user_group_managed_users_association (user_group_id, user_id)
                SELECT group_id, user_id FROM group_managed_users_association
                """
            )
            cursor.execute("DROP TABLE group_managed_users_association")

        # 5. group_managed_groups_association -> user_group_managed_groups_association
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='group_managed_groups_association'"
        )
        if cursor.fetchone():
            cursor.execute(
                """
                CREATE TABLE user_group_managed_groups_association (
                    manager_user_group_id VARCHAR(36) NOT NULL,
                    managed_user_group_id VARCHAR(36) NOT NULL,
                    PRIMARY KEY (manager_user_group_id, managed_user_group_id),
                    FOREIGN KEY (manager_user_group_id) REFERENCES user_groups(uuid),
                    FOREIGN KEY (managed_user_group_id) REFERENCES user_groups(uuid)
                )
                """
            )
            cursor.execute(
                """
                INSERT INTO user_group_managed_groups_association (manager_user_group_id, managed_user_group_id)
                SELECT manager_group_id, managed_group_id FROM group_managed_groups_association
                """
            )
            cursor.execute("DROP TABLE group_managed_groups_association")

        conn.commit()
    finally:
        conn.execute("PRAGMA foreign_keys=ON")


def main():
    config = load_config()
    url = config.database_url
    if not url.lower().startswith("sqlite"):
        print("此脚本仅针对 SQLite。其他数据库请备份后手动迁移或使用新库 create_all。")
        sys.exit(1)

    import sqlite3

    # 从 URL 解析路径，如 sqlite:///./foo.db -> ./foo.db
    if url.startswith("sqlite:///"):
        path = url.replace("sqlite:///", "", 1)
    else:
        path = url.replace("sqlite://", "", 1)
    if not path or path == ":memory:":
        print("内存数据库无需迁移。")
        return

    print(f"正在迁移数据库: {path}")
    conn = sqlite3.connect(path)
    try:
        run_sqlite_migration(conn)
        print("迁移完成。")
    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
