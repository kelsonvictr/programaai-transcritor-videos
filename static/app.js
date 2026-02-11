/* ══════════════════════════════════════════════════════════
   Transcritor → NotebookLM PRO — JavaScript
   ══════════════════════════════════════════════════════════ */

/**
 * Copia texto para o clipboard e mostra feedback visual.
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showCopyToast('Copiado para o clipboard!');
    }).catch(err => {
        // Fallback para navegadores mais antigos
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            showCopyToast('Copiado para o clipboard!');
        } catch (e) {
            showCopyToast('Erro ao copiar.', true);
        }
        document.body.removeChild(textarea);
    });
}

/**
 * Mostra um toast de feedback.
 */
function showCopyToast(message, isError = false) {
    // Remover toast anterior
    const existing = document.querySelector('.copy-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'copy-toast';
    toast.textContent = message;
    if (isError) {
        toast.style.background = '#dc3545';
    }
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 2000);
}

/**
 * Auto-scroll no log viewer quando atualizado.
 */
function autoScrollLog() {
    const logViewer = document.getElementById('logViewer');
    if (logViewer) {
        logViewer.scrollTop = logViewer.scrollHeight;
    }
}

// Auto-scroll inicial
document.addEventListener('DOMContentLoaded', autoScrollLog);
