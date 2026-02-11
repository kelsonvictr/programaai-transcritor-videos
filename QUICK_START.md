# ⚡ Quick Start — Transcritor NotebookLM PRO

<p align="center">
  <img src="https://programaai.dev/assets/logo-BPg_3cKF.png" alt="Programa AI" height="80">
</p>

## 🚀 Iniciar em 1 comando

```bash
# All-in-One: Setup + Run
./go.sh
```

Acesse: **http://127.0.0.1:5000**

---

### Ou em 2 comandos

```bash
# 1. Setup (primeira vez)
./start.sh

# 2. Rodar servidor
./run.sh
```

Acesse: **http://127.0.0.1:5000**

---

## 📖 O que cada script faz?

### `./go.sh` — All-in-One (RECOMENDADO)

Faz **tudo automaticamente** e já inicia o servidor:

1. ✅ Verifica Python 3.10+
2. ✅ Instala FFmpeg (se necessário)
3. ✅ Instala whisper-cli (se necessário)
4. ✅ Oferece download do modelo GGML (~1.5 GB)
5. ✅ Cria ambiente virtual Python
6. ✅ Instala dependências Flask
7. ✅ Inicializa banco SQLite
8. ✅ **Inicia o servidor automaticamente**

**Execute quando quiser setup + run em um comando só**.

### `./start.sh` — Setup Automático

Executa automaticamente:

1. ✅ Verifica Python 3.10+
2. ✅ Instala FFmpeg (se necessário)
3. ✅ Instala whisper-cli (se necessário)
4. ✅ Oferece download do modelo GGML (~1.5 GB)
5. ✅ Cria ambiente virtual Python
6. ✅ Instala dependências Flask
7. ✅ Inicializa banco SQLite
8. ✅ **Pergunta se quer iniciar o servidor**

**Execute apenas uma vez** (ou quando atualizar o projeto).

### `./run.sh` — Iniciar Servidor

- Ativa o ambiente virtual automaticamente
- Inicia o Flask em modo debug
- Mostra URL de acesso

**Execute sempre que quiser usar a ferramenta**.

---

## 🎯 Primeiro Uso

### Opção 1: Jeito mais fácil

```bash
./go.sh
```

Pronto! Já configura tudo e inicia.

### Opção 2: Em 2 etapas

```bash
# 1. Setup
./start.sh

# 2. Rodar (quando solicitado, ou depois com)
./run.sh
```

### 3. Acessar interface

Abra no navegador: **http://127.0.0.1:5000**

### 4. Criar primeira transcrição

1. Clique em **"Nova Transcrição"**
2. Faça upload de uma aula (`.mov`, `.mp4`, etc)
3. Preencha título e tags
4. Clique em **"Iniciar Transcrição"**
5. Acompanhe o progresso em tempo real
6. Baixe o pacote ZIP quando concluir

---

## 🛑 Parar o Servidor

No terminal onde está rodando, pressione:

```
Ctrl + C
```

---

## ⚙️ Configurações

Edite `config.py` para ajustar:

- Caminho do modelo GGML
- Idioma padrão
- Tamanho máximo de upload
- Quantidade de cortes para Reels
- Tamanho de parágrafos

---

## ❓ Problemas?

### Modelo não encontrado

```bash
# Baixar manualmente
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

### Erro de permissão nos scripts

```bash
chmod +x start.sh run.sh
```

---

## 📚 Documentação Completa

Veja `README.md` para detalhes sobre:

- Estrutura do pacote gerado
- Como importar no NotebookLM
- Troubleshooting detalhado
- Configurações avançadas

---

**Desenvolvido por [Programa AI](https://programaai.dev)** 🚀
