# RAG 嵌入模型选型建议

阶段 B 默认部署方式：Ollama 容器提供 embedding API，后端通过 `OLLAMA_BASE_URL` 调用，Chroma 容器保存向量。

## 推荐默认模型

### 1. `BAAI/bge-m3`

- Hugging Face：`https://hf.co/BAAI/bge-m3`
- Ollama 模型名：`bge-m3`
- 适用：中文/英文/多语言 RAG、长短文本混合检索、比赛演示默认方案。
- 优点：下载量高、开源、中文表现稳，Ollama 可直接拉取。
- 当前项目默认值：`OLLAMA_EMBEDDING_MODEL=bge-m3`

## 备选模型

### 2. `intfloat/multilingual-e5-large`

- Hugging Face：`https://hf.co/intfloat/multilingual-e5-large`
- 适用：多语言检索，语义检索质量较稳。
- 注意：E5 系列通常需要 query/passsage 前缀；如果后续切换，需要在 embedding 客户端里加前缀策略。

### 3. `mixedbread-ai/mxbai-embed-large-v1`

- Hugging Face：`https://hf.co/mixedbread-ai/mxbai-embed-large-v1`
- 适用：英文检索、通用语义搜索。
- 注意：中文场景不是首选；更适合英文文档或混合英文技术资料。

## 当前建议

第一版选择 `BAAI/bge-m3`。

原因：

- 项目文档和评测场景以中文为主。
- RAG 污染、敏感文档、提示注入样例需要中文语义检索。
- Ollama 部署简单，一键启动时可自动 `ollama pull bge-m3`。
- 后续如需要更精细对比，可在同一批 RAG case 上比较污染召回率、正常文档召回率和敏感文档误召回率。
