"""Interactively create a farm-team owner; never take passwords in command arguments."""

import argparse
import getpass
from pathlib import Path

from crop_twin.application.identity_service import IdentityService
from crop_twin.core.settings import Settings
from crop_twin.domain.identity.rules import IdentityError
from crop_twin.infrastructure.database.identity_repository import SqlIdentityRepository
from crop_twin.infrastructure.database.session import build_engine, reserve_sqlite_writer
from crop_twin.infrastructure.passwords import Argon2Passwords
from dotenv import load_dotenv
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session


def main() -> None:
    """Create an explicit initial owner in the configured, already migrated database."""
    parser = argparse.ArgumentParser(description="建立农田组织及管理员；先运行 init-db")
    parser.add_argument("--username", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--organization", required=True)
    parser.add_argument(
        "--adopt-legacy", action="store_true", help="明确接收当前未归属的 M1 旧地块"
    )
    arguments = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    password = getpass.getpass("设置管理员密码（12–128 字符，不显示）：")
    if password != getpass.getpass("再次输入密码："):
        raise SystemExit("两次密码不同，未创建账号")
    engine = build_engine(Settings().database_url.get_secret_value())
    try:
        with Session(engine) as session, session.begin():
            reserve_sqlite_writer(session)
            service = IdentityService(SqlIdentityRepository(session), Argon2Passwords())
            _, adopted = service.bootstrap(
                arguments.username,
                arguments.display_name,
                password,
                arguments.organization,
                adopt_legacy=arguments.adopt_legacy,
            )
    except IdentityError as error:
        raise SystemExit(error.message) from None
    except DBAPIError:
        raise SystemExit("数据存储不可用，请检查初始化、数据库连接与权限") from None
    finally:
        engine.dispose()
    print(f"管理员已建立，接收旧地块 {adopted} 块；请在页面登录。")


if __name__ == "__main__":
    main()
