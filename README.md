```
ai_evaluation_backend/
│── ai_evaluation/       # Django 项目主目录
│   ├── settings.py      # 配置文件
│   ├── urls.py          # URL 路由
│   ├── wsgi.py          # WSGI 入口
│── core/                # 核心模块（AI 交互、工具）
│   ├── one_api_client.py  # One API 请求封装
│   ├── prompt_templates.py # Prompt 模板
│   ├── utils.py          # 通用工具
│── question_bank/        # 题库管理
│   ├── models.py         # 题库模型
│   ├── views.py          # 题库 API 视图
│   ├── urls.py           # 题库路由
│── model_testing/        # 测试管理
│   ├── models.py         # 测试记录模型
│   ├── views.py          # 测试 API 视图
│   ├── urls.py           # 测试路由
│── model_evaluation/     # 评估模块（预留）
│   ├── models.py         
│   ├── views.py          
│   ├── urls.py           
│── report_generation/    # 报告生成（预留）
│   ├── models.py         
│   ├── views.py          
│   ├── urls.py           
│── api/                 # 统一 API 接口
│   ├── urls.py           # 统一路由
│── manage.py            # Django 管理脚本
│── requirements.txt      # 依赖文件
```

