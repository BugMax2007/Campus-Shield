# Hugging Face 模型接入说明

本项目现在有两条 HF 相关路线：

1. `路线分类模型`
   - 训练数据：`/Users/haihaihai/Code/CASproject/data/hf/route_advisor_train.jsonl`
   - 脚本：`/Users/haihaihai/Code/CASproject/tools/hf_train_route_advisor.py`
   - 目标：把当前局面分类到 `map_and_plan / collect_clues / relocate_safe / take_gate_now / distract_guard / relocate_to_secret / take_secret_now / hold_for_police / steady`

2. `机器人提示生成模型`
   - 训练数据：`/Users/haihaihai/Code/CASproject/data/hf/robot_coach_sft.jsonl`
   - 脚本：`/Users/haihaihai/Code/CASproject/tools/hf_train_robot_coach.py`
   - 目标：根据当前楼层、风险、线索和角色类型生成短句提示

## 本地游戏如何使用

- 游戏内的 `CampusAdvisor` 已经接入。
- 默认使用本地策略模型 fallback。
- 当你安装可选依赖并设置 `CAMPUS_SAFE_ENABLE_HF=1` 时，游戏会尝试启用 Hugging Face zero-shot 路线分类后端。

## 安装可选依赖

```bash
cd /Users/haihaihai/Code/CASproject
python3 -m pip install -e ".[hf]"
```

## 训练示例

路线分类：

```bash
cd /Users/haihaihai/Code/CASproject
uv run tools/hf_train_route_advisor.py
```

机器人提示生成：

```bash
cd /Users/haihaihai/Code/CASproject
uv run tools/hf_train_robot_coach.py
```

## 当前接入边界

- 现阶段的 HF 后端只接入了路线决策分类。
- 机器人提示生成模型的训练脚本和数据已经就位，但游戏内默认仍使用模板化输出。
- 这样做是为了保证没有 HF 依赖时，游戏仍然可运行。
