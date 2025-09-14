"""
This module contains the RewardMathFn class, which evaluates mathematical answers
and assigns rewards based on their correctness. It utilizes a language model to 
validate answers when necessary.
"""
from typing import List, Union

from deepscaler.globals import THOUGHT_DELIMITER_START, THOUGHT_DELIMITER_END

from deepscaler.rewards import RewardConfig, RewardFn, RewardInput, RewardOutput, RewardType

from math_verify import parse, verify

def labeling_responses(responses: list[str], golden_answer: str):
    predict_answers = list(map(parse, responses))
    golden_answers = list(map(parse, ["$" + golden_answer + "$"] * len(responses)))
    labels = list(map(verify, golden_answers, predict_answers))
    return labels

class RewardMathFn(RewardFn):
    """
    Reward function for evaluating mathematical answers.

    This class implements the __call__ method to process the input and determine
    the reward based on the correctness of the provided answer compared to the ground truth.
    """

    def __call__(self, input: RewardInput) -> RewardOutput:
        assert input.problem_type == RewardType.MATH, \
            "Invalid problem type: expected 'MATH', but got '{}'".format(input.problem_type)
        
        problem = input.problem
        model_response = input.model_response
        
        # print("think_format", self.config.think_format)
        if self.config.think_format:
            # Extract solution.
            if THOUGHT_DELIMITER_START in model_response and THOUGHT_DELIMITER_END in model_response:
                model_solution = model_response.split(THOUGHT_DELIMITER_END)[1]
            else:
                return RewardOutput(reward=self.config.format_error_reward, is_correct=False)
        else:
            model_solution = model_response
        # print(model_solution)

        labels = labeling_responses([model_solution,], input.ground_truth["answer"])
        if labels[0] is True:
            return RewardOutput(reward=self.config.correct_reward, is_correct=True)
        else:
            return RewardOutput(reward=self.config.incorrect_reward, is_correct=False)

def reward_fn_math_verify(solution_str: str, ground_truth: Union[str, List[str]], enable_llm = False):
    reward_config = RewardConfig()
    reward_config.use_math_orm = enable_llm
    reward_fn = RewardMathFn(reward_config)
    reward_response = reward_fn(RewardInput(problem=solution_str, problem_type=RewardType.MATH, model_response=solution_str, ground_truth={"answer": ground_truth}))
    return reward_response.is_correct

def reward_fn_math_verify_no_think(solution_str: str, ground_truth: Union[str, List[str]], enable_llm = False):
    reward_config = RewardConfig()
    reward_config.think_format = False
    reward_config.use_math_orm = enable_llm
    reward_fn = RewardMathFn(reward_config)
    reward_response = reward_fn(RewardInput(problem=solution_str, problem_type=RewardType.MATH, model_response=solution_str, ground_truth={"answer": ground_truth}))
    return reward_response.is_correct

if __name__ == "__main__":
    # reward = RewardMathFn(RewardConfig)
    # import pandas as pd
    # df = pd.read_parquet('/mnt/petrelfs/share_data/yanjianhao/v9/openr1.parquet')
    # cnt = 0
    # import tqdm
    # for i in tqdm.tqdm(range(len(df))):
    #     row = df.iloc[i]
    #     ground_truth = row['reward_model']['ground_truth']
    #     solution = row['target'][0]['content']
    #     # input = RewardInput(problem="problem", problem_type=RewardType.MATH, model_response=solution, ground_truth={"answer": ground_truth})
    #     solution = solution.split(THOUGHT_DELIMITER_END)[1]
    #     output = labeling_responses([solution], ground_truth)
    #     # output = reward(input)
    #     if output[0] is False:
    #         cnt += 1
    #     print(cnt)
    # print(cnt)
    solution = """Let's break down the problem step-by-step:\n\n1. **Understand the Tournament Structure**: In a round-robin tournament where each player plays against every other player exactly once, if there are \\( n \\) players, the total number of games played is given by \\( \\binom{n}{2} = \\frac{n(n-1)}{2} \\). Each game results in either a win (1 point), a draw (0.5 points each), or a loss (0 points).\n\n2. **Player Points Calculation**: If the winner \\( W \\) wins half of his games and draws the other half, and he ends up scoring points that are 9 times less than the combined points of all other players, we need to model this mathematically. Suppose the winner \\( W \\) has \\( k \\) games, then he has \\( \\frac{k}{2} \\) wins and \\( \\frac{k}{2} \\) draws, scoring \\( \\frac{3k}{4} \\) points in total.\n\n3. **Combined Points of Other Players**: Let \\( T \\) be the total points accumulated by all players including \\( W \\). Since \\( W \\)'s points are \\( \\frac{3k}{4} \\), the rest of the players collectively have \\( T - \\frac{3k}{4} \\) points. Given that \\( W \\)'s points are 9 times less than the others' combined points, we get:\n\\[ \\frac{3k}{4} = \\frac{1}{9}(T - \\frac{3k}{4}). \\]\n\n4. **Solving the Equation**: We now solve the equation above for \\( k \\) (the number of games played by the winner). First, let's express \\( T \\) in terms of \\( k \\):\n\\[ \\frac{3k}{4} * 9 = T - \\frac{3k}{4}, \\]\n\\[ 27k / 4 + 3k / 4 = T, \\]\n\\[ 30k / 4 = T, \\]\n\\[ 15k = 2T. \\]\n\n5. **Total Points Distribution**: Since \\( W \\) is playing a round-robin tournament, \\( k = n - 1 \\), as each player plays every other player once. Substituting \\( k = n - 1 \\) into our equation:\n\\[ 15(n - 1) = 2T. \\]\n\n6. **Points Calculation for Each Player**: The maximum possible points a player can score is if they win all their games, i.e., 1 point per game. So if \\( W \\) has \\( n-1 \\) games, their maximum score is \\( n-1 \\) points. However, since \\( W \\) only wins half and draws half, they receive \\( \\frac{3(n-1)}{4} \\) points.\n\n7. **Final Equations**: Given that the remaining players' total points are 15 times the remaining games played by \\( W \\), we equate this to \\( 2T \\):\n\\[ \\text{(remaining players' total points)} = 2 * \\left(\\frac{15(n-1)}{2}\\right), \\]\n\\[ \\text{Remaining players' total points} = 15(n-1). \\]\n\n8. **Final Simplification**: We know that the sum of points from all rounds played equals \\( \\frac{n(n-1)}{2} \\), as each game contributes 1 point towards the total. Therefore:\n\\[ \\frac{n(n-1)}{2} = \\frac{3(n-1)^2}{4} + 15(n-1). \\]\n\n9. **Solve for \\( n \\)**: Simplifying the right side of the equation:\n\\[ \\frac{n(n-1)}{2} = \\frac{3(n-1)(n-1) + 60(n-1)}{4}, \\]\n\\[ \\frac{n(n-1)}{2} = \\frac{3(n-1)^2 + 60(n-1)}{4}, \\]\n\\[ 2n(n-1) = 3(n-1)^2 + 60(n-1). \\]\n\nFactoring out \\( (n-1) \\):\n\\[ 2n = 3(n-1) + 60, \\]\n\\[ 2n = 3n - 3 + 60, \\]\n\\[ 2n = 3n + 57, \\]\n\\[ 0 = n + 57, \\]\n\\[ n = 57. \\]\n\nTherefore, there must have been \\(\\boxed{57}\\) players in the tournament.<|endoftext|>"""
    
    golden_answer = "$57$"
    from math_verify import parse
    # print(parse(solution))
    # print(parse(golden_answer))
    output = reward_fn_math_verify_no_think(solution, golden_answer, enable_llm=False)
    print(output)
    
        # print(output)
    # input = RewardInput(problem="Let $P(x)=x^{4}+2 x^{3}-13 x^{2}-14 x+24$ be a polynomial with roots $r_{1}, r_{2}, r_{3}, r_{4}$. Let $Q$ be the quartic polynomial with roots $r_{1}^{2}, r_{2}^{2}, r_{3}^{2}, r_{4}^{2}$, such that the coefficient of the $x^{4}$ term of $Q$ is 1. Simplify the quotient $Q\\left(x^{2}\\right) / P(x)$, leaving your answer in terms of $x$. (You may assume that $x$ is not equal to any of $\\left.r_{1}, r_{2}, r_{3}, r_{4}\\right)$.", problem_type=RewardType.MATH, model_response="<think> I am omniscient. </think> The answer is \\boxed{24 + 14*x + (-13)*x^2 - 2*x^3 + x^4}.", ground_truth={"answer": ["10", "$x^{4}-2 x^{3}-13 x^{2}+14 x+24$"]})
    # output = reward(input)
    # print(output)
