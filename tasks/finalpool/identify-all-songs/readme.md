### 1. Sometimes the agent does not perform well in recognizing songs. Out of 20 songs, it may only recognize about 10.
### 2. Some songs contain special symbols or are different versions, which makes ground truth evaluation less precise. We may need to relax the matching criteria somewhat.
For example, ground truth:

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
Agent return:
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
Ground truth modified by wenshuo:

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

### 3. Since the video description actually contains the full list of music titles in order, we checked whether the agent is able to extract information from a video's webpage description. In reality, LLM-based agents (such as GPT-5, Claude-4, etc.) cannot expand and read YouTube descriptions on their own, so most of this content cannot be obtained by the agent. Therefore, the difficulty of this task is not significantly reduced.