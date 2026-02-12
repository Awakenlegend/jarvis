PROJECT STRUCTURE
.
├── README.md
├── main.py
├── requirements.txt
├── data/
└── jarvis/
    ├── __init__.py
    ├── assistant.py
    ├── audio.py
    ├── automation.py
    ├── commands.py
    ├── config.py
    ├── llm.py
    ├── memory.py
    ├── pdf_tools.py
    ├── search.py
    └── plugins/
        ├── __init__.py
        ├── base.py
        ├── system_plugin.py
        └── time_plugin.py

INSTALL COMMANDS
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
mkdir -p models
cd models && wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip && unzip vosk-model-small-en-us-0.15.zip && cd ..
ollama pull llama3.1:8b

RUN COMMAND
source .venv/bin/activate && python main.py
