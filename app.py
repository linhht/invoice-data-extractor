import os
import tempfile
import streamlit as st
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.embeddings import OpenAIEmbeddings
from langchain.document_loaders import PyPDFLoader
from langchain.output_parsers import ResponseSchema
from langchain.indexes import VectorstoreIndexCreator
from langchain.vectorstores import DocArrayInMemorySearch
from langchain.output_parsers import StructuredOutputParser

st.set_page_config(
    page_title="Invoice Data Extractor | Learn LangChain",
    page_icon="🧾"
)

st.header('🧾 Invoice Data Extractor')

st.subheader('Learn LangChain | Demo Project #1')

st.write('''
This is a demo project to related to the [Learn LangChain](https://learnlangchain.org/) mini-course.
In this project we will use LangChain document loaders, prompts and parsers to develop an AI virtual
assistant trained to extract data from our PDF invoices and return them in JSON.

In a real-world use case, these data can be further processed and stored in an Excel file, sent
to our accounting software via API or processed according to out data pipeline needs.
''')

st.info("You need your own keys to run commercial LLM models.\
    The form will process your keys safely and never store them anywhere.", icon="🔒")

openai_key = st.text_input("OpenAI Api Key")

invoice_file = st.file_uploader("Upload a PDF invoice", type=["pdf"])

if invoice_file is not None:

    with st.spinner('Processing your request...'):

        with tempfile.NamedTemporaryFile(delete=False) as temporary_file:

            temporary_file.write(invoice_file.read())

        loader = PyPDFLoader(temporary_file.name)

        llm = OpenAI(openai_api_key=openai_key, temperature=0)

        embeddings = OpenAIEmbeddings(openai_api_key=openai_key)

        index = VectorstoreIndexCreator(
            embedding=embeddings,
            vectorstore_cls=DocArrayInMemorySearch
        ).from_loaders([loader])

        query = '''
        This document is an invoice, please describe it and be sure to include all the relevant infomation.
        Be sure to include:
        - the service purchased
        - the company who issued the invoice
        - the full address of the company who issued the invoice
        - the Grand Total amount
        - the invoice number
        - the date issued
        '''

        text_invoice = index.query(query, llm=llm)

        # format the response schema
        number = ResponseSchema(name="number", description="What's the invoice number? Answer null if unclear.")
        date = ResponseSchema(name="date", description="What's the issued date of the invoice? Format it as mm-dd-yyyy, answer null if unclear.")
        company = ResponseSchema(name="company", description="What's the name of the company who issued the invoice? Answer null if unclear.")
        address = ResponseSchema(name="address", description="What's the full address of the company who issued the invoice? Format it as address, city (state), country, answer null if unclear.")
        service = ResponseSchema(name="service", description="What is the service purchased with this invoice? Answer null if unclear.")
        total = ResponseSchema(name="total", description="What's the grand total amount of the invoice? Format is as a number, answer null if unclear.")

        response_schemas = [number, date, company, address, service, total]

        output_parser = StructuredOutputParser.from_response_schemas(response_schemas)

        format_instructions = output_parser.get_format_instructions()

        template = """\
        This document is an invoice, extract the following information:

        number: What's the invoice number? Answer null if unclear.
        date: What's the issued date of the invoice? Format it as mm-dd-yyyy, answer null if unclear.
        company: What's the name of the company who issued the invoice? Answer null if unclear.
        address: What's the full address of the company who issued the invoice? Format it as address, city (state), country, answer null if unclear.
        service: What is the service purchased with this invoice? Answer null if unclear.
        total: What's the grand total amount of the invoice? Format is as a number, answer null if unclear.

        Format the output as JSON with the following keys:
        number
        date
        company
        address
        service
        total

        text: {text}

        {format_instructions}
        """

        prompt_template = ChatPromptTemplate.from_template(template=template)

        chat = ChatOpenAI(openai_api_key=openai_key, temperature=0)

        format_template = prompt_template.format_messages(text=text_invoice, format_instructions=format_instructions)

        response = chat(format_template)

        json_invoice = output_parser.parse(response.content)

        st.write('Here is your JSON invoice:')

        st.json(json_invoice)

        # clean-up the temporary file
        os.remove(temporary_file.name)