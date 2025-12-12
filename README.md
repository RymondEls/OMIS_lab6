# Gesture & Motion Recognition — FastAPI Prototype

This repository is a prototype for the university project: an extensible gesture and motion recognition system with a FastAPI backend.

Quick start (assumes a `.venv` exists one directory above this project):

Windows PowerShell:

```powershell
# activate venv located one level up
& ..\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.main:app --reload
```

Windows CMD:

```bat
..\.venv\Scripts\activate.bat
pip install -r requirements.txt
uvicorn src.main:app --reload
```

Next steps:
- Implement capture, preprocess, recognizer services and WebSocket streaming.
