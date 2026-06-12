# -*- coding: utf-8 -*-
# Converted from llamaindex_04_custom_loader.ipynb

# %%
from dotenv import load_dotenv
load_dotenv()

# %%
# NOTEBOOK_MAGIC: !pip install llama-index-readers-smart-pdf-loader
# NOTEBOOK_MAGIC: !pip install llmsherpa

# %%
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
