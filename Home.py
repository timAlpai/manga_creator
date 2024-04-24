#from langchain.llms import MistralAI
import streamlit as st
import os
import urllib
import base64
import fitz  # Import PyMuPDF
import re
import json
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chains import SequentialChain
from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings
from dotenv import load_dotenv


load_dotenv()
api_key = os.getenv("mistral_api_key")

#streamlit application
st.set_page_config(layout='wide')

st.title('Book Manga Extractor')

# Initialize session variables if not already set
if 'book_extracted' not in st.session_state:
    st.session_state.book_extracted = False

if 'chapters' not in st.session_state:
    st.session_state.chapters = []
if 'prompts' not in st.session_state:
    st.session_state.prompts = []
# Function to save the uploaded file and extract chapters
@st.cache_resource
def save_and_extract_chapters(uploadedfile):
   
    base_path = os.path.join("data", uploadedfile.name)
    # Ensure the directory exists; if not, create it
   
    if not os.path.exists(base_path):
        os.makedirs(os.path.dirname(base_path), exist_ok=True)
        with open(base_path, "xb") as f:
            f.write(uploadedfile.getbuffer())
        print("Fichier créé : ", base_path)
    else: 
        # Write the file contents to the new path
        with open(base_path, "wb") as f:
            f.write(uploadedfile.getbuffer())
        print("File saved at:", base_path)
    # Open the PDF file
    doc = fitz.open(base_path)
    chapters = []  # List to store chapter texts
    chapter_pattern = re.compile(r'^CHAPITRE \d+')  # Adjust as per your chapter pattern
    current_chapter = 0
    chapter_text = []

    for page_number in range(len(doc)):
        if page_number <= toc_end_page:
            continue  # Skip TOC pages
        page = doc[page_number]
        text = page.get_text()
        lines = text.split('\n')
        for line in lines:
            if chapter_pattern.match(line.strip()):
                if chapter_text and current_chapter > 0:
                    chapters.append('\n'.join(chapter_text))
                    chapter_text = []
                current_chapter += 1
            if current_chapter > 0:
                chapter_text.append(line)
    
    if chapter_text and current_chapter > 0:
        chapters.append('\n'.join(chapter_text))
    
    # Save chapters as individual files
    for i, text in enumerate(chapters, 1):
        with open(os.path.join("data", f"chapter_{i}_{uploadedfile.name}.txt"), "w", encoding='utf-8') as file:
            file.write(text)
    
    return chapters, base_path  # Return list of chapter texts and path to PDF

# Create a function to run each chain
def run_chain(chain, input_text):
    with st.spinner("Running chain..."):
        response = chain.run(input_text)       
    return response
def displayPDF(file):
    with open(file, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = F'<iframe src="data:application/pdf;base64,{base64_pdf}" width="500" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)


toc_end_page = st.number_input('Enter the last page number of the Table of Contents:', min_value=1, value=1)
uploaded_pdf = st.file_uploader("Upload your PDF", type=['pdf'])

if uploaded_pdf is not None:
    total=[]
    chapters, pdf_file = save_and_extract_chapters(uploaded_pdf)
    if 'edited_chapters' not in st.session_state:
        # Initialize session state to store edits
        st.session_state['edited_chapters'] = chapters[:]

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.success("PDF uploaded and chapters extracted")
        displayPDF(pdf_file)

    with col2:
        chapter_index = st.selectbox("Select Chapter", list(range(1, len(chapters) + 1)))
        current_text = st.session_state['edited_chapters'][chapter_index - 1]
        chapter_text = st.text_area("Chapter Text", current_text, height=250, key=f'chapter_{chapter_index}')

        if st.button('Save Changes', key=f'save_{chapter_index}'):
            # Update the text in session state when saving
            st.session_state['edited_chapters'][chapter_index - 1] = chapter_text
            
            # Define the path to the chapter file
            chapter_filename = os.path.join("data", f"chapter_{chapter_index}_{uploaded_pdf.name}.txt")
            # Write the modified text back to the appropriate file
            with open(chapter_filename, "w", encoding="utf-8") as file:
                file.write(chapter_text)
            st.success(f"Chapter {chapter_index} saved successfully!")
        

        if st.button('process chapter', key=f'process_{chapter_index}'):
                        
        
            first_input_prompt = PromptTemplate(input_variables = ['chapter_text'],
                                                template="Résumez le texte suivant en utilisant un langage clair et concis, en vous concentrant sur les événements clés, les personnages principaux, les conflits et les résolutions. Assurez-vous d'inclure toutes les informations importantes tout en évitant les répétitions inutiles. utilisez le format markdown pour la réponse avec tous les éléments d'un résumé faites le en français  : {chapter_text}"
                                                )
            # AI LLMS

            llm = ChatMistralAI(api_key=api_key, temperature=0.8, model="mistral-large-latest")
            #LLM Chain
            chain1  = LLMChain(llm=llm, prompt = first_input_prompt, verbose=True, output_key = 'summaryofchapter')

            #Prompt Template       

            second_input_prompt = PromptTemplate(input_variables=['chapter_text'],
                template = "Identifiez les attitudes et les émotions associées à chaque personnage mentionné dans le texte suivant. Extrayez également les éléments d'imagerie guidée tels que la scène (où et quand l'action se déroule), le thème (le sujet principal de l'histoire), les composantes et l'intention (les éléments clés de l'intrigue et ce que les personnages essaient d'accomplir), et l'ambiance (l'atmosphère générale de l'histoire). utilisez le format markdown pour la réponse  n'omettez aucun détail, ni information y compris les nuances ou sous entendu. faites le en français : {chapter_text}"
                                    )
            #LLM Chain

            chain2  = LLMChain(llm=llm, prompt = second_input_prompt, verbose=True, output_key = 'chapterfullinfo')
            

            #Prompt Template

            third_input_prompt = PromptTemplate(input_variables=['chapterfullinfo', 'summaryofchapter','chapter_text'],
                                                template="Vérifiez la cohérence factuelle, sémantique et narrative entre le texte original, le résumé et la liste d'informations fournis. Fournissez un score de confiance pour chaque élément, ainsi que des commentaires détaillés pour justifier votre évaluation. Identifiez les éventuelles incohérences et suggérez des moyens de les résoudre,et fournir un score de confidence au résumé par rapport au texte originale et a la liste d'informations par rapport au texte originale fais le en français :\n  texte originale : {chapter_text}\n informations complètes: {chapterfullinfo}\n Résumé du chapître : {summaryofchapter}\n"
                                                )
            #LLM Chain

            chain3  = LLMChain(llm=llm, prompt = third_input_prompt, verbose=True, output_key = 'cohérence information')
            #, 'summaryofchapter'
            fourth_input_prompt= PromptTemplate(input_variables=['chapterfullinfo','chapter_text'],
                                                template="il est important de respecter ces règles. Créez un scénario de manga en trois chapitres, avec trois planches par chapitre et six cases par planche, à partir du texte original et de la liste d'informations fournis. Chaque chapitre devrait se concentrer sur un événement clé de l'histoire, avec une introduction, un développement et une conclusion clairs. Chaque planche devrait se concentrer sur un personnage principal ou un conflit important, en utilisant des techniques de narration visuelle pour rendre l'histoire plus engageante. Fournissez des détails spécifiques sur les éléments clés à inclure dans chaque chapitre et chaque planche. Pensez étape par étape le format de votre réponse est markdown et liste, fais le en français :\n  texte originale : {chapter_text}\n informations complètes: {chapterfullinfo}\n "
                                                )
            chain4=LLMChain(llm=llm, prompt = fourth_input_prompt, verbose=True, output_key = 'scénario manga')
            
            fifth_input_prompt  = PromptTemplate(input_variables=['chapterfullinfo' , 'scénario manga'],
                                                template="il est important de suivres et respecter ces règles. Créez un séquencier détaillé pour le scénario de manga fourni, en décrivant le contenu graphique et scénaristique de chaque case. Chaque case devrait se concentrer sur utilisez des techniques de narration visuelle pour rendre chaque case plus engageante, telles que des angles de caméra intéressants, des expressions faciales évocatrices et des effets sonores. Fournissez des détails spécifiques sur les éléments clés à inclure dans chaque case scénario. Pensez étape par étape le format de votre réponse est markdown  et liste, fais le en français :\n {scénario manga}  référence : {chapterfullinfo}\n"
            )
            chain5 = LLMChain(llm=llm, prompt=fifth_input_prompt,verbose=True, output_key='sequencier')

            #parent_chain = SequentialChain(chains = [chain1, chain2, chain3,chain4,chain5], input_variables = ['chapter_text'], output_variables = ['summaryofchapter', 'chapterfullinfo', 'cohérence information','scénario manga','sequencier'], verbose = True)
            
            
                # Exécution de la chaîne séquentielle avec l'argument verbose=True

            parent_chain = SequentialChain(chains = [chain1, chain2, chain3,chain4,chain5], input_variables = ['chapter_text'], output_variables = ['summaryofchapter', 'chapterfullinfo', 'cohérence information','scénario manga','sequencier'], verbose = True)

            total=parent_chain({'chapter_text':chapter_text})
            
            
            total_str=json.dumps(total)

            # Define the path to the chapter file
            chapter_filename = os.path.join(
                "data", f"chapter_{chapter_index}_{uploaded_pdf.name}_extract1.txt")
            # Write the modified text back to the appropriate file
            with open(chapter_filename, "w", encoding="utf-8") as file:
                file.write(total_str)
            st.success(f"Chapter {chapter_index} saved successfully!")
            
    with col3:
        st.success("information complète du chapitre")
        if total:
            st.write(total['chapterfullinfo'])
    if total:
        st.success("Résumé du chapitre")
        st.markdown(total['summaryofchapter'], unsafe_allow_html=True)
        st.success("cohérences des informations collecté")    
        st.markdown(total['cohérence information'], unsafe_allow_html=True)
        st.success("scénario manga basé sur le chapitre")
        st.markdown(total['scénario manga'], unsafe_allow_html=True)
        st.success("séquencier du scénario manga")
        st.markdown(total['sequencier'], unsafe_allow_html = True)
        # Save the generated texts in Markdown format
        output_file = os.path.join("data", f"chapter_{chapter_index}_{uploaded_pdf.name}_output.md")
        with open(output_file, "w", encoding="utf-8") as file:
            file.write("# Chapter Summary\n")
            file.write(total['summaryofchapter'] + "\n\n")
            file.write("# Chapter Full Information\n")
            file.write(total['chapterfullinfo'] + "\n\n")
            file.write("# Coherence Information\n")
            file.write(total['cohérence information'] + "\n\n")
            file.write("# Manga Scenario\n")
            file.write(total['scénario manga'] + "\n\n")
            file.write("# Manga Storyboard\n")
            file.write(total['sequencier'] + "\n\n")

        st.success(f"Chapter {chapter_index} processed and saved successfully!")