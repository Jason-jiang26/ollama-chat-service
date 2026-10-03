# 理解这个项目

先运行，再阅读代码，再做一次小修改并测试。能独立定位错误、说明改动原因，比背熟技术名称更能证明你理解项目。

## 必须理解的概念

| 概念 | 在本项目中的位置 | 你应该能回答的问题 |
| --- | --- | --- |
| Ollama 与模型 | 本机 11434 端口与 gemma3:270m | Ollama 是什么？模型参数量与模型文件大小有什么区别？ |
| Python 环境 | `.venv`、依赖清单 | 为什么不把所有依赖装进 conda base？如何复现环境？ |
| HTTP / JSON | `/health`、`/ready`、`/chat` | GET 与 POST 有什么区别？请求体和响应体是什么？ |
| FastAPI | `create_app` 与三个路由 | 浏览器的 `/docs` 是怎样生成的？FastAPI 与 Ollama 分别在哪个端口？ |
| Pydantic | `ChatRequest`、`ChatReply` | 空消息、数字和超长消息如何被拦截？422 代表什么？ |
| Ollama API | `OllamaBackend.chat` | `model`、`messages`、`stream` 分别控制什么？ |
| 异步与超时 | `async def`、`await`、`asyncio.wait_for` | 等待模型时为什么使用异步？超时后怎样返回？ |
| 健康与就绪 | `/health` 与 `/ready` | FastAPI 正常时，模型服务可以仍然不可用吗？ |
| 测试 | `test_api.py` 与 `smoke_test.py` | 模拟测试和真实模型测试分别能证明什么？ |
| Git / GitHub | `.gitignore`、提交、推送 | 什么是本地提交？推送到哪个远端？为什么不上传 `.venv`？ |

## 按顺序读 main.py

1. `Settings`：默认连接本机 Ollama，模型名由服务端配置；环境变量用于修改设置。
2. `ChatRequest`：约束客户端输入，只接受 `message`，首尾去空白后长度为 1–4000。
3. `OllamaBackend._request`：发送 HTTP 请求，并将连接错误、超时和异常响应转成明确的 HTTP 状态。
4. `OllamaBackend.ready`：查询安装的模型，检查配置的模型名称是否存在。
5. `OllamaBackend.chat`：组织 `messages`，调用 `/api/chat`，解析并验证文本回复。
6. `lifespan`：应用启动时建立共享 HTTP 客户端，退出时释放连接。
7. 三个路由：将用户请求交给相应逻辑，返回有定义的 JSON 结构。

## 做一次你自己的修改

例如把最大消息长度从 4000 改成 2000：先修改 `MessageText` 中的限制，再更新测试中的超长消息长度和 README，然后运行测试。尝试发送 2000 与 2001 字符，观察边界。这能帮助你理解“修改—验证—提交”的完整过程。

也可以调整输出 token 上限，记录生成时长与回复是否被截断。不要把一次测试的结果推广成模型质量或性能结论。

## 截图中其他技术与本项目的关系

- **UI / API / LLM 三层**：UI 接收输入并展示结果；FastAPI 组织与校验请求；Ollama 运行模型。当前客户端是 Swagger `/docs` 或测试脚本，尚未开发 Tkinter UI。
- **Prompt**：是发送给模型的指令、问题与上下文。表达清楚任务和输出格式，有助于控制结果；无法保证模型一定遵守或算对。
- **Tkinter**：Python 桌面界面库。若后续实现，界面应调用 `/chat`，并通过后台任务防止等待模型时界面冻结。
- **VirtualBox / Ubuntu**：属于另一种运行环境。当前项目在 Windows 原生运行，不能由此推断已经完成 Ubuntu 虚拟机部署。
- **conda / venv**：都能隔离 Python 环境。本项目以 `venv` 保存项目依赖，你的系统也已有 Anaconda。
- **自然语言 AI 计算器**：还需要将自然语言转换成受限表达式或工具请求，再由确定性计算逻辑求值，校验输入与结果。禁止直接 `eval` 用户或模型生成的字符串。
- **Agent**：需要工具选择与执行、任务状态和失败处理等机制。单次 `/chat` 调用不能证明已经实现这些功能。

## 面试中的简短讲解

“这是一个本地大模型对话 API。客户端向 FastAPI 的 `/chat` 发 JSON，Pydantic 先校验输入，应用通过 Ollama HTTP API 调用本地模型，再将回复封装成 JSON 返回。我区分了进程健康与模型就绪，处理了连接失败和超时，并分别测试了模拟错误场景和真实模型调用。”

请用自己的话讲解，并在阅读与修改代码后再使用这一表述。若使用 AI 辅助完成开发，应如实说明自己的实现、调试与理解工作。
