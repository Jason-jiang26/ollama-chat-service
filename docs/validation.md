# 验证记录

验证日期：2026-10-03（北京时间）。

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

## 环境复现说明

这次验证使用本机已有的 Python 环境，并在临时工作目录加载缺少的纯 Python 依赖源码，没有更改 Anaconda base 中的已安装包。独立的 `.venv` 应按 README 在 D 盘创建后再次执行测试。模型和源码不需要放在同一个目录。
