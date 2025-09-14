"""
This module contains the RewardMathFn class, which evaluates mathematical answers
and assigns rewards based on their correctness. It utilizes a language model to 
validate answers when necessary.
"""
from typing import List, Union

from deepscaler.rewards import RewardConfig, RewardFn, RewardInput, RewardOutput, RewardType

from deepscaler.rewards.math_reward import RewardMathFn

def deepscaler_reward_fn_impl1(solution_str: str, ground_truth: Union[str, List[str]], enable_llm = False):
    reward_config = RewardConfig(incorrect_reward=-0.5, correct_reward=1.0, format_error_reward=-1, unk_error_reward=-1)
    reward_config.use_math_orm = enable_llm
    reward_fn = RewardMathFn(reward_config)
    reward_response = reward_fn(RewardInput(problem=solution_str, problem_type=RewardType.MATH, model_response=solution_str, ground_truth={"answer": ground_truth}))
    # return reward_response.is_correct
    return reward_response.reward

def math_verify_reward_fn(solution_str: str, ground_truth: Union[str, List[str]], enable_llm = False):
    # ground_truth = "\\boxed{" + ground_truth + "}"
    assert isinstance(ground_truth, str)
    acc_reward = accuracy_reward([solution_str], [ground_truth])[0]
    f_reward = format_reward([solution_str])[0]
    return acc_reward * f_reward

def accuracy_reward(completions, solution, **kwargs):
    from math_verify import LatexExtractionConfig, parse, verify
    from latex2sympy2_extended import NormalizationConfig

    """Reward function that checks if the completion is the same as the ground truth."""
    contents = completions
    rewards = []
    for content, sol in zip(contents, solution):
        gold_parsed = parse(
            sol,
            extraction_mode="first_match",
            extraction_config=[LatexExtractionConfig()],
        )
        if len(gold_parsed) != 0:
            # We require the answer to be provided in correct latex (no malformed operators)
            answer_parsed = parse(
                content,
                extraction_config=[
                    LatexExtractionConfig(
                        normalization_config=NormalizationConfig(
                            nits=False,
                            malformed_operators=False,
                            basic_latex=True,
                            equations=True,
                            boxed="all",
                            units=True,
                        ),
                        # Ensures that boxed is tried first
                        boxed_match_priority=0,
                        try_extract_without_anchor=False,
                    )
                ],
                extraction_mode="first_match",
            )
            # Reward 1 if the content is the same as the ground truth, 0 otherwise
            try:
                reward = float(verify(answer_parsed, gold_parsed))
            except Exception as e:
                print(f"verify failed: {e}, answer: {answer_parsed}, gold: {gold_parsed}")
                reward = 0.0
        else:
            # If the gold solution is not parseable, we reward 1 to skip this example
            reward = 1.0
            print("Failed to parse gold solution: ", sol)
        rewards.append(reward)

    return rewards
    
import re
def format_reward(completions, **kwargs):
    """Reward function that checks if the reasoning process is enclosed within <think> and </think> tags, while the final answer is enclosed within <answer> and </answer> tags."""
    pattern = r"^<think>\n.*?\n</think>"
    completion_contents = [completion for completion in completions]
    matches = [re.match(pattern, content, re.DOTALL | re.MULTILINE) for content in completion_contents]
    return [1.0 if match else 0.0 for match in matches]

if __name__ == "__main__":
    solution_str = '<think>\nOkay, so I need to figure out what kind of graph is represented by the equation (1/5)^{|x - 3|} = (1/5)^{|x + 3| - 1}. The options are Line, Ellipse, Hyperbola with real semi-axis length of 1, or the right branch of a hyperbola with foci on the x-axis and real semi-axis length of 1/2. \n\nFirst, since both sides of the equation are exponentials with the same base (1/5), which is between 0 and 1, the function (1/5)^t is a decreasing function. That means if (1/5)^a = (1/5)^b, then a must equal b. So, I can set the exponents equal to each other. So, |x - 3| = |x + 3| - 1. \n\nWait, but before I proceed, I need to check if this is valid. Since the base is the same and positive, and since (1/5)^t is injective (one-to-one), then yes, the exponents must be equal. So, that step is correct.\n\nNow, the equation simplifies to |x - 3| = |x + 3| - 1. Hmm. Let\'s solve this equation for x. \n\nAbsolute value equations can sometimes be tricky because of the different cases depending on the sign inside the absolute value. Let me recall that |a| = |b| implies a = b or a = -b. But here, the equation is |x - 3| = |x + 3| - 1. So, maybe I need to consider different cases based on the values of x where the expressions inside the absolute values change sign. \n\nThe expressions inside the absolute values are (x - 3) and (x + 3). The critical points where these expressions change sign are at x = 3 and x = -3. So, I can split the real line into intervals based on these points: x < -3, -3 ≤ x < 3, and x ≥ 3. Then, in each interval, the absolute value expressions can be rewritten without the absolute value signs by considering their sign.\n\nLet me start with the first interval: x < -3.\n\nCase 1: x < -3\n\nIn this interval, x - 3 is negative (since x < -3 < 3) and x + 3 is also negative (since x < -3). Therefore, |x - 3| = -(x - 3) = -x + 3 and |x + 3| = -(x + 3) = -x - 3.\n\nSubstituting into the equation: |x - 3| = |x + 3| - 1\n\nSo, -x + 3 = (-x - 3) - 1\n\nSimplify the right-hand side: -x - 3 - 1 = -x - 4\n\nSo, equation becomes: -x + 3 = -x - 4\n\nAdding x to both sides: 3 = -4\n\nWait, that\'s not possible. 3 does not equal -4. So, in this case, there is no solution when x < -3.\n\nCase 2: -3 ≤ x < 3\n\nIn this interval, x - 3 is still negative (since x < 3), so |x - 3| = -(x - 3) = -x + 3. However, x + 3 is non-negative (since x ≥ -3), so |x + 3| = x + 3.\n\nSubstituting into the equation: -x + 3 = (x + 3) - 1\n\nSimplify the right-hand side: x + 3 - 1 = x + 2\n\nSo, equation becomes: -x + 3 = x + 2\n\nLet me solve for x: Add x to both sides: 3 = 2x + 2\n\nSubtract 2: 1 = 2x => x = 1/2\n\nNow, check if x = 1/2 is in the interval -3 ≤ x < 3. Yes, 1/2 is between -3 and 3. So, x = 1/2 is a valid solution in this case.\n\nCase 3: x ≥ 3\n\nIn this interval, both x - 3 and x + 3 are non-negative. Therefore, |x - 3| = x - 3 and |x + 3| = x + 3.\n\nSubstituting into the equation: x - 3 = (x + 3) - 1\n\nSimplify the right-hand side: x + 3 - 1 = x + 2\n\nSo, equation becomes: x - 3 = x + 2\n\nSubtract x from both sides: -3 = 2\n\nThat\'s not true. So, no solution in this interval.\n\nSo, the only solution is x = 1/2. Wait, but the question is about the graph represented by the equation. If the solution is only x = 1/2, then that would be a vertical line at x = 1/2, which is a line. But one of the options is A. Line, so that would be the answer? But let me check again because maybe I made a mistake.\n\nWait, but the original equation is in terms of x, but the problem mentions z is a complex number, and the equation is given with |x - 3| and |x + 3|. Wait, maybe there\'s a typo, or maybe x is actually the real part of z? Let me check the problem again.\n\nThe problem says: "z is a complex number, then the graph represented by the equation (1/5)^{|x - 3|} = (1/5)^{|x + 3| - 1} is..." Hmm. So, maybe x here is the real part of the complex number z. So, z can be written as x + yi, where x and y are real numbers. Then, the equation involves |x - 3| and |x + 3|. So, the equation only involves the real part x, but there is no restriction on the imaginary part y. So, if we solve for x, then for any y, as long as x satisfies the equation, the point (x, y) is on the graph.\n\nWait, but in my previous analysis, I found x = 1/2 is the only solution. So, in the complex plane, the solutions would be all complex numbers z = (1/2) + yi, where y is any real number. So, this is a vertical line in the complex plane, which corresponds to x = 1/2. Therefore, the graph is a vertical line. So, the answer should be A. Line.\n\nBut the options given include hyperbola options. So, perhaps my analysis is missing something. Wait, let me check again.\n\nWait, the original equation is (1/5)^{|x - 3|} = (1/5)^{|x + 3| - 1}. So, since (1/5)^a = (1/5)^b implies a = b, we have |x - 3| = |x + 3| - 1. So, solving this equation, as before, gives x = 1/2, but if x is allowed to be any real number and y is arbitrary, then the graph is the vertical line x = 1/2 in the complex plane (which is like the Cartesian plane). So, that\'s a line. Therefore, the answer should be A. Line.\n</think>\nThe graph represented by the equation \\(\\left(\\frac{1}{5}\\right)^{|x-3|} = \\left(\\frac{1}{5}\\right)^{|x+3|-1}\\) is a vertical line at \\(x = \\frac{1}{2}\\). So, the correct answer is:\n\n\\(\\boxed{\\text{A}}\\).'
    ground_truth = "\boxed{23}"
    
    print(math_verify_reward_fn(solution_str, ground_truth, enable_llm=False))
    
    # solution_str2 = "Okay, so I need to find the range of \\(\\log_{a} x^{2} y\\) given the conditions:\n\n1. \\(\\log_{a}^{2} x + \\log_{a}^{2} y - \\log_{a}(x y)^{2} \\leq 2\\)\n2. \\(\\log_{a} y \\geq 1\\)\n\nAnd \\(a\\) is a positive real number not equal to 1. Hmm, let's start by simplifying the given inequality. Maybe I can rewrite all the terms in terms of \\(\\log_{a} x\\) and \\(\\log_{a} y\\). Let me set some variables to make it easier. Let me denote \\(u = \\log_{a} x\\) and \\(v = \\log_{a} y\\). Then the inequality becomes:\n\n\\(u^2 + v^2 - \\log_{a}(x y)^2 \\leq 2\\)\n\nBut \\(\\log_{a}(x y)^2\\) can be expanded using logarithm properties. Remember that \\(\\log_{a}(xy)^2 = 2 \\log_{a}(xy) = 2(\\log_{a} x + \\log_{a} y) = 2(u + v)\\). So substituting that back in, the inequality becomes:\n\n\\(u^2 + v^2 - 2(u + v) \\leq 2\\)\n\nSo that simplifies to:\n\n\\(u^2 + v^2 - 2u - 2v \\leq 2\\)\n\nI can rearrange this inequality by completing the squares for both \\(u\\) and \\(v\\). Let me try that.\n\nFor the \\(u\\) terms: \\(u^2 - 2u\\). Completing the square: \\(u^2 - 2u + 1 - 1 = (u - 1)^2 - 1\\)\n\nSimilarly for the \\(v\\) terms: \\(v^2 - 2v\\). Completing the square: \\(v^2 - 2v + 1 - 1 = (v - 1)^2 - 1\\)\n\nSo substituting back into the inequality:\n\n\\((u - 1)^2 - 1 + (v - 1)^2 - 1 \\leq 2\\)\n\nSimplify the constants:\n\n\\((u - 1)^2 + (v - 1)^2 - 2 \\leq 2\\)\n\nAdd 2 to both sides:\n\n\\((u - 1)^2 + (v - 1)^2 \\leq 4\\)\n\nSo the inequality represents a circle centered at (1, 1) with radius 2 in the \\(uv\\)-plane. But we also have the condition that \\(v \\geq 1\\), since \\(\\log_{a} y \\geq 1\\). So we need to consider the intersection of the circle \\((u - 1)^2 + (v - 1)^2 \\leq 4\\) with the half-plane \\(v \\geq 1\\).\n\nNow, the question is to find the range of \\(\\log_{a} x^{2} y\\). Let's express that in terms of \\(u\\) and \\(v\\):\n\n\\(\\log_{a} x^{2} y = \\log_{a} x^{2} + \\log_{a} y = 2 \\log_{a} x + \\log_{a} y = 2u + v\\)\n\nSo we need to find the possible values of \\(2u + v\\) given that \\((u - 1)^2 + (v - 1)^2 \\leq 4\\) and \\(v \\geq 1\\).\n\nThis is essentially finding the maximum and minimum of the linear function \\(2u + v\\) over the intersection of a circle and a half-plane. To solve this, I can use methods from calculus or geometry. Since it's a circle, maybe parametrizing it would help, or using Lagrange multipliers. Let me consider both approaches.\n\nFirst, let's parametrize the circle. Let me denote \\(u - 1 = 2 \\cos \\theta\\) and \\(v - 1 = 2 \\sin \\theta\\), where \\(\\theta \\in [0, 2\\pi)\\). But since \\(v \\geq 1\\), we have \\(v - 1 = 2 \\sin \\theta \\geq 0\\), so \\(\\sin \\theta \\geq 0\\), which implies \\(\\theta \\in [0, \\pi]\\).\n\nTherefore, \\(u = 1 + 2 \\cos \\theta\\) and \\(v = 1 + 2 \\sin \\theta\\). Substitute these into \\(2u + v\\):\n\n\\(2u + v = 2(1 + 2 \\cos \\theta) + (1 + 2 \\sin \\theta) = 2 + 4 \\cos \\theta + 1 + 2 \\sin \\theta = 3 + 4 \\cos \\theta + 2 \\sin \\theta\\)\n\nNow, the range of \\(4 \\cos \\theta + 2 \\sin \\theta\\) can be found by noting that it is a linear combination of sine and cosine functions. The maximum and minimum values of \\(4 \\cos \\theta + 2 \\sin \\theta\\) are \\(\\pm \\sqrt{4^2 + 2^2} = \\pm \\sqrt{20} = \\pm 2\\sqrt{5}\\).\n\nSo the range of \\(2u + v\\) is from \\(3 - 2\\sqrt{5}\\) to \\(3 + 2\\sqrt{5}\\).\n\nThus, the range of \\(\\log_{a} x^{2} y\\) is \\(\\boxed{[3 - 2\\sqrt{5}, 3 + 2\\sqrt{5}]}\\).\n</think>\n\\boxed{[3 - 2\\sqrt{5}, 3 + 2\\sqrt{5}]}"