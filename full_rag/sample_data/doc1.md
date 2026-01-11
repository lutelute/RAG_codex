# RAG Overview

Retrieval-Augmented Generation (RAG) combines search and generation to ground LLM outputs.
A typical flow: ingest data, split into chunks, embed, store vectors, retrieve top-k, and generate.
Choosing chunk size and overlap trades recall for speed.

# Prompting

A good prompt includes the user question and the retrieved context.
It should instruct the model to only use the context and to admit when missing.
