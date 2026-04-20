# Render 部署步骤（Flask + SQLite）

## 1. 推送代码到 GitHub

确保以下文件已在仓库中：

- `app.py`
- `requirements.txt`
- `Procfile`
- `render.yaml`
- `schema.sql`
- `seed.sql`
- `templates/`
- `static/`

## 2. 在 Render 创建服务

1. 登录 Render
2. 点击 `New +` -> `Blueprint`
3. 连接 GitHub 仓库并选择本项目
4. Render 会自动识别 `render.yaml`
5. 确认后点击 `Apply`

部署完成后即可获得公网地址（类似 `https://xxx.onrender.com`）。

## 3. 首次访问检查

- 打开首页是否正常显示
- 进入登录页，验证演示账号可登录
- 在查询页测试筛选是否正常

## 4. SQLite 说明（作业答辩可用）

- 当前方案适合课程作业演示
- 数据库文件位于服务实例本地磁盘
- 服务重建/迁移后，数据库可能重置
- 生产环境建议迁移到 PostgreSQL
