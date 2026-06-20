

# NASA Engine RUL - MLOps & DataOps Pipeline

Ce projet implémente une architecture complète DataOps et MLOps pour la prédiction de la durée de vie utile restante (RUL - Remaining Useful Life) de moteurs turbofan de la NASA.

Le système inclut l'ingestion de données en temps réel via Kafka, la gestion des caractéristiques avec un Feature Store (Feast), le réentraînement des modèles d'intelligence artificielle avec MLflow, un tableau de bord de supervision interactif (Streamlit), ainsi qu'un front-end statique industriel dans `frontend/`.

## 🚀 Comment lancer le projet manuellement

Pour exécuter ce projet localement, vous allez avoir besoin d'ouvrir **4 terminaux séparés** (PowerShell ou Invite de commandes) à la racine du projet.

> **Prérequis :** Assurez-vous que votre environnement virtuel Python est activé dans chaque terminal et que les dépendances (`pip install -r requirements.txt`) sont bien installées.

### Terminal 1 : Démarrer l'infrastructure
Ce terminal va lancer les services requis (Kafka et Zookeeper) en arrière-plan à l'aide de Docker.
```powershell
docker compose up -d
```

> **📌 Note (Première exécution uniquement) :**
> Si c'est la première fois que vous lancez le projet, vous devez initialiser le Feature Store Feast avant de passer à la suite :
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

### Terminal 4 : Lancer le Tableau de Bord Streamlit
Le tableau de bord Streamlit permet de visualiser les flux de capteurs en temps réel, de consulter les prédictions RUL et de suivre les métriques de maintenance.
```powershell
streamlit run dashboard\app.py
```
*L'interface graphique va s'ouvrir automatiquement dans votre navigateur web (généralement accessible sur `http://localhost:8501`).*

---

## 🖥️ Front-end statique

En complément de l'interface Streamlit, le dossier `frontend/` contient une application statique orientée supervision industrielle, inspirée de la plateforme TwinSense AI.

### Pages principales du front-end
* **`frontend/index.html`** : Dashboard de visualisation globale avec carte usine, état en direct et navigation.
* **`frontend/machines.html`** : Vue d'ensemble de la flotte de machines, filtrage par zone et statut santé.
* **`frontend/machine-details.html`** : Page de détails machine avec télémétrie, RUL et ETF.
* **`frontend/technicians.html`** : Suivi des techniciens, statut en temps réel et assignation de tâches.
* **`frontend/alerts.html`** : Centre d'alertes avec historique des warnings et accès direct aux détails machine.
* **`frontend/settings.html`** : Paramètres et configuration de la plateforme.

### Design et ergonomie
* **Interface industrielle** avec thème sombre, micro-animations fluides et typographie lisible.
* **Cartographie** : intégration Leaflet.js et Esri Satellite pour la vue usine.
* **Graphiques** : visualisation temps réel avec Chart.js pour la télémétrie et l'évolution du RUL.
* **Contrôles de supervision** : navigation persistante et symboles industriels normalisés pour les machines.

---

## 🏗️ Structure du Projet

* **`dataops/`** : Scripts pour le pipeline ETL, producteur/consommateur Kafka, gestion du Data Lake et ingénierie des caractéristiques.
* **`mlops/`** : Scripts pour l'entraînement automatique des modèles de Deep Learning, l'évaluation et la détection de dérive.
* **`feature_store/`** : Intégration de Feast pour stocker et récupérer les features (online/offline).
* **`dashboard/`** : Interface Streamlit de supervision et visualisation temps réel.
* **`frontend/`** : Application front-end statique basée sur TwinSense AI pour le pilotage industriel.
* **`engine_rul/feature_repo/`** : Configuration et définition des entités/features Feast.
* **`dataset/`** : Données brutes et fichiers CSV d'entraînement de la NASA.
* **`config/`** : Configuration Kafka, Feast, chemins et paramètres MLOps.
* **`kafka/`** : Consumers/producer Kafka et documentation d'architecture.

---

## 📌 Remarques

* Le front-end statique dans `frontend/` est destiné à la supervision et à la présentation visuelle. Il peut être servi via un simple serveur HTTP ou intégré dans une progression future du pipeline.
* Le tableau de bord principal reste `dashboard/app.py` pour l'exécution Streamlit et la visualisation des modèles en direct.
* Link to the presentation .mp4 is [https://drive.google.com/file/d/15jFwUOr72tjmu-uh03zoma3ge_Rwwqe5/view?usp=drive_link](here)
