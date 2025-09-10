# **FastAPI 企业级应用脚手架**

这是一个功能齐全、生产就绪的 FastAPI 企业级应用脚手架。它集成了异步数据库操作、Redis缓存、统一的响应报文规范、分层日志系统、全局异常处理和动态分页等最佳实践，旨在帮助开发者快速启动一个健壮、可扩展、易于维护的后端项目。

## **✨ 核心功能**

* **完全异步**: 基于 async/await，使用 SQLAlchemy 2.0 和 asyncpg 实现全异步数据库操作。  
* **企业级分层**: 清晰的项目结构 (/core, /routes, /schemas, /models)，实现业务逻辑、数据模型和API接口的完全解耦。  
* **统一报文规范**: 内置标准的成功 (StandardResponse) 和失败 (ErrorResponse) 响应模型，所有API返回统一的JSON结构。  
* **强大的CRUD工具**: 基于 fastcrud 进行了二次封装 (LoggingFastCRUD)，自动处理日志记录和缓存失效。  
* **动态分页**: “获取列表”接口自动计算并返回完整的分页元数据 (total\_items, total\_pages 等)，极大地方便了前端开发。  
* **多层日志系统**:  
  * api\_traffic.log: 记录所有API请求的流量、耗时和状态码。  
  * user\_activity.log: 记录详细的业务逻辑执行步骤。  
  * error.log: 专门记录所有可预见的业务异常和未捕获的系统错误。  
* **全局异常处理**: 优雅地捕获所有业务异常和服务器内部错误，防止敏感信息泄露，并返回统一格式的错误响应。  
* **旁路缓存策略**: 对“读”操作集成了 Redis 缓存，对“写”操作（增、删、改）自动实现缓存失效，提升性能。  
* **后台任务**: 使用 FastAPI 的 lifespan 事件和 asyncio 来管理后台任务（如：定时日志清理）。  
* **配置管理**: 使用 .env 文件来管理环境变量，保护敏感信息。

## **🛠️ 技术栈**

* **Web 框架**: [FastAPI](https://fastapi.tiangolo.com/)  
* **数据库 ORM**: [SQLAlchemy 2.0 (Async)](https://www.sqlalchemy.org/)  
* **数据校验**: [Pydantic V2](https://docs.pydantic.dev/latest/)  
* **数据库驱动**: [asyncpg](https://github.com/MagicStack/asyncpg) (for PostgreSQL)  
* **缓存**: [Redis](https://redis.io/)  
* **服务器**: [Uvicorn](https://www.uvicorn.org/)

## **🚀 快速上手**

请按照以下步骤在本地运行此项目。

### **1\. 先决条件**

* Python 3.11+  
* PostgreSQL 数据库  
* Redis 服务器

### **2\. 克隆项目**

git clone \<你的仓库URL\>  
cd \<项目目录\>

### **3\. 创建并激活虚拟环境**

\# 创建虚拟环境  
python \-m venv .venv

\# 激活虚拟环境 (Windows)  
.venv\\Scripts\\activate

\# 激活虚拟环境 (macOS/Linux)  
source .venv/bin/activate

### **4\. 安装依赖**

项目的所有依赖都记录在 requirements.txt 文件中。

pip install \-r requirements.txt

### **5\. 配置环境变量**

项目中包含一个 .env.example 文件，作为环境配置的模板。

1. 复制模板文件：  
   \# (Windows)  
   copy .env.example .env

   \# (macOS/Linux)  
   cp .env.example .env

2. **编辑 .env 文件**：打开你刚刚创建的 .env 文件，填入你本地的数据库连接信息和 Redis 地址。  
   \# .env  
   DATABASE\_URL=postgresql+asyncpg://YOUR\_USER:YOUR\_PASSWORD@localhost:5432/YOUR\_DB\_NAME  
   REDIS\_HOST=localhost  
   REDIS\_PORT=6379

### **6\. 运行应用**

一切准备就绪！现在，启动服务器：

python run.py

你应该能看到类似以下的输出，表明服务器已成功启动：

\--- Starting FastAPI Server with Uvicorn (Fixed) \---  
...  
INFO:     Uvicorn running on \[http://0.0.0.0:8000\](http://0.0.0.0:8000) (Press CTRL+C to quit)

## **📚 API 文档**

项目启动后，FastAPI 会自动为你生成交互式的 API 文档。

* **Swagger UI**: [http://127.0.0.1:8000/docs](https://www.google.com/search?q=http://127.0.0.1:8000/docs)  
* **ReDoc**: [http://127.0.0.1:8000/redoc](https://www.google.com/search?q=http://127.0.0.1:8000/redoc)

你可以在这些页面上直接浏览和测试所有的API端点。

## **🏗️ 如何添加新模块**

假设你需要添加一个新的 products 模块。

(可以通过sqlacodegen指令快速生成已经存在的表格结构，放在models.py里)
1. **创建模型**: 在 models.py 中定义 Products SQLAlchemy 模型。  
2. **创建 Schema**: 在 schemas.py 中定义 ProductCreate, ProductUpdate, ProductRead 等 Pydantic 模型。  
3. **创建路由文件**:  
   * 在 app/routes/ 目录下创建一个新文件 products.py。  
   * 参考 app/routes/items.py 的结构，创建一个新的 APIRouter 和 LoggingFastCRUD 实例。  
   * 实现你的 products API 端点。  
4. **注册新路由**:  
   * 打开 **app/api.py** 文件。  
   * 导入并注册你刚刚创建的 products 路由：  
     \# app/api.py  
     from app.routes.users import router as users\_router  
     from app.routes.items import router as items\_router  
     from app.routes.products import router as products\_router \# \<-- 1\. 导入

     api\_router \= APIRouter()

     api\_router.include\_router(users\_router, prefix="/users", tags=\["Users"\])  
     api\_router.include\_router(items\_router, prefix="/items", tags=\["Items"\])  
     api\_router.include\_router(products\_router, prefix="/products", tags=\["Products"\]) \# \<-- 2\. 注册

重启应用，新的 /products API 就已经生效了！

## **📜 许可证**

本项目采用 [MIT License](https://www.google.com/search?q=LICENSE) 授权。