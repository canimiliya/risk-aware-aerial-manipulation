# write 与 grasp/lift 的官方任务复杂度对比

本文件只读取官方配置和已保存运行日志，不修改配置。

|任务|中间点|JPS段|走廊段|起点|终点|TotalT|QdIntervals|Rho|MultiLayerOpt|OptRelTol1|OptRelTol2|
|---|---:|---:|---:|---|---|---:|---:|---:|---|---:|---:|
|grasp|0|2|1|[-3.0, 0.0, 1.2]|[3.0, 0, 1.2]|20|96|500|True|0.0001|1e-06|
|lift|1|2|1|[-3.0, 0.0, 1.2]|[1.0, 0.0, 1.5]|20|96|500|True|0.0001|1e-06|
|write|6|7|6|[-3.0, 0.0, 1.5]|[3.0, 0.0, 1.5]|20|96|0.001|False|1e-08|1e-10|

## 结论

write 比 grasp 多 6 个官方中间点、比 lift 多 5 个；它的路径更长，且约束标志分布更密集。write 的 `MultiLayerOpt=False`，但 `OptRelTol1=1e-8`、`OptRelTol2=1e-10` 比 grasp/lift 更严格；其 `Rho=0.001` 也明显更小。JPS 实际段数和走廊段数由运行时日志确定，不能仅从任务点数量推定。

## 约束标志

- `grasp`：{}
- `lift`：{'inter_point_flag_6': 1, 'inter_point_flag_7': 1, 'inter_point_flag_11': 1, 'inter_point_flag_12': 1, 'inter_point_flag_13': 1}
- `write`：{'inter_point_flag_15': 2, 'inter_point_flag_16': 5, 'inter_point_flag_11': 3, 'inter_point_flag_12': 3, 'inter_point_flag_13': 3, 'inter_point_flag_14': 2}
