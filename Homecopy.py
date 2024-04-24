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
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage


load_dotenv()
api_key = os.getenv("mistral_api_key")

#streamlit application
st.set_page_config(layout='wide')

st.title('Book Manga Extractor')

# Initialize session variables if not already set
if 'total' not in st.session_state:
    st.session_state.total = {}

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
    chapter_pattern = re.compile(r'^CHAPITRE *\d+')  # Adjust as per your chapter pattern
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
    total=st.session_state.total
    chapters, pdf_file = save_and_extract_chapters(uploaded_pdf)
    client = MistralClient(api_key=api_key)
    if 'edited_chapters' not in st.session_state:
        # Initialize session state to store edits
        st.session_state['edited_chapters'] = chapters[:]

    col1, col2 = st.columns([1, 1])
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
        first_input_prompt = PromptTemplate(input_variables = ['chapter_text'],
                                                template="Résumez le texte suivant en utilisant un langage clair et concis, en vous concentrant sur les événements clés, les personnages principaux, les conflits et les résolutions. Assurez-vous d'inclure toutes les informations importantes tout en évitant les répétitions inutiles. utilisez le format markdown pour la réponse avec tous les éléments d'un résumé faites le en français  : {chapter_text}"
                                                )
            # AI LLMS

        llm = ChatMistralAI(api_key=api_key, temperature=0.8, model="mistral-medium-latest")
        #LLM Chain
        chain1  = LLMChain(llm=llm, prompt = first_input_prompt, verbose=True, output_key = 'summaryofchapter')

           # Create an expander for each chain
        with st.expander("Chain 1: Summary of Chapter"):
            if st.button("Run Chain 1"):
                total['summaryofchapter']=run_chain(chain1, {'chapter_text': chapter_text})
                st.session_state.total['summaryofchapter'] = total['summaryofchapter']
                st.success("Chain 1: Summary of Chapter executed successfully!")
                
        #Prompt Template       

        second_input_prompt = PromptTemplate(input_variables=['chapter_text'],
            template = "Identifiez les attitudes et les émotions associées à chaque personnage mentionné dans le texte suivant. Extrayez également les éléments d'imagerie guidée tels que la scène (où et quand l'action se déroule), le thème (le sujet principal de l'histoire), les composantes et l'intention (les éléments clés de l'intrigue et ce que les personnages essaient d'accomplir), et l'ambiance (l'atmosphère générale de l'histoire). utilisez le format markdown pour la réponse  n'omettez aucun détail, ni information y compris les nuances ou sous entendu. faites le en français : {chapter_text}"
                                )
        #LLM Chain

        chain2  = LLMChain(llm=llm, prompt = second_input_prompt, verbose=True, output_key = 'chapterfullinfo')
            
        with st.expander("Chain 2: Chapter Full Info"):
            if st.button("Run Chain 2"):
                total['chapterfullinfo']=run_chain(chain2, {'chapter_text': chapter_text})
                st.session_state.total['chapterfullinfo'] = total['chapterfullinfo']
                st.success("Chain 2: Chapter Full Info executed successfully!")

        #Prompt Template

        third_input_prompt = PromptTemplate(input_variables=['chapterfullinfo', 'summaryofchapter','chapter_text'],
                                            template="Vérifiez la cohérence factuelle, sémantique et narrative entre le texte original, le résumé et la liste d'informations fournis. Fournissez un score de confiance pour chaque élément, ainsi que des commentaires détaillés pour justifier votre évaluation. Identifiez les éventuelles incohérences et suggérez des moyens de les résoudre,et fournir un score de confidence au résumé par rapport au texte originale et a la liste d'informations par rapport au texte originale fais le en français :\n  texte originale : {chapter_text}\n informations complètes: {chapterfullinfo}\n Résumé du chapître : {summaryofchapter}\n"
                                            )
        #LLM Chain

        chain3  = LLMChain(llm=llm, prompt = third_input_prompt, verbose=True, output_key = 'cohérence information')
        #, 'summaryofchapter'
        with st.expander("Chain 3: Coherence Information"):
            if st.button("Run Chain 3"):
                total['cohérence information']=run_chain(chain3, {'chapter_text': chapter_text, 'summaryofchapter': total['summaryofchapter'], 'chapterfullinfo': total['chapterfullinfo']})
                st.session_state.total['cohérence information'] = total['cohérence information']
                st.success("Chain 3: Coherence Information executed successfully!")

        
        fourth_input_prompt= PromptTemplate(input_variables=['chapterfullinfo','chapter_text'],
                                                template="il est important de respecter ces règles. Créez un scénario de manga en trois chapitres, avec trois planches par chapitre et six cases par planche, à partir du texte original et de la liste d'informations fournis. Chaque chapitre devrait se concentrer sur un événement clé de l'histoire, avec une introduction, un développement et une conclusion clairs. Chaque planche devrait se concentrer sur un personnage principal ou un conflit important, en utilisant des techniques de narration visuelle pour rendre l'histoire plus engageante. Fournissez des détails spécifiques sur les éléments clés à inclure dans chaque chapitre et chaque planche. Pensez étape par étape le format de votre réponse est markdown fais le en français :\n  texte originale : {chapter_text}\n informations complètes: {chapterfullinfo}\n "
                                                )
        chain4=LLMChain(llm=llm, prompt = fourth_input_prompt, verbose=True, output_key = 'scénario manga')
        with st.expander("Chain 4: Manga Scenario"):
            if st.button("Run Chain 4"):
                total['scénario manga']=run_chain(chain4, {'chapter_text': chapter_text, 'chapterfullinfo': total['chapterfullinfo']})
                st.session_state.total['scénario manga'] = total['scénario manga']
                st.success("Chain 4: Manga Scenario executed successfully!")        
        fifth_input_prompt  = PromptTemplate(input_variables=['scénario manga','chapterfullinfo'],
                                                template="il est important de suivres et respecter ces règles. Compléter le scénario de manga fourni, en décrivant le contenu graphique et scénaristique de chaque case vous pouvez vous basé sur les information complémentaire chapterfullinformation. Format de sortie markdown faites le en français \n scénario : {scénario manga} \n information complémentaire :{chapterfullinfo}\n")
        chain5 = LLMChain(llm=llm, prompt=fifth_input_prompt,verbose=True, output_key='sequencier')

        with st.expander("Chain 5: Sequencier"):
            if st.button("Run Chain 5"):
                total['sequencier'] =run_chain(chain5, {'scénario manga': total['scénario manga'],'chapterfullinfo': total['chapterfullinfo'] }) 
                st.session_state.total['sequencier'] = total['sequencier']
                st.success("Chain 5: Sequencier executed successfully!")        
        if st.button('process chapter', key=f'process_{chapter_index}'):
                       
            total_str=json.dumps(total)

            # Define the path to the chapter file
            chapter_filename = os.path.join(
                "data", f"chapter_{chapter_index}_{uploaded_pdf.name}_extract1.txt")
            # Write the modified text back to the appropriate file
            with open(chapter_filename, "w", encoding="utf-8") as file:
                file.write(total_str)
            st.success(f"Chapter {chapter_index} saved successfully!")
     
        
    if total:
        
        if 'chapterfullinfo' in total:
            st.success("information complète du chapitre")
            st.write(total['chapterfullinfo'])
        if 'summaryofchapter' in total:
            st.success("Résumé du chapitre")
            st.markdown(total['summaryofchapter'], unsafe_allow_html=True)
        if 'cohérence information' in total:
            st.success("cohérences des informations collecté")
            st.markdown(total['cohérence information'], unsafe_allow_html=True)
        if 'scénario manga' in total:
            st.success("scénario manga basé sur le chapitre")
            st.markdown(total['scénario manga'], unsafe_allow_html=True)
        if 'sequencier' in total:
            st.success("séquencier du scénario manga")
            st.markdown(total['sequencier'], unsafe_allow_html = True)
            # Save the generated texts in Markdown format
            output_file = os.path.join("data", f"chapter_{chapter_index}_{uploaded_pdf.name}_output.md")
            with open(output_file, "w", encoding="utf-8") as file:
                if 'summaryofchapter' in total:
                    file.write("# Chapter Summary\n")
                    file.write(total['summaryofchapter'] + "\n\n")
                if 'chapterfullinfo' in total:
                    file.write("# Chapter Full Information\n")
                    file.write(total['chapterfullinfo'] + "\n\n")
                if 'cohérence information' in total:
                    file.write("# Coherence Information\n")
                    file.write(total['cohérence information'] + "\n\n")
                if 'scénario manga' in total:
                    file.write("# Manga Scenario\n")
                    file.write(total['scénario manga'] + "\n\n")
                if 'sequencier' in total:
                    file.write("# Manga Storyboard\n")
                    file.write(total['sequencier'] + "\n\n")

            st.success(f"Chapter {chapter_index} processed and saved successfully!")
