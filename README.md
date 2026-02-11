# 🎓 Transcritor de Aulas → NotebookLM PRO

<p align="center">
  <img src="https://programaai.dev/assets/logo-BPg_3cKF.png" alt="Programa AI" height="80">
</p>

Ferramenta **100% local** (macOS) para transcrever aulas gravadas e gerar um pacote completo otimizado para importação no **Google NotebookLM**.

## ⚡ Início Rápido

```bash
# Jeito mais fácil (all-in-one)
./go.sh
```

Pronto! Acesse **http://127.0.0.1:5000**

Para mais detalhes, veja `QUICK_START.md` ou execute `./help.sh`.

## 🛠 Scripts Disponíveis

| Script | Descrição |
|--------|-----------|
| `./go.sh` | 🚀 Setup + Run em 1 comando (recomendado) |
| `./start.sh` | ⚙️ Setup inicial (pergunta se quer iniciar) |
| `./run.sh` | ▶️ Iniciar servidor Flask |
| `./clean.sh` | 🧹 Limpar dados e recomeçar |
| `./help.sh` | ❓ Menu de ajuda visual |

## 📦 O Que Você Recebe

Para cada aula, o sistema gera um pacote NotebookLM com:

- ✅ Transcrição limpa (.txt) com timestamps por parágrafo
- ✅ Legendas (.srt e .vtt)
- ✅ Notas em 3 versões (curta/média/apostila)
- ✅ Capítulos detectados automaticamente  
- ✅ 12 prompts prontos para copy/paste
- ✅ Cortes sugeridos para Reels com timestamps
- ✅ ZIP completo para importar facilmente

## 📋 Requisitos

- **macOS** (Apple Silicon ou Intel com Homebrew)
- **Python 3.10+**
- **FFmpeg** → `brew install ffmpeg`
- **whisper.cpp** → `brew install whisper-cpp`
- **Modelo GGML** → O script `./go.sh` pode baixar automaticamente

## 📖 Documentação

- **`QUICK_START.md`** → Guia visual rápido
- **`./help.sh`** → Ajuda interativa no terminal
- Documentação completa das funcionalidades abaixo ↓

### 💡 Dicas de Configuração

- **VAD (Voice Activity Detection)**: Recomendado **ativado** para aulas longas (remove silêncios e melhora timestamps)
- **Modelo**: Use `medium` (padrão) para melhor qualidade. Use `small` para testes rápidos.
- **Limpeza de texto**: Mantém o conteúdo técnico, remove apenas muletas repetitivas
- **Timestamps no TXT**: Facilita navegação no NotebookLM

---

## 📂 Estrutura do Pacote Gerado

```
data/outputs/<id>/
├── transcript.txt           # Transcrição limpa com timestamps
├── transcript.srt           # Legendas SRT
├── transcript.vtt           # Legendas WebVTT
├── chapters.md              # Capítulos com timestamps
├── notes_short.md           # Notas resumidas
├── notes_medium.md          # Notas completas
├── notes_detailed.md        # Apostila detalhada
├── notebooklm_prompts.txt   # 12 prompts prontos
├── reels_cuts.md            # Cortes para Reels
├── index.json               # Metadados
├── README.md                # Instruções
└── package.zip              # Tudo empacotado
```

## 🔧 Configuração

Edite `config.py` para ajustar:

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `WHISPER_BIN` | `/opt/homebrew/bin/whisper-cli` | Caminho do whisper-cli |
| `MODEL_PATH` | `./ggml-medium.bin` | Caminho do modelo GGML |
| `DEFAULT_LANGUAGE` | `pt` | Idioma padrão |
| `MAX_UPLOAD_MB` | `4096` | Tamanho máximo de upload (MB) |
| `DEFAULT_REELS_CUT_COUNT` | `12` | Qtd. de cortes sugeridos |

## 📝 Como Importar no NotebookLM

### Básico (Recomendado)
1. Acesse [notebooklm.google.com](https://notebooklm.google.com)
2. Crie um novo Notebook
3. Importe:
   - `transcript.txt` → Fonte principal
   - `notes_medium.md` → Notas organizadas
   - `chapters.md` → Estrutura de tópicos
4. Use os prompts de `notebooklm_prompts.txt`

### Avançado
Para análise mais profunda, importe também `notes_detailed.md`.

💡 **Dica**: O NotebookLM funciona melhor com blocos curtos. A `transcript.txt` já vem segmentada perfeitamente.

## ❓ Troubleshooting

### Modelo não encontrado
```bash
curl -L -o ggml-medium.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin
```

### whisper-cli não encontrado
```bash
brew install whisper-cpp
```

### FFmpeg não encontrado
```bash
brew install ffmpeg
```

### PATH do Homebrew
Se comandos não forem encontrados:
```bash
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Transcrição lenta
- Use modelo `small` em vez de `medium` para testes
- Ative o VAD para pular silêncios
- Verifique modo de economia de energia do Mac

### Crash com Metal/GPU (Apple Silicon)
Se o whisper-cli crashar com erro de Metal:
```bash
# Desabilite a GPU editando config.py:
WHISPER_USE_GPU = False
```
Ou defina a variável de ambiente:
```bash
export WHISPER_USE_GPU=false
python app.py
```
A transcrição será mais lenta, mas estável.

### Erro de VAD Model
O checkbox "Usar VAD" está disponível na interface, mas o modelo VAD não está configurado por padrão. O whisper.cpp já faz detecção de voz internamente, então você pode desmarcar essa opção. Para usar VAD no futuro, será necessário baixar o modelo VAD separadamente.

## 📂 Estrutura do Projeto

```
transcritor-videos/
├── go.sh                   # 🚀 All-in-one
├── start.sh                # ⚙️  Setup
├── run.sh                  # ▶️  Run
├── clean.sh                # 🧹 Clean
├── help.sh                 # ❓ Help
├── QUICK_START.md          # 📖 Guia
├── README.md               # 📚 Docs
├── app.py                  # Flask app
├── config.py               # Config
├── database.py             # SQLite
├── worker.py               # Processing
├── requirements.txt        # Python deps
├── templates/              # HTML
├── static/                 # CSS + JS
└── data/                   # Uploads + outputs
```

## 📜 Licença

Uso pessoal / educacional. Feito com ❤️ por [Programa AI](https://programaai.dev).
