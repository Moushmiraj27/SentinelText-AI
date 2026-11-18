# SentinelText

### AI-Assisted Longitudinal Mental Wellness Monitoring & Early-Warning Support Platform

> **From isolated emotional check-ins to meaningful longitudinal
> insights.**
>
> A privacy-conscious prototype that helps users reflect on emotional
> patterns over time through journaling, emotion analysis,
> recurring-theme detection, and personalized coping suggestions.

------------------------------------------------------------------------

## Table of Contents

-   [Overview](#overview)
-   [Problem Statement](#problem-statement)
-   [Our Approach](#our-approach)
-   [Key Features](#key-features)
-   [Technology Stack](#technology-stack)
-   [System Architecture](#system-architecture)
-   [AI/ML Workflow](#aiml-workflow)
-   [Project Structure](#project-structure)
-   [Getting Started](#getting-started)
-   [Environment Configuration](#environment-configuration)
-   [Running the Application](#running-the-application)
-   [API Documentation](#api-documentation)
-   [Privacy and Security](#privacy-and-security)
-   [Current Scope and Limitations](#current-scope-and-limitations)
-   [Future Roadmap](#future-roadmap)
-   [Contributing](#contributing)
-   [Disclaimer](#disclaimer)

------------------------------------------------------------------------

## Overview

**SentinelText** is an AI-assisted mental wellness monitoring prototype
designed to help users understand their emotional experiences over time.

Traditional check-ins and isolated assessments may not always capture
recurring emotional patterns or changes in a person's experiences.
SentinelText explores a more continuous and reflective approach by
connecting personal journal entries, approximate emotion identification,
recurring themes, and user-reported activities.

Rather than treating every journal entry as an isolated piece of
information, the platform aims to build a longitudinal view of emotional
experiences and provide understandable, supportive insights.

The project is being developed in the context of **Smart India Hackathon
(SIH) 2026**, under the problem statement:

**SIH26094 --- AI-Powered Dynamic Mental Health Monitoring and Distress
Prediction System for Victims of Atrocities.**

> **Project status:** The current implementation is a working prototype.
> Advanced distress prediction, professional monitoring dashboards, and
> case-management capabilities are part of the proposed development
> roadmap, not claims about the existing implementation.

------------------------------------------------------------------------

## Problem Statement

Emotional well-being is dynamic. A person's emotional state can change
in response to personal experiences, environmental conditions, stressful
situations, and everyday activities.

However, conventional approaches often rely on:

-   Isolated check-ins or one-time assessments.
-   Self-reported information that may not capture recurring patterns.
-   Limited visibility into changes across time.
-   A lack of structured connections between emotional experiences,
    possible triggers, and helpful activities.
-   Difficulty maintaining continuity between individual interactions.

This creates an opportunity for technology that supports continuous
reflection and helps organize relevant information over time.

------------------------------------------------------------------------

## Our Approach

SentinelText follows a user-centered, longitudinal approach:

1.  **Capture** --- Users record personal experiences through journal
    entries and voice-based input.
2.  **Analyze** --- The system processes journal text to identify
    approximate emotional signals.
3.  **Connect** --- Similar entries and recurring themes are grouped to
    reveal patterns.
4.  **Understand** --- Users can explore possible connections between
    situations, emotional experiences, and activities.
5.  **Support** --- The platform provides personalized coping activity
    suggestions and reflective insights.

The objective is to support awareness and continuity --- not to replace
professional mental healthcare.

------------------------------------------------------------------------

## Key Features

### 1. Secure User Authentication

-   User registration and login.
-   Password hashing.
-   Authentication-based access to user-specific information.
-   JWT-based authentication configuration.

### 2. Personal Journaling

-   Create and maintain private journal entries.
-   Record personal experiences and reflections.
-   Maintain historical entries for longitudinal exploration.

### 3. Voice-to-Text Input

-   Voice-based journal input through transcription.
-   Makes it easier to record reflections without manually typing
    everything.

### 4. Emotion Analysis

-   Rule-based emotion identification from journal text.
-   Provides approximate emotional signals for reflection.
-   Designed as an initial analysis layer that can be extended with more
    advanced NLP models.

### 5. Emotional Echo

-   Identifies similarities between journal entries.
-   Uses text similarity to discover recurring themes.
-   Helps users explore patterns that may not be obvious from individual
    entries.

### 6. Trigger & Relief Mapper

-   Connects reported situations and emotional patterns with activities.
-   Helps users reflect on activities they associate with feeling better
    or worse.
-   Encourages awareness of personal patterns.

### 7. Personalized Coping Suggestions

-   Provides supportive activity recommendations.
-   Encourages healthy reflection and self-awareness.

### 8. 30-Day Emotional Journey

-   Presents a time-based view of emotional experiences.
-   Helps users explore changes and recurring patterns across journal
    history.

### 9. User Interface

-   React-based responsive interface.
-   Light and dark theme support.
-   Dedicated views for journaling, insights, and emotional patterns.

------------------------------------------------------------------------

## Technology Stack

  -----------------------------------------------------------------------
  Layer                   Technologies            Purpose
  ----------------------- ----------------------- -----------------------
  Frontend                React, TypeScript       User interface and
                                                  application logic

  Build Tool              Vite                    Frontend development
                                                  and production builds

  Backend                 Python, FastAPI         REST API and
                                                  application services

  ORM                     SQLAlchemy              Database interaction

  Database                SQLite                  Local development and
                                                  persistent storage

  Authentication          JWT, password hashing   Authentication and
                                                  access control

  NLP                     Python NLP libraries    Text processing and
                                                  emotion-related
                                                  analysis

  Text Vectorization      TF-IDF                  Numerical
                                                  representation of
                                                  journal text

  Similarity Analysis     Cosine Similarity       Identifying related
                                                  journal entries

  ML Extensions           Sentence Transformers,  Potential semantic and
                          Hugging Face            emotion-analysis
                                                  extensions

  External AI Integration Groq (optional          Optional AI-assisted
                          integration)            functionality where
                                                  configured

  Version Control         Git, GitHub             Source code management
                                                  and collaboration
  -----------------------------------------------------------------------

**Core implementation:** React, TypeScript, Vite, Python, FastAPI,
SQLAlchemy, SQLite, and the existing text-analysis components.

Some listed technologies represent optional integrations or extension
paths. Their presence in this table does not imply that every model or
external service is required to run the current prototype.

------------------------------------------------------------------------

## System Architecture

SentinelText follows a frontend-backend architecture with separate
application, authentication, data, and analysis responsibilities.

### High-Level Architecture

``` mermaid
flowchart TD
    A[User] --> B[React + TypeScript Frontend]
    B --> C[FastAPI Backend]

    C --> D[Authentication Layer]
    C --> E[Application Services]

    D --> F[User Access Control]
    E --> G[Journal Management]
    E --> H[Emotion Analysis]
    E --> I[Pattern Analysis]

    G --> J[(SQLite Database)]
    F --> J

    H --> K[Emotion Signals]
    I --> L[TF-IDF and Cosine Similarity]

    K --> M[Insights and Emotional Journey]
    L --> M

    M --> B
```

### Architecture Components

**1. Presentation Layer**

-   Built using React and TypeScript.
-   Handles user interaction, journal input, navigation, and
    visualization.
-   Communicates with the backend through API requests.

**2. Backend / API Layer**

-   Built using FastAPI.
-   Handles incoming requests and application logic.
-   Separates authentication, journal operations, and analysis
    functionality.

**3. Authentication Layer**

-   Manages user registration and login.
-   Uses password hashing and JWT-based authentication.
-   Supports user-specific data access.

**4. Data Layer**

-   Uses SQLAlchemy for database operations.
-   SQLite is used for local development and data persistence.
-   A production database configuration should be selected and validated
    before deployment.

**5. AI/NLP Processing Layer**

-   Processes journal text.
-   Performs approximate emotion identification.
-   Applies text similarity techniques to discover recurring themes.
-   Supplies analysis results to the application's insight features.

------------------------------------------------------------------------

## AI/ML Workflow

The current prototype uses text-processing and similarity-analysis
techniques to explore patterns in journal entries.

``` mermaid
flowchart TD
    A[Journal Entry] --> B[Text Preprocessing]
    B --> C[Emotion Identification]
    B --> D[Text Vectorization]

    C --> E[Emotion Signals]
    D --> F[TF-IDF Vectors]
    F --> G[Cosine Similarity]

    G --> H[Related Entry Grouping]
    E --> I[Emotional Pattern Insights]
    H --> I

    I --> J[Longitudinal Reflection]
    J --> K[User-Facing Insights]
```

### Techniques Used

  Technique             Application
  --------------------- ------------------------------------------------
  Text Preprocessing    Preparing journal text for analysis
  Rule-Based Analysis   Approximate emotion identification
  TF-IDF                Converting text into numerical feature vectors
  Cosine Similarity     Measuring similarity between journal entries
  Similarity Grouping   Connecting entries with recurring themes

### Future AI/ML Extensions

The architecture can be extended with:

-   Transformer-based emotion classification.
-   Sentence embeddings for semantic similarity.
-   Improved contextual understanding of journal entries.
-   Longitudinal trend analysis.
-   Explainable indicators for human-reviewed support workflows.

These extensions require further implementation, testing, and
validation.

------------------------------------------------------------------------

## Project Structure

The repository is organized around separate frontend and backend
applications.

``` text
SentinelText-AI/
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.ts
├── backend/
│   ├── services/
│   ├── auth/
│   ├── requirements.txt
│   └── main.py
├── .gitignore
└── README.md
```

*Note: This is a high-level representation of the project structure.
Refer to the repository for the complete and current directory layout.*

------------------------------------------------------------------------

## Getting Started

Follow these steps to run SentinelText locally.

### Prerequisites

Make sure the following are installed:

-   Python 3.12
-   Node.js and npm
-   Git

Check your installations:

``` bash
python --version
node --version
npm --version
git --version
```

### 1. Clone the Repository

``` bash
git clone https://github.com/dnyanu0909/SentinelText-AI.git
cd SentinelText-AI
```

### 2. Set Up the Backend

Create a Python virtual environment:

``` bash
py -3.12 -m venv .venv
```

Activate it on Windows PowerShell:

``` powershell
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

``` bash
pip install -r backend/requirements.txt
```

### 3. Set Up the Frontend

Open a terminal in the project root:

``` bash
cd frontend
npm install
```

### 4. Configure Environment Variables

The backend requires a secure JWT secret.

On Windows PowerShell, generate a random secret:

``` powershell
$bytes = New-Object byte[] 48
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$secret = [Convert]::ToBase64String($bytes)

[Environment]::SetEnvironmentVariable("JWT_SECRET_KEY", $secret, "User")
$env:JWT_SECRET_KEY = $secret

$rng.Dispose()
Remove-Variable secret, bytes
```

Open a new terminal after setting the persistent user environment
variable.

> **Important:** Never commit secret keys, API tokens, credentials, or
> `.env` files to GitHub.

------------------------------------------------------------------------

## Running the Application

The frontend and backend run in separate terminals.

### Start the Backend

From the project root, with the virtual environment activated:

``` bash
python -m uvicorn backend.main:app --reload
```

The backend should be available at:

``` text
http://127.0.0.1:8000
```

### Start the Frontend

Open another terminal:

``` bash
cd frontend
npm run dev
```

Vite will display the local development URL, typically:

``` text
http://localhost:5173
```

Open the displayed URL in your browser.

------------------------------------------------------------------------

## API Documentation

SentinelText uses FastAPI for backend API development.

FastAPI provides automatically generated interactive API documentation.

After starting the backend, open:

-   **Swagger UI:** <http://127.0.0.1:8000/docs>
-   **OpenAPI Schema:** <http://127.0.0.1:8000/openapi.json>

The documentation allows developers to inspect available endpoints and
test supported API operations.

------------------------------------------------------------------------

## Privacy and Security

Because SentinelText handles personal journal information, privacy and
security are important design considerations.

The current prototype includes or is configured around:

-   Password hashing for authentication.
-   JWT-based authentication.
-   User-specific data access.
-   Separation of frontend and backend responsibilities.
-   Environment-based configuration for sensitive authentication
    secrets.

### Security Considerations for Further Development

Before production deployment, the project should undergo additional
security work, including:

-   Comprehensive authorization and access-control testing.
-   Input validation and secure error handling.
-   HTTPS and secure deployment configuration.
-   Database backup and recovery planning.
-   Data retention and deletion policies.
-   Consent management for optional external AI services.
-   Security testing and dependency monitoring.

Sensitive journal information should not be exposed to unauthorized
users or sent to external services without appropriate consent and
safeguards.

------------------------------------------------------------------------

## Current Scope and Limitations

SentinelText is an evolving prototype, and its capabilities should be
understood within the scope of the current implementation.

  -----------------------------------------------------------------------
  Area                                Current Status
  ----------------------------------- -----------------------------------
  User authentication                 Implemented

  Personal journaling                 Implemented

  Voice-to-text input                 Available in the prototype

  Rule-based emotion identification   Implemented

  Emotional Echo similarity analysis  Implemented

  Trigger & Relief Mapper             Implemented prototype functionality

  Coping activity suggestions         Implemented prototype functionality

  30-day emotional journey            Implemented prototype functionality

  Advanced distress prediction        Future development

  Counselor / case-worker dashboard   Proposed

  Role-based professional access      Proposed

  Case management and intervention    Proposed
  tracking                            

  Validated clinical assessment       Requires further development and
                                      validation

  District-level anonymized analytics Proposed
  -----------------------------------------------------------------------

### Important Limitations

-   Emotion identification is approximate and should not be interpreted
    as a clinical assessment.
-   Text similarity does not establish psychological or clinical
    relationships.
-   The prototype does not provide a clinically validated distress
    prediction model.
-   User-generated journal data may be incomplete or subjective.
-   Recommendations are supportive suggestions, not professional
    treatment.
-   Production readiness, scalability, and clinical effectiveness have
    not been established.

------------------------------------------------------------------------

## Future Roadmap

The next development stages focus on improving analytical capabilities,
privacy, and support workflows.

### Phase 1 --- Prototype Foundation

-   User authentication and journaling.
-   Emotion-related text analysis.
-   Recurring-theme identification.
-   Emotional journey and coping suggestions.

### Phase 2 --- Advanced AI/ML

-   Evaluate transformer-based emotion models.
-   Improve semantic similarity using sentence embeddings.
-   Develop longitudinal trend analysis.
-   Improve interpretability of generated insights.

### Phase 3 --- Dynamic Monitoring

-   Explore configurable distress assessments.
-   Develop transparent risk-trend indicators.
-   Evaluate performance using appropriate datasets and validation
    methods.

### Phase 4 --- Professional Support Workflows

-   Counselor and case-worker dashboard.
-   Role-based access control.
-   Case management and intervention tracking.
-   Human-reviewed alert prioritization.

### Phase 5 --- Security and Deployment

-   Strengthen privacy and access controls.
-   Evaluate production database architecture.
-   Conduct security and performance testing.
-   Explore controlled pilot deployment with appropriate oversight.

------------------------------------------------------------------------

## Contributing

Contributions, suggestions, and improvements are welcome.

If you would like to contribute:

1.  Fork the repository.
2.  Create a feature branch.
3.  Make your changes.
4.  Test your implementation.
5.  Submit a pull request with a clear description.

Example:

``` bash
git checkout -b feature/your-feature-name
git add .
git commit -m "Add: describe your changes"
git push origin feature/your-feature-name
```

Please avoid committing credentials, private journal data, database
files containing personal information, virtual environments, or
generated dependency directories.

------------------------------------------------------------------------

## Disclaimer

SentinelText is an experimental, AI-assisted wellness-support prototype
intended for educational, research, and development purposes.

It is **not a medical device, diagnostic tool, emergency-response
system, or substitute for qualified mental health professionals**.

Its emotion-related outputs and recommendations are exploratory and
should not be used as the sole basis for clinical decisions, risk
classification, or consequential interventions.

Any future distress-monitoring or professional-support functionality
must be developed with appropriate privacy safeguards, validation, human
oversight, and ethical review.

------------------------------------------------------------------------

## Project Information

  ----------------------------------- ------------------------------------------------------------------
  **Project**                         SentinelText

  **Domain**                          Artificial Intelligence · Machine Learning · Natural Language
                                      Processing · Mental Wellness Technology

  **Hackathon Context**               Smart India Hackathon 2026

  **Problem Statement**               SIH26094

  **Repository**                      [SentinelText-AI](https://github.com/dnyanu0909/SentinelText-AI)
  ----------------------------------- ------------------------------------------------------------------

------------------------------------------------------------------------

**SentinelText — Making emotional patterns easier to understand, one reflection at a time.**
