import os
import typer
import subprocess
from pathlib import Path
import re
from typing import List, Dict, Any
from dotenv import load_dotenv
from textwrap import dedent

# 创建一个 Typer 应用实例
cli_app = typer.Typer()


def to_pascal_case(s: str) -> str:
    """将 snake_case 或普通字符串转换为 PascalCase。"""
    return "".join(word.capitalize() for word in s.split('_'))


def get_db_url_from_env() -> str:
    """
    从 .env 文件读取 DATABASE_URL，并自动将其转换为同步链接供脚本使用。
    """
    project_root = Path.cwd()
    dotenv_path = project_root / '.env'
    if not dotenv_path.is_file():
        raise FileNotFoundError(f"错误: 在项目根目录 '{project_root}' 中未找到 .env 文件。")

    load_dotenv(dotenv_path=dotenv_path)
    # 脚本总是读取主应用的 DATABASE_URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError(f"错误: 已加载 '{dotenv_path}' 文件，但在其中未找到 DATABASE_URL 变量。")

    # ⭐ 核心逻辑：自动将异步驱动替换为同步驱动
    if "+asyncmy" in db_url:
        sync_db_url = db_url.replace("+asyncmy", "+pymysql")
        typer.secho(f"  -> 检测到异步URL，已自动转换为同步URL供脚本使用。", fg=typer.colors.BLUE)
        typer.secho(f"     原始: {db_url}", dim=True)
        typer.secho(f"     转换后: {sync_db_url}", dim=True)
        return sync_db_url

    # 如果已经是同步的或无法识别，则直接返回
    return db_url


def parse_sqlalchemy_model(content: str) -> Dict[str, Any]:
    """解析器现在只负责提取基本信息，不再提取代码块。"""
    class_name_match = re.search(r"class\s+(\w+)\(Base\):", content)
    if not class_name_match:
        raise ValueError("无法解析模型类名。")
    class_name = class_name_match.group(1)

    pk_match = re.search(r"(\w+):\s*Mapped\[.*?primary_key=True", content)
    if not pk_match:
        raise ValueError("无法解析主键。")
    primary_key = pk_match.group(1)

    fields = []
    for match in re.finditer(r"^\s*(\w+):\s*Mapped\[(Optional\[)?([\w\.]+)\]?", content, re.MULTILINE):
        field_name, is_optional, field_type = match.groups()
        if field_name == primary_key:
            continue
        fields.append({"name": field_name, "type": field_type, "optional": bool(is_optional)})

    return {"class_name": class_name, "primary_key": primary_key, "fields": fields}


# ... generate_schema_code 函数保持不变 ...
def generate_schema_code(entity_pascal: str, pk_name: str, fields: List[Dict]) -> str:
    def map_type(t: str) -> str:
        return {"str": "str", "int": "int", "float": "float", "date": "date", "datetime": "datetime"}.get(t, "Any")

    base_fields = "\n".join([f"    {f['name']}: Optional[{map_type(f['type'])}] = None" for f in fields])
    create_fields = "\n".join([f"    {f['name']}: {map_type(f['type'])}" for f in fields if not f['optional']])
    update_fields = "\n".join([f"    {f['name']}: Optional[{map_type(f['type'])}] = None" for f in fields])
    return f"""
# --- (自动生成) {entity_pascal} Schemas ---
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any

class {entity_pascal}Base(BaseModel):
{base_fields if base_fields else '    pass'}

class {entity_pascal}Create({entity_pascal}Base):
{create_fields if create_fields else '    pass'}

class {entity_pascal}Update(BaseModel):
{update_fields if update_fields else '    pass'}

class {entity_pascal}Read({entity_pascal}Base):
    {pk_name}: int
    model_config = ConfigDict(from_attributes=True)

class {entity_pascal}sResponse(BaseModel):
    data: List[{entity_pascal}Read]
    total_count: int
"""


# ⭐ 1. generate_router_code 做了微小调整，以适应新的模型导入路径
def generate_router_code(entity_name: str, model_name: str, pk_name: str) -> str:
    """动态生成完整的路由文件代码。"""
    entity_pascal = to_pascal_case(entity_name)
    return f"""
# --- (自动生成) {entity_pascal} Router ---
import logging

# 从库中导入核心工具
from app.core.actions_router import create_actions_router, CRUDSchemas
from app.core.logging_crud import LoggingFastCRUD

# 导入本项目的模型和 Schemas
from models.{entity_name} import {model_name} # 路径从 'models' 改为 'models.{entity_name}'
from schemas import (
    {entity_pascal}Create,
    {entity_pascal}Update,
    {entity_pascal}Read,
    {entity_pascal}sResponse,
)

logger = logging.getLogger(__name__)

# 准备 CRUD 实例和 Schema 集合
crud_instance = LoggingFastCRUD({model_name})
schemas = CRUDSchemas(
    Create={entity_pascal}Create,
    Update={entity_pascal}Update,
    Read={entity_pascal}Read,
    MultiResponse={entity_pascal}sResponse,
)

# 调用工厂函数，一键生成路由器
router = create_actions_router(
    crud_instance=crud_instance,
    schemas=schemas,
    prefix="/{entity_name}s",
    tags=["{entity_pascal}"],
    primary_key_name="{pk_name}"
)
"""


@cli_app.command("generate")
def generate_module(
        table_name: str = typer.Argument(..., help="数据库中的表名 (例如: promotions)"),
        entity_name: str = typer.Option(None, "--entity", "-e", help="实体名称 (单数, 小写, 例如: promotion)"),
):
    """从一个数据库表，自动生成并集成 Model, Schema, 和 Router 代码。"""
    if not entity_name:
        entity_name = table_name.rstrip('s')

    typer.secho(f"--- 自动化模块生成器 ---", bold=True)
    project_root = Path.cwd()
    temp_model_file = project_root / f"_temp_{entity_name}_model.py"

    try:
        # 1. 生成模型到临时文件
        typer.echo(f"\n[1/5] 从表 '{table_name}' 生成 SQLAlchemy 模型...")
        db_url = get_db_url_from_env()
        command = ["sqlacodegen", db_url, "--tables", table_name, "--outfile", str(temp_model_file)]
        # ⭐ 2. 增加 --no-declarative-base 选项
        # 解释：因为每个文件都是独立的，我们不希望 sqlacodegen 在每个文件里都生成一个 Base = declarative_base()。
        # 相反，我们应该有一个统一的 app/db/base.py 文件来定义 Base，然后在每个模型文件中导入它。
        # 为了简化，我们暂时先让它在每个文件里生成，但这是一个可以优化的点。
        # 更新：更简单的做法是让它生成，然后我们用代码替换掉。
        result = subprocess.run(command, check=False, capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0:
            raise RuntimeError(f"sqlacodegen 执行失败: {result.stderr}")

        # 2. 解析模型基本信息
        typer.echo(f"[2/5] 解析生成的模型...")
        model_content_raw = temp_model_file.read_text(encoding='utf-8')
        parsed_info = parse_sqlalchemy_model(model_content_raw)

        # 命名修正逻辑 (保持不变)
        original_model_name = parsed_info['class_name']
        correct_model_name = to_pascal_case(entity_name)
        if original_model_name != correct_model_name:
            typer.secho(f"  -> 命名修正: 将模型名从 '{original_model_name}' 强制更正为 '{correct_model_name}'。",
                        fg=typer.colors.YELLOW)
            model_content_raw = model_content_raw.replace(
                f"class {original_model_name}(Base):",
                f"class {correct_model_name}(Base):"
            )
            parsed_info['class_name'] = correct_model_name

        # ⭐ 3. 新增逻辑：确保所有模型都从一个统一的 Base 继承
        # 假设您有一个 `app/db/base_class.py` 文件，内容是 `from sqlalchemy.orm import declarative_base; Base = declarative_base()`
        # 我们将替换 sqlacodegen 生成的 Base 定义
        model_content_final = re.sub(
            r"from sqlalchemy.orm import DeclarativeBase\n\nclass Base\(DeclarativeBase\):\n    pass",
            "from app.db.base_class import Base  # 统一的 Base",
            model_content_raw
        )

        # 3. 生成 Schema 和 Router
        typer.echo(f"[3/5] 自动生成 Pydantic Schemas...")
        schema_code = generate_schema_code(parsed_info['class_name'], parsed_info['primary_key'], parsed_info['fields'])
        typer.echo(f"[4/5] 自动生成路由文件...")
        router_code = generate_router_code(entity_name, parsed_info['class_name'], parsed_info['primary_key'])

        # 5. 写入文件（核心逻辑变更）
        typer.echo(f"[5/5] 更新项目文件...")

        # ⭐ 4. 写入到独立的模型文件中
        models_dir = project_root / "models"
        models_dir.mkdir(exist_ok=True)
        model_target_path = models_dir / f"{entity_name}.py"
        model_target_path.write_text(model_content_final, encoding='utf-8')
        typer.echo(f"  -> 已创建独立模型文件: {model_target_path}")

        # ⭐ 5. 更新 models/__init__.py 以导出新模型
        models_init_path = models_dir / "__init__.py"
        new_export = f"from .{entity_name} import {parsed_info['class_name']}"
        if not models_init_path.exists() or new_export not in models_init_path.read_text(encoding='utf-8'):
            with open(models_init_path, "a", encoding='utf-8') as f:
                f.write(f"{new_export}\n")
            typer.echo(f"  -> 已在 models/__init__.py 中导出 {parsed_info['class_name']}")

        # 追加 Schema (路径可能需要根据您的项目调整)
        schemas_path = project_root / "schemas.py"
        with open(schemas_path, "a", encoding='utf-8') as f:
            f.write(f"\n\n{schema_code}")
        typer.echo(f"  -> 已将 Schema 追加到 {schemas_path}")

        # 创建路由文件 (保持不变)
        route_prefix = f"{entity_name}s"
        route_target_path = project_root / "routes" / f"{route_prefix}.py"
        route_target_path.parent.mkdir(exist_ok=True)
        route_target_path.write_text(router_code, encoding='utf-8')
        typer.echo(f"  -> 已创建路由文件: {route_target_path}")

        # 注册路由 (保持不变)
        api_router_path = project_root / 'api.py'
        # ... (这部分逻辑保持不变)
        api_router_content = api_router_path.read_text(encoding='utf-8')
        new_import = f"from routes.{route_prefix} import router as {route_prefix}_router"
        if new_import not in api_router_content:
            new_inclusion = dedent(f"""
                # --- (自动生成) 注册 {route_prefix} 路由 ---
                api_router.include_router({route_prefix}_router)
            """)
            api_router_content += f"\n{new_import}\n{new_inclusion}\n"
            api_router_path.write_text(api_router_content, encoding='utf-8')
            typer.echo(f"  -> 已将新路由自动注册到 api.py")

        typer.secho(f"\n✨ 自动化流程全部完成！ ✨", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"请重启您的 FastAPI 服务器。")

    except (FileNotFoundError, ValueError, RuntimeError) as e:
        typer.secho(f"\n❌ 自动化流程失败: {e}", fg=typer.colors.RED)
    except Exception as e:
        typer.secho(f"\n❌ 发生未知错误: {e}", fg=typer.colors.RED)
    finally:
        if temp_model_file.exists():
            temp_model_file.unlink()


if __name__ == "__main__":
    cli_app()