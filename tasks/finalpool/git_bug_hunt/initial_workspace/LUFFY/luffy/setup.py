from setuptools import setup, find_packages

setup(
    name='luffy',
    version='0.0.0',
    description='LUFFY: Learning to Reason under Off-Policy Guidance',
    author='Jianhao Yan',
    packages=find_packages(include=['deepscaler',]),
    install_requires=[
        'google-cloud-aiplatform',
        'pylatexenc',
        'sentence_transformers',
        'tabulate',
        'math-verify[antlr4_9_3]==0.6.0',
        'flash_attn==2.7.3',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.9',
)
