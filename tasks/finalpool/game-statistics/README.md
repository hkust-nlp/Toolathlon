数据生成方式：

  1. daily_scores_stream表：
    - 200个虚拟玩家
    - 每个玩家3-10场游戏记录
    - 基于技能等级生成真实分数分布
    - 包含online_score和task_score两部分
  2. player_historical_stats表：
    - 过去10天的历史数据
    - 每天100个玩家的统计记录
    - 包含player_id、date、total_score、game_count等字段

该任务的评估分为两个主要检测：

  1. 每日排行榜验证 (verify_daily_leaderboard)

  检测内容：
  - 表名: leaderboard_YYYYMMDD（如leaderboard_20250804）
  - 数据量: 必须包含100条记录
  - 排序: 按total_score降序排列
  - 排名: rank字段必须是连续的1-100

  验证字段：
  - player_id: 玩家ID
  - total_score: 总分数
  - rank: 排名（必须连续1-100）

  2. 历史统计更新验证 (verify_historical_stats_update)

  检测内容：
  - 表名: player_historical_stats
  - 数据一致性: 与daily_scores_stream原始数据对比
  - 聚合准确性: 验证每个玩家的总分和游戏次数

  验证逻辑：
  - 从daily_scores_stream表聚合当日数据：SUM(scores.online_score + scores.task_score)
  - 与player_historical_stats表中的记录逐一比较
  - 检查total_score和game_count字段的准确性

  只验证当天数据：
  -- evaluation/main.py:88-94 只查询当天
  WHERE date = '{today_str}'

  -- evaluation/main.py:118-122 也只查询当天  
  WHERE DATE(timestamp) = '{today_str}'

  每个玩家每天一条记录：
  从 player_historical_stats 表结构可以看出：
  - player_id + date 组成复合主键
  - 每个玩家每天只有一条记录
  - 不同日期的记录是独立的，不会合并

  验证逻辑：
  - 取当天 daily_scores_stream 中每个玩家的所有游戏记录
  - 按 player_id 分组求和得到当天总分
  - 与 player_historical_stats 表中当天的对应记录比较
  - 确保每个玩家当天的总分和游戏次数匹配