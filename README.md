# Book Manga Extractor

Ce programme est un outil qui permet de créer une suite de manga basé sur chaque chapitre d'un roman donné. Il utilise l'API MistralAI pour générer les scénarios de manga et les séquenciers.

## Fonctionnalités

- Extraction des chapitres d'un roman au format PDF
- Édition des chapitres extraits
- Génération d'un résumé pour chaque chapitre
- Identification des attitudes et émotions des personnages, ainsi que des éléments d'imagerie guidée
- Vérification de la cohérence factuelle, sémantique et narrative entre le texte original, le résumé et la liste d'informations fournis
- Création d'un scénario de manga en trois chapitres, avec trois planches par chapitre et six cases par planche
- Création d'un séquencier détaillé pour le scénario de manga

## Utilisation

1. Téléchargez le programme et installez les dépendances requises en utilisant `pip install -r requirements.txt`.
2. Créez un fichier `.env` et ajoutez votre clé API MistralAI en utilisant `mistral_api_key=VOTRE_CLÉ_API`.
3. Exécutez le programme en utilisant `streamlit run Home.py`.
4. Téléchargez un roman au format PDF.
5. Entrez le numéro de la dernière page de la table des matières.
6. Sélectionnez un chapitre et modifiez le texte si nécessaire.
7. Cliquez sur "process chapter" pour générer le résumé, les informations complètes, le scénario de manga et le séquencier.

## Structure des dossiers

- `data` : contient les chapitres extraits et les fichiers de sortie au format Markdown.
- `Home.py` : contient le code source du programme.

## Dépendances

- streamlit
- fitz
- re
- json
- langchain_core
- langchain_mistralai
- dotenv

## Licence

Ce programme est sous licence Apache2.0. Consultez le fichier `LICENSE` pour plus de détails.

## Auteur

[Timothée de Almeida](timotheel@alpai.eu)

## Remerciements
- [Alpai](https://alpai.eu) C'est ce que nous faisons.
- [Streamlit](https://streamlit.io/) pour la création d'interfaces utilisateur interactives.
- [MistralAI](https://mistralai.com/) pour l'API de génération de texte.
- [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/) pour la manipulation de fichiers PDF.
