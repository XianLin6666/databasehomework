# 数据库大作业实现（Flask + SQLite）

校园二手交易平台数据库系统。  
本项目包含：数据库建模、约束与触发器、事务购买流程、权限控制、查询可视化、无刷新筛选和自动化测试。

## 1. 快速运行（Windows PowerShell）

```powershell
cd d:\code\databasehomework
.\.venv\Scripts\Activate.ps1
python -m flask --app app run
```

访问：`http://127.0.0.1:5000`

## 2. 首次初始化（或环境损坏时）

```powershell
cd d:\code\databasehomework
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

首次运行如果数据库不存在，执行一次：

```powershell
python app.py
```

后续日常开发用 `flask run` 即可。

## 3. 在线部署（Render）

项目已包含部署文件：`Procfile`、`render.yaml`。  
可按 [DEPLOY_RENDER.md](./DEPLOY_RENDER.md) 直接部署并获得公网访问地址。

## 4. 项目亮点（可用于答辩）

- 三表建模：`user`、`item`、`orders`
- 数据一致性：主键/外键/唯一约束/`CHECK` + 触发器
- 事务安全：购买流程使用 `BEGIN IMMEDIATE`，防并发重复下单
- 权限控制：`viewer` 只读，`admin` 才能写（增改删购、重建数据库）
- 查询展示：基本查询、连接查询、聚合分组、视图查询
- 前端交互：查询筛选支持局部异步刷新（不整页重载）
- 工程质量：`unittest` 覆盖关键业务规则

## 5. 页面与功能

- 首页：系统统计 + 管理员重建数据库入口
- 用户列表：查看 `user` 表
- 商品列表：查看 `item`，并执行新增/改价/删除未售/购买（仅管理员）
- 订单列表：查看订单详情
- 查询展示：多类 SQL 查询 + Chart.js 图表 + 无刷新筛选

## 6. 安全与并发策略

- 应用层：路由写操作统一校验管理员身份
- SQL 层：参数化查询，避免注入
- 数据库层：
  - `orders.item_id UNIQUE` 限制同商品只成交一次
  - 触发器阻止非法购买（商品不存在、已售、买自己商品）
  - 触发器自动将成交商品置为已售
  - 触发器禁止删除已成交商品、禁止把已成交状态改回未售

## 7. 演示账号

- 管理员：`admin / admin123`
- 普通用户：`viewer / viewer123`

## 8. 测试与依赖

运行测试：

```powershell
python -m unittest discover -s tests -v
```

依赖文件说明：

- `requirements.txt`：项目标准依赖
- `requirements.lock.txt`：当前环境锁定依赖快照

安装新包后可更新锁定文件：

```powershell
pip freeze > requirements.lock.txt
```

## 9. 常见问题

- 激活虚拟环境被拦截（PowerShell 策略）：
  ```powershell
  Set-ExecutionPolicy -Scope Process Bypass
  .\.venv\Scripts\Activate.ps1
  ```
- `ModuleNotFoundError: flask`：确认已激活 `.venv` 后执行 `pip install -r requirements.txt`

## 10. 目录结构

- `app.py`：Flask 主程序（路由、权限、业务逻辑）
- `schema.sql`：表结构、约束、触发器、视图
- `seed.sql`：初始数据
- `templates/`：页面模板
- `static/style.css`：样式
- `tests/test_app.py`：自动化测试
- `项目说明.md`：课程提交说明
