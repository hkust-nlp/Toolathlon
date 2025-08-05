### 1.agent识别歌曲有时候比较烂，一共20首歌只识别出10首
### 2.有些歌曲带一些特殊符号/不同版本，用groundtruth evaluate说实话有点不准，可能要放宽一点条件
比如groundtruth：

```yaml
- Song1: Sweet But Psycho
- Song2: abcdefu (chill) visualizer
- Song3: At My Worst
- Song4: "10:35"
- Song5: Hymn For The Weekend
- Song6: Thats What I Like
- Song7: CUPID
- Song8: UNHEALTHY
- Song9: Nothing On You
- Song10: Talking To The Moon
- Song11: Im A Mess
- Song12: INFERNO
- Song13: FRIENDS
- Song14: Let Me Down Slowly
- Song15: Ride
- Song16: Fly Me to the Moon
- Song17: Symphony
- Song18: Let It Be Me
- Song19: Stressed Out
- Song20: Prayer In C
```
agent_Return:
```yaml
- Song1: Sweet but Psycho
- Song2: abcdefu
- Song3: At My Worst
- Song4: 10:35
- Song5: Angels
- Song6: That's What I Like
- Song7: Cupid
- Song8: Unhealthy
- Song9: Nothing on You
- Song10: Talking to the Moon
- Song11: good 4 u
- Song12: Hell Is Hot
- Song13: F.R.I.E.N.D.S
- Song14: Let Me Down Slowly
- Song15: Ride
- Song16: Fly Me to the Moon
- Song17: Symphony
- Song18: Let It Be Me
- Song19: Stressed Out
- Song20: Forgive You
```
gt modified by wenshuo

```yaml
- Song1: Sweet but Psycho
- Song2: abcdefu
- Song3: At My Worst
- Song4: 10:35
- Song5: Hymn For the Weekend
- Song6: That's What I Like
- Song7: CUPID
- Song8: UNHEALTHY
- Song9: Nothing On You
- Song10: Talking To The Moon
- Song11: Im A Mess
- Song12: INFERNO
- Song13: FRIENDS
- Song14: Let Me Down Slowly
- Song15: Ride
- Song16: Fly Me to the Moon
- Song17: Symphony
- Song18: Let It Be Me
- Song19: Stressed Out
- Song20: Prayer In C
```