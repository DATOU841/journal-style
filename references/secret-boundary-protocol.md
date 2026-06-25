# Secret Boundary 协议

## 定位

本协议防止期刊画像与检索入库协作时把 key/token/cookie 写入进程参数、日志、evidence、handoff 或 Git。

## 规则

- 不得使用 `--api-key=<value>` 或等价命令行参数传递密钥。
- 密钥只能通过受控环境变量或服务器 secret 文件加载。
- evidence 只记录 secret 的存在性、用途、权限和路径，不记录值。
- `journal-style` 不读取、不导出、不解析 Zotero DB、浏览器 profile、cookie、token、RAG chunk、vector dump、`full.md` 正文或带签名的 `full_zip_url`。
- `full_md_path` 只可作为相对指针，不可据此打开正文。

## Gate

`secret-boundary` gate 必须扫描命令文本或 evidence 文本。发现 key/token/cookie 风险时判定 `NO_GO`，并要求人工 review 后才能恢复执行。
