# 验证记录

验证日期：2026-10-03、2026-10-04（北京时间）。

## 环境

- Windows / Python 3.13.9。
- Ollama 0.35.1，模型 `gemma3:270m`。
- 本地模型文件已下载；Ollama 服务使用 `D:\Ollama\models`。
- 主要依赖版本见 `requirements.txt`，验证环境的相关依赖快照见 `requirements-lock.txt`。

## 离线接口测试

命令：`python -m pytest -q`。

结果：**21 passed**。

包括中文消息的发送与返回、空白/超长/非字符串输入的拒绝、模型存在与缺失检查、连接失败、超时、上游 HTTP 错误、非 JSON/空白/格式错误回复。模型 HTTP 响应由 `httpx.MockTransport` 模拟，因此这些测试可以在没有 GPU 与 Ollama 的环境中运行。

## 真实模型调用

命令：`python scripts/smoke_test.py`。

实际观察结果：

```text
GET /health: HTTP 200
GET /ready: HTTP 200
POST /chat: HTTP 200
```

实际请求与返回：

```json
{
  "request": "你好，请用一句中文介绍自己。",
  "response": {
    "model": "gemma3:270m",
    "reply": "你好！我是一个大型语言模型，由 Google 训练。"
  },
  "elapsed_seconds": 36.728
}
```

此用例验证了客户端 → FastAPI → Ollama → 本地模型 → JSON 回复的链路。耗时是这一次请求的观察值，可能包含模型加载与设备调度，不是稳定性能指标。没有据此测量回答准确率，也没有验证多轮对话、语音、工具调用或 Agent。

## 环境复现说明（2026-10-03）

这次验证使用本机已有的 Python 环境，并在临时工作目录加载缺少的纯 Python 依赖源码，没有更改 Anaconda base 中的已安装包。独立的 `.venv` 应按 README 在 D 盘创建后再次执行测试。模型和源码不需要放在同一个目录。

## 2026-10-04 本地验证

- 已在 `D:\Projects\ollama-chat-service` 创建独立 `.venv`，使用 Python 3.13.9。
- 新增 GET /info 接口及测试，并新增 GET /chat 返回 405 的测试。
- 命令：`.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider`。
- 自动测试结果：23 passed、1 warning，耗时 1.13 秒（开发者本机运行记录）。
- 警告来自 Starlette TestClient 对 AnyIO 已弃用别名的引用，测试断言通过；关闭 pytest 缓存避免了本机缓存目录的权限警告。
- 真实调用：/health 和 /ready 均返回 HTTP 200。
- 输入：5加5等于多少？请只回答数字。
- gemma3:270m 返回：5。
- 本次聊天请求耗时：0.912 秒。
- 结论：服务调用流程正常，但本次算术答案错误。
  当前自动测试和 smoke test 不评价模型答案的正确性。

上述耗时为单次调用观察值，不代表稳定性能。该算术用例的期望答案为 `10`，实际回答为 `5`；它记录了一个失败案例，没有据此估算整体准确率。
