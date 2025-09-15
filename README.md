# **企业级 FastAPI 项目脚手架 (Enterprise FastAPI Scaffold)**

这是一个功能完备、高度可扩展的企业级 FastAPI 项目模板。它集成了现代 Python Web 开发中的各项最佳实践，旨在为新项目的快速启动提供一个坚实、可靠的基础，让开发者可以更专注于业务逻辑的实现。

## **✨ 核心特性**

本脚手架的核心设计哲学是**模块化、高内聚、低耦合**，并内置了以下企业级特性：

* **现代化技术栈**: 基于 FastAPI, Pydantic V2, SQLAlchemy 2.0 (Async) 构建，保证高性能和优秀的开发体验。  
* **统一的路由接口**: 所有 CRUD 操作均遵循 POST /\<资源\>/actions 模式，接口规范高度统一，便于客户端调用。  
* **分层的异常处理**: 集中管理的 错误码 \-\> 自定义异常 \-\> 全局异常处理器，实现业务异常和未知错误的优雅、分层处理。  
* **上下文感知日志**: 利用 contextvars 自动为每条日志注入 request\_id 和 user\_id，完美支持分布式系统下的链路追踪。日志按用途和级别分离到不同文件 (info.log, error.log, api\_traffic.log)。  
* **异步 CRUD 抽象层**: LoggingFastCRUD 封装了通用的数据库操作，并自动处理日志、缓存失效和数据库错误翻译，业务代码更专注于逻辑本身。  
* **专业的测试套件**: 使用 pytest 和 Starlette TestClient，为 API 提供稳定、可靠的自动化集成测试，并使用独立的内存数据库保证测试的纯净与高速。  
* **灵活的配置管理**: 通过 pydantic-settings 和 .env 文件实现配置与代码的完全分离，轻松适配开发、测试、生产等多种环境。  
* **应用生命周期管理**: 使用 lifespan 管理器优雅地处理数据库、Redis 连接池等资源的初始化与释放，并包含后台定时任务的最佳实践。  
* **自动化代码生成**: 内置 Node.js 脚本，可通过命令行交互式地为新数据表快速生成全套符合项目规范的路由接口代码。

## **📂 项目结构**

.  
├── app/                  \# 核心应用代码  
│   ├── api.py            \# API 路由聚合器  
│   ├── core/             \# 核心模块 (配置, 日志, CRUD基类)  
│   ├── db/               \# 数据库 (会话, 缓存)  
│   ├── exceptions/       \# 自定义异常和错误码  
│   ├── middleware/       \# 中间件  
│   ├── routes/           \# 业务路由模块 (items.py, users.py)  
│   ├── lifespan.py       \# 应用生命周期管理  
│   └── main.py           \# FastAPI 应用主入口  
├── scripts/              \# 存放各类脚本  
│   └── generate\_route.js \# 路由生成器脚本  
├── tests/                \# 自动化测试  
│   ├── conftest.py       \# Pytest 配置文件 (Fixtures)  
│   └── test\_users\_api.py \# 具体的测试用例  
├── \_templates/           \# 代码生成器模板  
│   └── route.ejs  
├── .env                  \# (需手动创建) 环境变量配置文件  
├── .env.example          \# 环境变量示例文件  
├── .gitignore  
├── package.json          \# Node.js 依赖配置  
├── pyproject.toml        \# Python 项目打包与依赖配置  
└── README.md

## **🚀 快速开始**

请按照以下步骤在您的本地环境中设置并运行本项目。

### **1\. 环境准备**

* 确保您已安装 Python 3.9+ 和 Node.js 16+。  
* 克隆本项目到本地:  
  git clone \<your-repository-url\>  
  cd \<your-project-directory\>

### **2\. 安装依赖**

* **创建并激活 Python 虚拟环境**:  
  python \-m venv .venv  
  \# Windows  
  .\\.venv\\Scripts\\activate  
  \# macOS/Linux  
  source .venv/bin/activate

* 安装 Python 依赖:  
  (本项目使用 pyproject.toml 管理依赖。如果您需要生成 requirements.txt，可以运行 pip freeze \> requirements.txt)  
  pip install \-e .

  *(使用 \-e . 可编辑模式安装，方便开发)*  
* **安装 Node.js 开发依赖**:  
  npm install

### **3\. 配置**

* 项目配置由 .env 文件管理。请将项目根目录下的 .env.example 文件复制一份并重命名为 .env：  
  \# Windows  
  copy .env.example .env  
  \# macOS/Linux  
  cp .env.example .env

* 根据您的本地环境，修改 .env 文件中的配置，特别是 DATABASE\_URL，指向您的 MySQL 数据库。

### **4\. 运行应用**

\# 推荐使用 uvicorn 运行，它支持热重载  
uvicorn app.main:app \--reload

服务启动后，您可以在浏览器中访问 http://127.0.0.1:8000 查看欢迎信息，或访问 http://127.0.0.1:8000/docs 查看交互式 API 文档。

### **5\. 运行测试**

pytest \-v \-s

## **🤖 代码生成器**

当您需要为新的数据表（例如 products）创建一套标准的路由接口时，可以使用内置的代码生成器。

1. **前提**: 确保已在 models.py 和 schemas.py 中定义了新表对应的模型和 Schema。  
2. **运行命令**:  
   npm run generate:route

3. 根据命令行提示，依次输入**实体名称**、**主键字段名**和**路由前缀**。  
4. 脚本会自动在 app/routes/ 目录下生成新的路由文件，并提示您如何在 app/api.py 中注册它。

## **🔌 API 接口约定**

* **端点**: POST /\<资源复数名称\>/actions (例如: /users/actions, /items/actions)  
* **请求体**:  
  {  
      "action": "操作名称",  
      "payload": {  
          "参数": "值"  
      }  
  }  
