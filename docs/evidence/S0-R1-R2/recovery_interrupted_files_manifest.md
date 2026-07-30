# S0-R1-R2 中断文件恢复清单

- 仓库外备份目录：`C:\Users\Administrator\AppData\Local\Temp\risk-aware-r2a-recovery-20260731-032837`
- 备份文件数：9；二进制 diff：`working_tree_binary.diff`（13005 bytes）。
- 原始文件 SHA-256、字节数和最后修改时间：`backup_manifest.json` 与 `backup_manifest.txt`。
- 异常原因：中断写入的 `hardware_audit.json` 顶层为 list，检查器按 object 调用 `.get()` 发生异常。
- 探针结果：`collect_s0_hardware.ps1 -OutputDir` 在仓库外成功；新 JSON 顶层为 dict/object。
- 最终处理：已先恢复 9 个工作树文件至 HEAD，再复制仓库外的新鲜、有效采集结果；采集脚本无需修改。
- 最终 `hardware_audit.json` SHA-256 将由提交前自动检查和 Git 证据复核。
