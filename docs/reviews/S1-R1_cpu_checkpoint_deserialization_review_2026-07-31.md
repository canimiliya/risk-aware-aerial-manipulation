# S1-R1 CPU 权重反序列化审查

- 审查 Head：`99c4f1a7a6973927fd85e64a66a8e3fdf8feabb1`
- CPU Torch、权重独立加载和 19/19 构建均通过。
- 旧 grasp 三次在同一加载位置 abort；最小实验确认官方调用把 `{"map_location":"cpu"}` 当作第二个位置参数传入。
- PyTorch 将该位置参数当作 storage-location 映射；CUDA checkpoint 未匹配 `cuda:* -> cpu`，所以继续尝试 CUDA 反序列化。
- 本轮未修改官方源码；使用 CPU 规范化副本和临时文件 bind mount。
- bind mount 退出后已卸载，官方权重哈希恢复且源码工作树干净。
