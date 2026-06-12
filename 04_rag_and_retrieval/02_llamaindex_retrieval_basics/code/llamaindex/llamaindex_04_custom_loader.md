<!-- Converted from llamaindex_04_custom_loader.ipynb -->

```python
from dotenv import load_dotenv
load_dotenv()
```

```python
!pip install llama-index-readers-smart-pdf-loader
!pip install llmsherpa
```

输出：

```text
Looking in indexes: https://mirrors.aliyun.com/pypi/simple/
Requirement already satisfied: llama-index-readers-smart-pdf-loader in d:\miniconda3\envs\mlops\lib\site-packages (0.4.0)
Requirement already satisfied: llama-index-core<0.14,>=0.13.0 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-readers-smart-pdf-loader) (0.13.3)
Requirement already satisfied: llmsherpa<0.2,>=0.1.4 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-readers-smart-pdf-loader) (0.1.4)
Requirement already satisfied: aiohttp<4,>=3.8.6 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (3.12.15)
Requirement already satisfied: aiosqlite in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (0.21.0)
Requirement already satisfied: banks<3,>=2.2.0 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (2.2.0)
Requirement already satisfied: dataclasses-json in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (0.6.7)
Requirement already satisfied: deprecated>=1.2.9.3 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (1.2.18)
Requirement already satisfied: dirtyjson<2,>=1.0.8 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (1.0.8)
Requirement already satisfied: filetype<2,>=1.2.0 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (1.2.0)
Requirement already satisfied: fsspec>=2023.5.0 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (2025.7.0)
Requirement already satisfied: httpx in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (0.28.1)
Requirement already satisfied: llama-index-workflows<2,>=1.0.1 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (1.3.0)
Requirement already satisfied: nest-asyncio<2,>=1.5.8 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (1.6.0)
Requirement already satisfied: networkx>=3.0 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (3.5)
Requirement already satisfied: nltk>3.8.1 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (3.9.1)
Requirement already satisfied: numpy in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (2.3.2)
Requirement already satisfied: pillow>=9.0.0 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (11.3.0)
Requirement already satisfied: platformdirs in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (4.4.0)
Requirement already satisfied: pydantic>=2.8.0 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (2.11.7)
Requirement already satisfied: pyyaml>=6.0.1 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (6.0.2)
Requirement already satisfied: requests>=2.31.0 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (2.32.5)
Requirement already satisfied: setuptools>=80.9.0 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (80.9.0)
Requirement already satisfied: sqlalchemy>=1.4.49 in d:\miniconda3\envs\mlops\lib\site-packages (from sqlalchemy[asyncio]>=1.4.49->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (2.0.43)
Requirement already satisfied: tenacity!=8.4.0,<10.0.0,>=8.2.0 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (9.1.2)
Requirement already satisfied: tiktoken>=0.7.0 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (0.11.0)
Requirement already satisfied: tqdm<5,>=4.66.1 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (4.67.1)
Requirement already satisfied: typing-extensions>=4.5.0 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (4.15.0)
Requirement already satisfied: typing-inspect>=0.8.0 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (0.9.0)
Requirement already satisfied: wrapt in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (1.17.3)
Requirement already satisfied: aiohappyeyeballs>=2.5.0 in d:\miniconda3\envs\mlops\lib\site-packages (from aiohttp<4,>=3.8.6->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (2.6.1)
Requirement already satisfied: aiosignal>=1.4.0 in d:\miniconda3\envs\mlops\lib\site-packages (from aiohttp<4,>=3.8.6->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (1.4.0)
Requirement already satisfied: attrs>=17.3.0 in d:\miniconda3\envs\mlops\lib\site-packages (from aiohttp<4,>=3.8.6->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (25.3.0)
Requirement already satisfied: frozenlist>=1.1.1 in d:\miniconda3\envs\mlops\lib\site-packages (from aiohttp<4,>=3.8.6->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (1.7.0)
Requirement already satisfied: multidict<7.0,>=4.5 in d:\miniconda3\envs\mlops\lib\site-packages (from aiohttp<4,>=3.8.6->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (6.6.4)
Requirement already satisfied: propcache>=0.2.0 in d:\miniconda3\envs\mlops\lib\site-packages (from aiohttp<4,>=3.8.6->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (0.3.2)
Requirement already satisfied: yarl<2.0,>=1.17.0 in d:\miniconda3\envs\mlops\lib\site-packages (from aiohttp<4,>=3.8.6->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (1.20.1)
Requirement already satisfied: griffe in d:\miniconda3\envs\mlops\lib\site-packages (from banks<3,>=2.2.0->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (1.13.0)
Requirement already satisfied: jinja2 in d:\miniconda3\envs\mlops\lib\site-packages (from banks<3,>=2.2.0->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (3.1.6)
Requirement already satisfied: llama-index-instrumentation>=0.1.0 in d:\miniconda3\envs\mlops\lib\site-packages (from llama-index-workflows<2,>=1.0.1->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (0.4.0)
Requirement already satisfied: urllib3 in d:\miniconda3\envs\mlops\lib\site-packages (from llmsherpa<0.2,>=0.1.4->llama-index-readers-smart-pdf-loader) (2.5.0)
Requirement already satisfied: colorama in d:\miniconda3\envs\mlops\lib\site-packages (from tqdm<5,>=4.66.1->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (0.4.6)
Requirement already satisfied: idna>=2.0 in d:\miniconda3\envs\mlops\lib\site-packages (from yarl<2.0,>=1.17.0->aiohttp<4,>=3.8.6->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (3.10)
Requirement already satisfied: click in d:\miniconda3\envs\mlops\lib\site-packages (from nltk>3.8.1->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (8.2.1)
Requirement already satisfied: joblib in d:\miniconda3\envs\mlops\lib\site-packages (from nltk>3.8.1->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (1.5.1)
Requirement already satisfied: regex>=2021.8.3 in d:\miniconda3\envs\mlops\lib\site-packages (from nltk>3.8.1->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (2025.7.33)
Requirement already satisfied: annotated-types>=0.6.0 in d:\miniconda3\envs\mlops\lib\site-packages (from pydantic>=2.8.0->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (0.7.0)
Requirement already satisfied: pydantic-core==2.33.2 in d:\miniconda3\envs\mlops\lib\site-packages (from pydantic>=2.8.0->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (2.33.2)
Requirement already satisfied: typing-inspection>=0.4.0 in d:\miniconda3\envs\mlops\lib\site-packages (from pydantic>=2.8.0->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (0.4.1)
Requirement already satisfied: charset_normalizer<4,>=2 in d:\miniconda3\envs\mlops\lib\site-packages (from requests>=2.31.0->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (3.4.3)
Requirement already satisfied: certifi>=2017.4.17 in d:\miniconda3\envs\mlops\lib\site-packages (from requests>=2.31.0->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (2025.8.3)
Requirement already satisfied: greenlet>=1 in d:\miniconda3\envs\mlops\lib\site-packages (from sqlalchemy>=1.4.49->sqlalchemy[asyncio]>=1.4.49->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (3.2.4)
Requirement already satisfied: mypy-extensions>=0.3.0 in d:\miniconda3\envs\mlops\lib\site-packages (from typing-inspect>=0.8.0->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (1.1.0)
Requirement already satisfied: marshmallow<4.0.0,>=3.18.0 in d:\miniconda3\envs\mlops\lib\site-packages (from dataclasses-json->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (3.26.1)
Requirement already satisfied: packaging>=17.0 in d:\miniconda3\envs\mlops\lib\site-packages (from marshmallow<4.0.0,>=3.18.0->dataclasses-json->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (25.0)
Requirement already satisfied: anyio in d:\miniconda3\envs\mlops\lib\site-packages (from httpx->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (4.10.0)
Requirement already satisfied: httpcore==1.* in d:\miniconda3\envs\mlops\lib\site-packages (from httpx->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (1.0.9)
Requirement already satisfied: h11>=0.16 in d:\miniconda3\envs\mlops\lib\site-packages (from httpcore==1.*->httpx->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (0.16.0)
Requirement already satisfied: sniffio>=1.1 in d:\miniconda3\envs\mlops\lib\site-packages (from anyio->httpx->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (1.3.1)
Requirement already satisfied: MarkupSafe>=2.0 in d:\miniconda3\envs\mlops\lib\site-packages (from jinja2->banks<3,>=2.2.0->llama-index-core<0.14,>=0.13.0->llama-index-readers-smart-pdf-loader) (3.0.2)
Looking in indexes: https://mirrors.aliyun.com/pypi/simple/
Requirement already satisfied: llmsherpa in d:\miniconda3\envs\mlops\lib\site-packages (0.1.4)
Requirement already satisfied: urllib3 in d:\miniconda3\envs\mlops\lib\site-packages (from llmsherpa) (2.5.0)
```

```python
from llama_index.readers.smart_pdf_loader import SmartPDFLoader

llmsherpa_api_url = "https://readers.llmsherpa.com/api/document/developer/parseDocument?renderFormat=all"
pdf_url = "https://arxiv.org/pdf/1910.13461.pdf"  # also allowed is a file path e.g. /home/downloads/xyz.pdf
documents = SmartPDFLoader(llmsherpa_api_url=llmsherpa_api_url).load_data(pdf_url)


# 参考  https://github.com/run-llama/llama_index/tree/main/llama-index-integrations/readers/llama-index-readers-smart-pdf-loader/llama_index


# base.py

"""Smart PDF Loader."""

from typing import Any, Dict, List, Optional

from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document


class SmartPDFLoader(BaseReader):
    """
    SmartPDFLoader uses nested layout information such as sections, paragraphs, lists and tables to smartly chunk PDFs for optimal usage of LLM context window.

    Args:
        llmsherpa_api_url (str): Address of the service hosting llmsherpa PDF parser

    """

    def __init__(
        self, *args: Any, llmsherpa_api_url: str = None, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        from llmsherpa.readers import LayoutPDFReader

        self.pdf_reader = LayoutPDFReader(llmsherpa_api_url)

    def load_data(
        self, pdf_path_or_url: str, extra_info: Optional[Dict] = None
    ) -> List[Document]:
        """
        Load data and extract table from PDF file.

        Args:
            pdf_path_or_url (str): A url or file path pointing to the PDF

        Returns:
            List[Document]: List of documents.

        """
        results = []
        doc = self.pdf_reader.read_pdf(str(pdf_path_or_url))
        for chunk in doc.chunks():
            document = Document(
                text=chunk.to_context_text(),
                extra_info={**extra_info, "chunk_type": chunk.tag}
                if extra_info
                else {"chunk_type": chunk.tag},
            )
            results.append(document)
        return results
```
