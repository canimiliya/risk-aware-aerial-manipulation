# S4-R0 名义动力学闭环报告

## 结论

S4-R0 的 route-B 名义动力学闭环证据已准备提交独立复核。`hover_hold` 3 次、`initial_offset_recovery` 4 次、`arm_motion_hold` 3 次和 reaction-off 对照共 11 次 headless 240 Hz 运行完成；真实 Isaac GUI 产生了 315 个原始时序帧，经整理形成 12 张 PNG、3 段本地 GIF 和 3 张曲线图。

## 自动结果

权威 summary：`docs/evidence/S4-R0/summary/s4_r0_metrics.json`。悬停位置 RMSE 约 0.0015 m、最大误差约 0.0059 m；偏差恢复四组最大误差不超过 0.10 m，settling time 为 0–0.75 s；机械臂运动位置 RMSE 约 0.0066 m、活动关节 RMSE 约 0.0100 rad、末端 FK RMSE 约 0.0069 m。重力下落探针证明未施加悬停 wrench 时 z 下降且末速度为负。所有 post-reset root/joint write audit 计数为 0。

## 诚实限制

这是 `BASE_DYNAMIC_ARM_REACTION_SURROGATE_V1`，不是完整闭链动力学；visual manifest 中的视频是实际 Isaac GUI viewport 的本地时序 GIF，不提交大视频到 Git。S4-R1 的整条名义轨迹闭环尚未开始；风、接触、学习和 S5 保持冻结。
