
# NASA Engine RUL - MLOps & DataOps Pipeline

Ce projet implémente une architecture complète DataOps et MLOps pour la prédiction de la durée de vie utile restante (RUL - Remaining Useful Life) de moteurs turbofan de la NASA. 

Le système inclut l'ingestion de données en temps réel via Kafka, la gestion des caractéristiques avec un Feature Store (Feast), le réentraînement des modèles d'intelligence artificielle avec MLflow, et un tableau de bord de supervision interactif (Streamlit).

## 🚀 Comment lancer le projet manuellement

Pour exécuter ce projet localement, vous allez avoir besoin d'ouvrir **4 terminaux séparés** (PowerShell ou Invite de commandes) à la racine du projet. 

> **Prérequis :** Assurez-vous que votre environnement virtuel Python est activé dans chaque terminal et que les dépendances (`pip install -r requirements.txt`) sont bien installées.

### Terminal 1 : Démarrer l'infrastructure
Ce terminal va lancer les services requis (Kafka et Zookeeper) en arrière-plan à l'aide de Docker.
```powershell
docker compose up -d
```

> **📌 Note (Première exécution uniquement) :**
> Si c'est la première fois que vous lancez le projet, vous devez initialiser la base de données Feast avant de passer à la suite :
> ```powershell
> cd engine_rul\feature_repo

> feast apply
> cd ..\..
> ```

### Terminal 2 : Lancer le Consommateur DataOps
Le pipeline de consommation écoute les données de télémétrie Kafka en direct, les nettoie, calcule de nouvelles caractéristiques (features) et les sauvegarde dans le Data Lake (Bronze/Silver/Gold) ainsi que dans la base de données hors-ligne de Feast.
```powershell
python -m dataops.consumer_pipeline
```
*Laissez ce terminal tourner en arrière-plan.*

### Terminal 3 : Lancer le Producteur de Télémétrie
Le producteur va simuler les capteurs des moteurs en temps réel et envoyer continuellement les données vers le flux Kafka.
```powershell
python -m dataops.producer
```
*Laissez ce terminal tourner en arrière-plan.*

### Terminal 4 : Lancer le Tableau de Bord
Le tableau de bord Streamlit vous permet de visualiser les flux de capteurs en temps réel, de manipuler Feast, et de voir les prédictions d'intelligence artificielle.
```powershell
streamlit run dashboard\app.py
```
*L'interface graphique va s'ouvrir automatiquement dans votre navigateur web (généralement accessible sur `http://localhost:8501`).*

---

## 🏗️ Structure du Projet

* **`dataops/`** : Scripts pour le pipeline ETL, producteur/consommateur Kafka, gestion du Data Lake et ingénierie des caractéristiques.
* **`mlops/`** : Scripts pour l'entraînement automatique des modèles de Deep Learning (LSTM), l'évaluation et la détection de dérive (Drift).
* **`feature_store/`** : Intégration de Feast pour stocker et récupérer les features (Online / Offline).
* **`dashboard/`** : L'interface utilisateur de supervision construite avec Streamlit.
* **`engine_rul/feature_repo/`** : Configuration du Feature Store Feast.
* **`dataset/`** : Les fichiers CSV contenant les données brutes d'entraînement d'origine de la NASA.
>>>>>>> b790e79 (Initial commit - TwinSenseAI industrial machine learning project)
