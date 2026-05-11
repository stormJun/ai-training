# 可观测性与 Serving Runtime 专题

本父目录合并了原来的 `44_elk_observability/`、`45_prometheus_ollama_exporter/`、`46_ray_serve_streaming/` 和 `59_ttft_and_llm_serving_latency/`，目的是减少仓库顶层目录数量，并把可观测性、流式服务与时延分析资料放到同一专题下。

## 子目录

- `44_elk_observability/`
  - ELK 观测与日志
- `45_prometheus_ollama_exporter/`
  - Prometheus 与 Ollama Exporter
- `46_ray_serve_streaming/`
  - Ray Serve 与流式服务
- `59_ttft_and_llm_serving_latency/`
  - TTFT、首 token 延迟与 LLM 推理时延资料整理

## 建议学习顺序

1. 先看 `44_elk_observability/`
2. 再看 `45_prometheus_ollama_exporter/`
3. 然后查看 `46_ray_serve_streaming/`
4. 最后阅读 `59_ttft_and_llm_serving_latency/`

## 说明

- 该父目录只做聚合，不拆分各子主题内部结构。
- 子目录里的命令默认以仓库根目录或各自子目录为起点，具体以子目录 README 为准。
