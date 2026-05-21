```python
!pip install -U "langgraph-cli[inmem]"

# Install debugpy package
!pip install debugpy
```
**Output:**

```text
Requirement already satisfied: langgraph-cli[inmem] in d:\software\miniconda3\envs\mlops\lib\site-packages (0.4.2)
Requirement already satisfied: click>=8.1.7 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-cli[inmem]) (8.2.1)
Requirement already satisfied: langgraph-sdk>=0.1.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-cli[inmem]) (0.2.6)
Requirement already satisfied: langgraph-api<0.5.0,>=0.3 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-cli[inmem]) (0.4.20)
Requirement already satisfied: langgraph-runtime-inmem>=0.7 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-cli[inmem]) (0.12.0)
Requirement already satisfied: python-dotenv>=0.8.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-cli[inmem]) (1.1.1)
Requirement already satisfied: cloudpickle>=3.0.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (3.1.1)
Requirement already satisfied: cryptography<45.0,>=42.0.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (44.0.3)
Requirement already satisfied: httpx>=0.25.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (0.28.1)
Requirement already satisfied: jsonschema-rs<0.30,>=0.20.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (0.29.1)
Requirement already satisfied: langchain-core>=0.3.64 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (0.3.75)
Requirement already satisfied: langgraph-checkpoint>=2.0.23 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (2.1.1)
Requirement already satisfied: langgraph>=0.4.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (0.6.7)
Requirement already satisfied: langsmith>=0.3.45 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (0.4.27)
Requirement already satisfied: orjson>=3.9.7 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (3.11.3)
Requirement already satisfied: pyjwt>=2.9.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (2.10.1)
Requirement already satisfied: sse-starlette<2.2.0,>=2.1.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (2.1.3)
Requirement already satisfied: starlette>=0.38.6 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (0.47.3)
Requirement already satisfied: structlog<26,>=24.1.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (25.4.0)
Requirement already satisfied: tenacity>=8.0.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (8.5.0)
Requirement already satisfied: truststore>=0.1 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (0.10.4)
Requirement already satisfied: uvicorn>=0.26.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (0.35.0)
Requirement already satisfied: watchfiles>=0.13 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (1.1.0)
Requirement already satisfied: cffi>=1.12 in d:\software\miniconda3\envs\mlops\lib\site-packages (from cryptography<45.0,>=42.0.0->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (1.17.1)
Requirement already satisfied: blockbuster<2.0.0,>=1.5.24 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-runtime-inmem>=0.7->langgraph-cli[inmem]) (1.5.25)
Requirement already satisfied: forbiddenfruit>=0.1.4 in d:\software\miniconda3\envs\mlops\lib\site-packages (from blockbuster<2.0.0,>=1.5.24->langgraph-runtime-inmem>=0.7->langgraph-cli[inmem]) (0.1.4)
Requirement already satisfied: anyio in d:\software\miniconda3\envs\mlops\lib\site-packages (from sse-starlette<2.2.0,>=2.1.0->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (4.10.0)
Requirement already satisfied: pycparser in d:\software\miniconda3\envs\mlops\lib\site-packages (from cffi>=1.12->cryptography<45.0,>=42.0.0->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (2.22)
Requirement already satisfied: colorama in d:\software\miniconda3\envs\mlops\lib\site-packages (from click>=8.1.7->langgraph-cli[inmem]) (0.4.6)
Requirement already satisfied: certifi in d:\software\miniconda3\envs\mlops\lib\site-packages (from httpx>=0.25.0->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (2025.8.3)
Requirement already satisfied: httpcore==1.* in d:\software\miniconda3\envs\mlops\lib\site-packages (from httpx>=0.25.0->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (1.0.9)
Requirement already satisfied: idna in d:\software\miniconda3\envs\mlops\lib\site-packages (from httpx>=0.25.0->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (3.10)
Requirement already satisfied: h11>=0.16 in d:\software\miniconda3\envs\mlops\lib\site-packages (from httpcore==1.*->httpx>=0.25.0->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (0.16.0)
Requirement already satisfied: jsonpatch<2.0,>=1.33 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langchain-core>=0.3.64->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (1.33)
Requirement already satisfied: PyYAML>=5.3 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langchain-core>=0.3.64->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (6.0.2)
Requirement already satisfied: typing-extensions>=4.7 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langchain-core>=0.3.64->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (4.15.0)
Requirement already satisfied: packaging>=23.2 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langchain-core>=0.3.64->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (25.0)
Requirement already satisfied: pydantic>=2.7.4 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langchain-core>=0.3.64->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (2.11.7)
Requirement already satisfied: jsonpointer>=1.9 in d:\software\miniconda3\envs\mlops\lib\site-packages (from jsonpatch<2.0,>=1.33->langchain-core>=0.3.64->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (3.0.0)
Requirement already satisfied: langgraph-prebuilt<0.7.0,>=0.6.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph>=0.4.0->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (0.6.4)
Requirement already satisfied: xxhash>=3.5.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph>=0.4.0->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (3.5.0)
Requirement already satisfied: ormsgpack>=1.10.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langgraph-checkpoint>=2.0.23->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (1.10.0)
Requirement already satisfied: requests-toolbelt>=1.0.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langsmith>=0.3.45->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (1.0.0)
Requirement already satisfied: requests>=2.0.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langsmith>=0.3.45->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (2.32.5)
Requirement already satisfied: zstandard>=0.23.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from langsmith>=0.3.45->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (0.24.0)
Requirement already satisfied: annotated-types>=0.6.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from pydantic>=2.7.4->langchain-core>=0.3.64->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (0.7.0)
Requirement already satisfied: pydantic-core==2.33.2 in d:\software\miniconda3\envs\mlops\lib\site-packages (from pydantic>=2.7.4->langchain-core>=0.3.64->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (2.33.2)
Requirement already satisfied: typing-inspection>=0.4.0 in d:\software\miniconda3\envs\mlops\lib\site-packages (from pydantic>=2.7.4->langchain-core>=0.3.64->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (0.4.1)
Requirement already satisfied: charset_normalizer<4,>=2 in d:\software\miniconda3\envs\mlops\lib\site-packages (from requests>=2.0.0->langsmith>=0.3.45->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (3.4.3)
Requirement already satisfied: urllib3<3,>=1.21.1 in d:\software\miniconda3\envs\mlops\lib\site-packages (from requests>=2.0.0->langsmith>=0.3.45->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (2.5.0)
Requirement already satisfied: sniffio>=1.1 in d:\software\miniconda3\envs\mlops\lib\site-packages (from anyio->sse-starlette<2.2.0,>=2.1.0->langgraph-api<0.5.0,>=0.3->langgraph-cli[inmem]) (1.3.1)
Requirement already satisfied: debugpy in d:\software\miniconda3\envs\mlops\lib\site-packages (1.8.16)
```
```python
!langgraph new "D:\AI工程化训练营\workspace\02_workflows\app" --template new-langgraph-project-python
```
**Output:**

```text
📥 Attempting to download repository as a ZIP archive...
URL: https://github.com/langchain-ai/new-langgraph-project/archive/refs/heads/main.zip
✅ Downloaded and extracted repository to D:\AI工程化训练营\workspace\02_workflows\app
🎉 New project created at D:\AI工程化训练营\workspace\02_workflows\app
```
```python
!cd app && langgraph dev
```
**Output:**

```text
^C
```
```python
!cd app2 && langgraph dev
```
**Output:**

```text
^C
```
